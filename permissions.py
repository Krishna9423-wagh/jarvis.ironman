"""
J.A.R.V.I.S. 3-Tier Autonomous Permission & Safety System
---------------------------------------------------------
Tier 1 - SAFE: No permission needed. Executed immediately.
         (App opening, website reading, search, time, weather, volume, read-only file/shell)

Tier 2 - ASK: Spoken 'yes' required before execution.
         (Messages, emails, calls, posts, typing in external apps, installing packages, moving files)
         - Reads back who, where, what text.
         - Allows voice modification ("change it").
         - Immediately aborts on "stop" or "cancel".

Tier 3 - BLOCKED: High risk. Prohibited unless user speaks "yes, I'm sure" TWICE.
         (File deletion 'rm', sudo, payments/purchases, changing account settings/passwords)
"""

import re
import time
from typing import Dict, Any, Optional, Tuple
from config import log_event

class PermissionTier:
    SAFE = "SAFE"
    ASK = "ASK"
    BLOCKED = "BLOCKED"

# Tool-to-Tier Mapping
TOOL_TIER_MAP = {
    # SAFE Tools
    "open_app": PermissionTier.SAFE,
    "close_app": PermissionTier.SAFE,
    "open_website": PermissionTier.SAFE,
    "web_search": PermissionTier.SAFE,
    "play_youtube": PermissionTier.SAFE,
    "open_file_or_folder": PermissionTier.SAFE,
    "read_file_content": PermissionTier.SAFE,
    "summarize_document": PermissionTier.SAFE,
    "tell_time": PermissionTier.SAFE,
    "tell_date": PermissionTier.SAFE,
    "get_weather": PermissionTier.SAFE,
    "take_screenshot": PermissionTier.SAFE,
    "system_control": PermissionTier.SAFE,
    "start_gesture_control": PermissionTier.SAFE,
    "stop_gesture_control": PermissionTier.SAFE,
    "toggle_gesture_debug": PermissionTier.SAFE,
    "open_gesture_hud": PermissionTier.SAFE,
    "resolve_contact": PermissionTier.SAFE,

    # ASK Tools (Direct communications, system mutations, typing)
    "send_whatsapp": PermissionTier.ASK,
    "send_imessage": PermissionTier.ASK,
    "send_email": PermissionTier.ASK,
    "send_instagram_dm": PermissionTier.ASK,
    "make_call": PermissionTier.ASK,
    "type_on_screen": PermissionTier.ASK,
    "click_screen": PermissionTier.ASK,
    "create_file": PermissionTier.ASK,
    "write_code_file": PermissionTier.ASK,
    "set_timer": PermissionTier.SAFE,
    "set_reminder": PermissionTier.ASK,
    "add_calendar_event": PermissionTier.ASK,

    # Dynamic Shell evaluation
    "run_shell": None,  # Checked dynamically below
}

# Dangerous shell patterns for BLOCKED tier
BLOCKED_SHELL_PATTERNS = [
    r"\brm\s+", r"\brmdir\b", r"\btrash\b", r"\bsudo\b", r"\bmkfs\b",
    r"\bdd\s+", r"\bshutdown\b", r"\breboot\b", r"\bkillall\b",
    r"passwd", r"keychain", r"security\s+delete", r"format\b"
]

ASK_SHELL_PATTERNS = [
    r"\bmv\s+", r"\bcp\s+", r"\bbrew\s+install", r"\bpip\s+install",
    r"\bnpm\s+install", r"\bgit\s+commit", r"\bgit\s+push", r"\bcurl\s+-X\s*(POST|PUT|DELETE)"
]

class PendingAction:
    def __init__(self, tool_name: str, tool_args: Dict[str, Any], tier: str, description: str):
        self.tool_name = tool_name
        self.tool_args = tool_args
        self.tier = tier
        self.description = description
        self.created_at = time.time()
        self.blocked_confirm_count = 0  # Requires 2 for BLOCKED

class PermissionManager:
    def __init__(self):
        self.pending_action: Optional[PendingAction] = None

    def evaluate_tier(self, tool_name: str, tool_args: Dict[str, Any]) -> str:
        """Determine safety tier of a requested tool execution."""
        if tool_name == "run_shell":
            cmd = tool_args.get("command", "").strip()
            for pattern in BLOCKED_SHELL_PATTERNS:
                if re.search(pattern, cmd, re.IGNORECASE):
                    return PermissionTier.BLOCKED
            for pattern in ASK_SHELL_PATTERNS:
                if re.search(pattern, cmd, re.IGNORECASE):
                    return PermissionTier.ASK
            return PermissionTier.SAFE

        if tool_name in ["create_file", "write_code_file"]:
            path = tool_args.get("path", "")
            if any(p in path.lower() for p in ["/etc", "/system", "/library", "/bin", "/usr"]):
                return PermissionTier.BLOCKED
            return PermissionTier.ASK

        return TOOL_TIER_MAP.get(tool_name, PermissionTier.ASK)

    def is_cancel_phrase(self, text: str) -> bool:
        """Check if user is issuing an immediate kill/abort voice command."""
        t = text.lower().strip()
        cancel_words = [
            "stop", "cancel", "abort", "halt", "quit", "no", "nah", "nevermind",
            "ruko", "ruk jao", "mat karo", "rehne do", "chhor do", "band karo"
        ]
        return any(re.search(rf"\b{w}\b", t) for w in cancel_words)

    def is_approval_phrase(self, text: str) -> bool:
        """Check if user verbally granted permission."""
        t = text.lower().strip()
        approvals = [
            "yes", "yeah", "yep", "sure", "go ahead", "do it", "send it", "send",
            "haan", "karo", "bhejo", "theek hai", "sahi hai", "approved", "proceed"
        ]
        return any(re.search(rf"\b{w}\b", t) for w in approvals)

    def is_double_confirmation(self, text: str) -> bool:
        """Check for strict double confirmation phrase 'yes, I'm sure'."""
        t = text.lower().strip()
        return bool(re.search(r"\b(yes[, ]*i['’]?m sure|yes i am sure|haan mujhe pura yakeen hai)\b", t))

    def is_change_request(self, text: str) -> Tuple[bool, str]:
        """Check if user wants to modify draft arguments verbally."""
        t = text.lower().strip()
        pattern = r"\b(change it to|change message to|change it|no change it to|instead say|say)\s+(.*)"
        match = re.search(pattern, t)
        if match:
            new_text = match.group(2).strip()
            return True, new_text
        if "change it" in t or "edit it" in t:
            return True, ""
        return False, ""

    def format_ask_prompt(self, tool_name: str, tool_args: Dict[str, Any]) -> str:
        """Generate human-readable read-back of pending action."""
        if tool_name == "send_whatsapp":
            contact = tool_args.get("contact", "recipient")
            text = tool_args.get("text", "")
            return f"I'll send this to {contact} on WhatsApp: \"{text}\". Should I send it, Sir?"

        elif tool_name == "send_imessage":
            contact = tool_args.get("contact", "recipient")
            text = tool_args.get("text", "")
            return f"I'll send this iMessage to {contact}: \"{text}\". Shall I proceed, Sir?"

        elif tool_name == "send_email":
            to = tool_args.get("to", "recipient")
            subject = tool_args.get("subject", "No subject")
            body = tool_args.get("body", "")
            short_body = body[:80] + ("..." if len(body) > 80 else "")
            return f"I'll send an email to {to} with subject \"{subject}\" and body \"{short_body}\". Should I send it, Sir?"

        elif tool_name == "make_call":
            contact = tool_args.get("contact", "target")
            plat = tool_args.get("platform", "FaceTime")
            return f"I'm ready to place a {plat} call to {contact}. Should I connect the call, Sir?"

        elif tool_name == "send_instagram_dm":
            user = tool_args.get("user", "user")
            text = tool_args.get("text", "")
            return f"I'll send an Instagram DM to @{user}: \"{text}\". Should I send it, Sir?"

        elif tool_name == "run_shell":
            cmd = tool_args.get("command", "")
            return f"I am about to execute the shell command: `{cmd}`. Do you approve, Sir?"

        elif tool_name in ["create_file", "write_code_file"]:
            path = tool_args.get("path", "")
            return f"I am about to write or overwrite file `{path}`. Shall I proceed, Sir?"

        elif tool_name == "set_reminder":
            msg = tool_args.get("message", "")
            return f"I will add a reminder: \"{msg}\". Should I save it, Sir?"

        elif tool_name == "add_calendar_event":
            title = tool_args.get("title", "")
            return f"I will schedule calendar event: \"{title}\". Should I create it, Sir?"

        return f"I am ready to perform `{tool_name}` with {tool_args}. Do you approve, Sir?"

    def prepare_action(self, tool_name: str, tool_args: Dict[str, Any]) -> Tuple[str, str]:
        """
        Evaluate if tool needs approval.
        Returns: (tier, verbal_prompt)
        """
        tier = self.evaluate_tier(tool_name, tool_args)
        desc = self.format_ask_prompt(tool_name, tool_args)
        
        if tier == PermissionTier.SAFE:
            return PermissionTier.SAFE, ""

        self.pending_action = PendingAction(tool_name, tool_args, tier, desc)
        log_event("PERMISSION:GATED", f"Tool '{tool_name}' requires [{tier}] approval. Desc: {desc}")

        if tier == PermissionTier.BLOCKED:
            prompt = (
                f"SECURITY WARNING: This action is classified as HIGH RISK: {desc} "
                "To proceed, you must state 'Yes, I'm sure' twice."
            )
            return PermissionTier.BLOCKED, prompt

        return PermissionTier.ASK, desc

    def handle_user_response(self, user_text: str) -> Dict[str, Any]:
        """
        Process user's vocal response to a pending permission request.
        Returns:
            {
                "status": "APPROVED" | "CANCELLED" | "MODIFIED" | "NEED_CONFIRMATION_2" | "UNRESOLVED",
                "message": str,
                "action": Optional[PendingAction]
            }
        """
        if not self.pending_action:
            return {"status": "UNRESOLVED", "message": "No action pending.", "action": None}

        # 1. Immediate cancel
        if self.is_cancel_phrase(user_text):
            action = self.pending_action
            self.pending_action = None
            log_event("PERMISSION:CANCELLED", f"User aborted action '{action.tool_name}'")
            return {"status": "CANCELLED", "message": "Action cancelled, Sir. Standing down.", "action": None}

        # 2. Check for voice edit / modification
        wants_change, new_text = self.is_change_request(user_text)
        if wants_change:
            if new_text and ("text" in self.pending_action.tool_args or "body" in self.pending_action.tool_args):
                if "text" in self.pending_action.tool_args:
                    self.pending_action.tool_args["text"] = new_text
                elif "body" in self.pending_action.tool_args:
                    self.pending_action.tool_args["body"] = new_text
                new_desc = self.format_ask_prompt(self.pending_action.tool_name, self.pending_action.tool_args)
                self.pending_action.description = new_desc
                log_event("PERMISSION:MODIFIED", f"Updated draft text: {new_text}")
                return {
                    "status": "MODIFIED",
                    "message": f"Updated. {new_desc}",
                    "action": self.pending_action
                }
            else:
                return {
                    "status": "MODIFIED",
                    "message": "What should the updated message say, Sir?",
                    "action": self.pending_action
                }

        # 3. Handling BLOCKED tier (Double Confirmation)
        if self.pending_action.tier == PermissionTier.BLOCKED:
            if self.is_double_confirmation(user_text):
                self.pending_action.blocked_confirm_count += 1
                if self.pending_action.blocked_confirm_count == 1:
                    return {
                        "status": "NEED_CONFIRMATION_2",
                        "message": "First confirmation accepted. For safety, please repeat: 'Yes, I'm sure' to execute.",
                        "action": self.pending_action
                    }
                elif self.pending_action.blocked_confirm_count >= 2:
                    action = self.pending_action
                    self.pending_action = None
                    log_event("PERMISSION:OVERRIDE", f"Double confirmation completed for BLOCKED action: {action.tool_name}")
                    return {"status": "APPROVED", "message": "Double confirmation verified. Executing.", "action": action}
            else:
                return {
                    "status": "UNRESOLVED",
                    "message": "This dangerous action requires you to say 'Yes, I'm sure' twice, or say 'cancel' to abort.",
                    "action": self.pending_action
                }

        # 4. Handling ASK tier
        if self.is_approval_phrase(user_text):
            action = self.pending_action
            self.pending_action = None
            log_event("PERMISSION:APPROVED", f"User approved action '{action.tool_name}'")
            return {"status": "APPROVED", "message": "Approved. Executing now.", "action": action}

        # Unclear response
        return {
            "status": "UNRESOLVED",
            "message": f"Please clarify, Sir: say 'Yes' to proceed, 'Change it to [message]' to edit, or 'Cancel' to abort.",
            "action": self.pending_action
        }
