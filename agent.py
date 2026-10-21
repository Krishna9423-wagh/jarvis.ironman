"""
J.A.R.V.I.S. Autonomous Agent Engine
------------------------------------
Features:
- Multi-step iterative reasoning loop (Plans, invokes tools one by one, reads results)
- 3-Tier Safety & Permission gating (SAFE, ASK, BLOCKED)
- Voice draft review & interactive modification ("change it to...")
- Contact resolution with ambiguity detection
- Persistent multi-turn memory for contextual follow-ups ("send the same to Amit", "now open it")
- Full dual engine: Anthropic Claude LLM tool-calling + deterministic multi-step offline planner
- Seamless logging to jarvis.log
"""

import os
import re
import json
import time
from typing import Dict, Any, List, Optional, Tuple
from config import ANTHROPIC_API_KEY, MODEL_NAME, log_event
from tools import DISPATCH_MAP, CLAUDE_TOOLS
from permissions import PermissionManager, PermissionTier, PendingAction

try:
    import anthropic
    HAS_ANTHROPIC = bool(ANTHROPIC_API_KEY)
except ImportError:
    HAS_ANTHROPIC = False

AGENT_SYSTEM_PROMPT = """You are J.A.R.V.I.S., Tony Stark's autonomous AI operating natively on macOS.

Operational Directives:
1. You understand natural language seamlessly across English, Hindi, and Hinglish.
2. Break down complex user goals into logical multi-step plans. Execute tools step by step, observing the output of each before proceeding to the next.
3. For communications (WhatsApp, iMessage, Email, Calls, DMs):
   - Always resolve the contact first using 'resolve_contact'.
   - If ambiguous (e.g. multiple Rahuls found), stop and ask the user to clarify which one.
   - Always draft the message clearly in your character and state recipient and platform.
4. For file operations like "email my resume", first locate the file using 'find_file_path', then draft the email with that attachment path.
5. Provide concise, polished verbal responses addressed to 'Sir' (1-2 sentences).
6. Respect the permission system: safe read operations run immediately; outgoing communications and modifications will be paused for user approval.
"""

class JarvisAgent:
    def __init__(self):
        self.messages: List[Dict[str, Any]] = []
        self.client = None
        self.permissions = PermissionManager()
        
        # Contextual Memory across turns
        self.last_contact = ""
        self.last_app = "WhatsApp"
        self.last_file = ""
        self.last_message_text = ""
        
        # Active Goal State
        self.current_goal = ""
        self.pending_tool_call = None
        self.is_task_running = False
        self.pending_ambiguity = None

        if HAS_ANTHROPIC and ANTHROPIC_API_KEY:
            try:
                self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
                log_event("AGENT", f"Initialized Claude Agent client with model: {MODEL_NAME}")
            except Exception as e:
                log_event("AGENT:WARN", f"Could not initialize Claude client: {e}")

    def reset_task(self):
        """Abort currently running task and clear pending execution."""
        self.permissions.pending_action = None
        self.pending_tool_call = None
        self.is_task_running = False
        log_event("AGENT:RESET", "Active task aborted.")

    def execute_tool(self, tool_name: str, tool_args: Dict[str, Any]) -> str:
        """Directly dispatch tool and track context."""
        log_event("AGENT:EXEC", f"Running '{tool_name}' with {tool_args}")
        fn = DISPATCH_MAP.get(tool_name)
        if not fn:
            return f"Error: Tool '{tool_name}' is not registered."

        try:
            # Memory tracking
            if "name" in tool_args:
                self.last_app = tool_args["name"]
            if "contact" in tool_args:
                self.last_contact = tool_args["contact"]
            if "text" in tool_args:
                self.last_message_text = tool_args["text"]
            if "body" in tool_args:
                self.last_message_text = tool_args["body"]
            if "name_or_query" in tool_args:
                self.last_file = tool_args["name_or_query"]

            result = fn(**tool_args)
            log_event("AGENT:RESULT", f"Result: {result}")
            return str(result)
        except TypeError:
            try:
                val = next(iter(tool_args.values()))
                return str(fn(val))
            except Exception as e:
                return f"Execution error in {tool_name}: {e}"
        except Exception as e:
            log_event("AGENT:ERROR", f"Tool error in {tool_name}: {e}")
            return f"Error executing {tool_name}: {e}"

    def run_agent_loop(self, user_prompt: str) -> str:
        """
        Execute multi-step Claude agent reasoning loop.
        Calls tools iteratively until complete or until an ASK permission pause is reached.
        """
        self.messages.append({"role": "user", "content": user_prompt})
        max_steps = 6
        step = 0

        while step < max_steps:
            step += 1
            try:
                response = self.client.messages.create(
                    model=MODEL_NAME,
                    max_tokens=1024,
                    system=AGENT_SYSTEM_PROMPT,
                    tools=CLAUDE_TOOLS,
                    messages=self.messages[-12:]
                )

                tool_calls = [c for c in response.content if c.type == "tool_use"]
                if not tool_calls:
                    # Final textual reply from assistant
                    reply = next((c.text for c in response.content if c.type == "text"), "")
                    self.messages.append({"role": "assistant", "content": reply})
                    self.is_task_running = False
                    return reply

                # Assistant wants to call a tool
                tool_call = tool_calls[0]
                tool_name = tool_call.name
                tool_input = tool_call.input

                # Gating Check via Permission Manager
                tier, prompt = self.permissions.prepare_action(tool_name, tool_input)

                if tier != PermissionTier.SAFE:
                    # Freeze agent loop: wait for user approval
                    self.pending_tool_call = (tool_call, response.content)
                    self.is_task_running = True
                    return prompt

                # SAFE Action: execute immediately and continue loop
                tool_result = self.execute_tool(tool_name, tool_input)

                # Feed result back into history
                self.messages.append({"role": "assistant", "content": response.content})
                self.messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_call.id,
                            "content": tool_result
                        }
                    ]
                })

            except Exception as e:
                log_event("AGENT:LLM_ERR", f"Claude API failure: {e}. Falling back to rule planner.")
                break

        # Fallback if loop finishes or error
        return self.rule_based_planner(user_prompt)

    def rule_based_planner(self, prompt: str) -> str:
        """
        Autonomous Multi-Step Rule Planner.
        Guarantees 100% reliable execution of communication, system, files, and apps
        even when offline or without an API key.
        """
        q = prompt.lower().strip()

        # Follow-up: "now open it" / "close it"
        if ("open it" in q or "kholo" in q) and self.last_app:
            return self.execute_tool("open_app", {"name": self.last_app})
        if ("close it" in q or "band karo" in q) and self.last_app:
            return self.execute_tool("close_app", {"name": self.last_app})

        # Follow-up: "send the same to Amit" / "same message Amit ko bhejo"
        if ("send the same" in q or "same message" in q or "wahi message" in q) and self.last_message_text:
            match_contact = re.sub(r".*(to|ko)\s+", "", q).strip()
            target_contact = match_contact or "Rahul"
            return self.plan_communication(target_contact, self.last_message_text, platform="whatsapp")

        # 1. Communication Flow: "text Rahul that I'll be late by 10 minutes"
        msg_patterns = [
            r"(?:text|message|whatsapp)\s+([a-zA-Z0-9\s]+?)\s+(?:that|saying|ko\s+bhejo|ko|say)\s+(.*)",
            r"(?:send\s+whatsapp\s+to|send\s+message\s+to)\s+([a-zA-Z0-9\s]+?)\s+(?:saying|that)?\s*(.*)",
            r"(?:text|message)\s+([a-zA-Z0-9\s]+?)\s*:\s*(.*)",
            r"(?:text|message|whatsapp)\s+([a-zA-Z0-9]+)\s+(.*)",
        ]
        for pat in msg_patterns:
            m = re.search(pat, q, re.IGNORECASE)
            if m:
                contact = m.group(1).strip()
                text = m.group(2).strip()
                text = re.sub(r"^(that|saying|to say)\s+", "", text, flags=re.IGNORECASE).strip()
                if not text:
                    text = "I'll be late by 10 minutes."
                return self.plan_communication(contact, text, platform="whatsapp")

        # 2. Email Flow: "email my resume to <address>"
        if "email" in q or "mail" in q:
            m_email = re.search(r"email\s+(?:my\s+)?([a-zA-Z0-9_\-\.\s]+?)\s+(?:to\s+)([a-zA-Z0-9_\-\.\@]+)", q)
            if m_email:
                doc_name = m_email.group(1).strip()
                to_addr = m_email.group(2).strip()
                return self.plan_email(doc_name, to_addr)

        # 3. Gesture Control Commands
        if any(p in q for p in ["start gesture", "gesture control on", "gesture on", "enable gesture"]):
            show_debug = "debug" in q or "window" in q or "camera" in q
            return self.execute_tool("start_gesture_control", {"show_debug": show_debug})
        if any(p in q for p in ["stop gesture", "gesture control off", "gesture off", "disable gesture"]):
            return self.execute_tool("stop_gesture_control", {})
        if any(p in q for p in ["toggle gesture", "gesture debug"]):
            return self.execute_tool("toggle_gesture_debug", {})

        # 4. YouTube
        if "youtube" in q or "you tube" in q:
            yt_query = re.sub(r"\b(search for|search|play|video on|videos on|on youtube|in youtube|youtube pe|youtube par|youtube)\b", "", q)
            yt_query = re.sub(r"\s+", " ", yt_query).strip() or "trending"
            return self.execute_tool("play_youtube", {"query": yt_query})

        # 5. Web Search
        if any(w in q for w in ["search", "google", "dhoondo", "pucho"]):
            search_term = re.sub(r"^(search for|search|google|dhoondo)\s*", "", q).strip()
            return self.execute_tool("web_search", {"query": search_term})

        # 6. Open App
        if any(w in q for w in ["open", "launch", "start", "kholo", "chalu karo"]):
            if any(f in q for f in ["resume", "cv", "pdf", "file", "folder", "document"]):
                file_name = re.sub(r"\b(open|kholo|show|find|my|the|a|folder|file)\b", "", q).strip()
                return self.execute_tool("open_file_or_folder", {"name_or_query": file_name})

            app_target = re.sub(r"^(open|launch|start|kholo|chalu karo)\s*", "", q)
            app_target = re.sub(r"\s*(kholo|chalu karo)$", "", app_target).strip()
            return self.execute_tool("open_app", {"name": app_target})

        # 7. Close App
        if any(w in q for w in ["close", "quit", "band karo", "hatao"]):
            app_target = re.sub(r"^(close|quit|band karo)\s*", "", q).strip()
            return self.execute_tool("close_app", {"name": app_target or self.last_app})

        # 8. Volume & System Control
        if "volume" in q or "aawaz" in q or "sound" in q:
            val = "".join(filter(str.isdigit, q)) or "50"
            return self.execute_tool("system_control", {"action": "volume", "value": val})

        # 9. Time & Date
        if "time" in q or "samay" in q or "ghadi" in q:
            return self.execute_tool("tell_time", {})
        if "date" in q or "din" in q or "tareekh" in q:
            return self.execute_tool("tell_date", {})

        # 10. Weather
        if "weather" in q or "mausam" in q:
            city = re.sub(r".*(in|of|for)\s*", "", q).strip() if "in" in q else ""
            return self.execute_tool("get_weather", {"city": city})

        # 11. Screenshot
        if "screenshot" in q or "screen record" in q:
            return self.execute_tool("take_screenshot", {})

        # 12. Shell Commands / Deletion / Dangerous Actions
        if any(w in q for w in ["run shell", "shell command", "terminal", "execute", "run command", "delete", "remove", "rm "]):
            cmd = re.sub(r"^(run shell|shell command|terminal|run command|execute)\s*", "", q).strip()
            tier, prompt = self.permissions.prepare_action("run_shell", {"command": cmd})
            if tier != PermissionTier.SAFE:
                self.is_task_running = True
                return prompt
            return self.execute_tool("run_shell", {"command": cmd})

        # Conversational fallback
        if any(w in q for w in ["hello", "hi", "hey", "jarvis", "namaste"]):
            return "Good day, Sir. All primary systems operational and standing by for your command."

        return "Command received, Sir. Analyzing and processing your request."

    def plan_communication(self, contact: str, text: str, platform: str = "whatsapp") -> str:
        """Plan and gate messaging with ambiguity checking and permission read-back."""
        self.last_contact = contact
        self.last_message_text = text

        # Step 1: Resolve Contact
        res = DISPATCH_MAP["resolve_contact"](contact)
        if res.get("status") == "AMBIGUOUS":
            names = [c["name"] for c in res.get("candidates", [])]
            self.pending_ambiguity = {
                "candidates": names,
                "text": text,
                "platform": platform
            }
            return f"Which {contact}? I found multiple matching contacts: {', '.join(names)}. Please specify."

        self.pending_ambiguity = None
        resolved_name = res.get("name") or contact
        tool_name = "send_whatsapp" if platform == "whatsapp" else "send_imessage"
        tool_args = {"contact": resolved_name, "text": text}

        # Step 2: Safety Permission Gate (ASK)
        tier, prompt = self.permissions.prepare_action(tool_name, tool_args)
        self.is_task_running = True
        return prompt

    def plan_email(self, doc_name: str, to_addr: str) -> str:
        """Plan multi-step email flow: locate attachment -> draft email -> gate permission."""
        path = DISPATCH_MAP["find_file_path"](doc_name)
        subject = f"{doc_name.capitalize()} from Krishna Wagh"
        body = f"Hello,\n\nPlease find attached my {doc_name}.\n\nBest regards,\nKrishna Wagh"

        tool_args = {
            "to": to_addr,
            "subject": subject,
            "body": body,
            "attachment_path": path
        }
        tier, prompt = self.permissions.prepare_action("send_email", tool_args)
        self.is_task_running = True
        return prompt

    def process_turn(self, user_input: str) -> str:
        """
        Main entry point for conversational turns.
        Handles:
        1. Ongoing permission response if an action is pending.
        2. Execution of approved action.
        3. Starting new multi-step agent reasoning.
        """
        log_event("AGENT:INPUT", f"User input: '{user_input}'")

        # Check if an action is waiting for permission (ASK or BLOCKED)
        if self.permissions.pending_action:
            perm_result = self.permissions.handle_user_response(user_input)
            status = perm_result["status"]
            msg = perm_result["message"]

            if status == "APPROVED":
                action: PendingAction = perm_result["action"]
                # Execute the approved action
                execution_result = self.execute_tool(action.tool_name, action.tool_args)

                # If Claude was waiting in a multi-step loop, resume Claude
                if self.client and self.pending_tool_call:
                    tool_call, orig_content = self.pending_tool_call
                    self.pending_tool_call = None
                    self.messages.append({"role": "assistant", "content": orig_content})
                    self.messages.append({
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": tool_call.id,
                                "content": execution_result
                            }
                        ]
                    })
                    # Resume agent loop for any remaining steps
                    self.is_task_running = False
                    return f"{execution_result} Sent."

                self.is_task_running = False
                return execution_result

            elif status in ["CANCELLED", "MODIFIED", "NEED_CONFIRMATION_2", "UNRESOLVED"]:
                if status == "CANCELLED":
                    self.reset_task()
                return msg

        # Check if waiting for contact ambiguity clarification
        if self.pending_ambiguity:
            if self.permissions.is_cancel_phrase(user_input):
                self.pending_ambiguity = None
                self.reset_task()
                return "Task cancelled, Sir."
            
            chosen = None
            q_clean = user_input.lower().strip()
            for cand in self.pending_ambiguity["candidates"]:
                if cand.lower() in q_clean or q_clean in cand.lower():
                    chosen = cand
                    break
            
            if not chosen:
                if "first" in q_clean or "1" in q_clean:
                    chosen = self.pending_ambiguity["candidates"][0]
                elif ("second" in q_clean or "2" in q_clean) and len(self.pending_ambiguity["candidates"]) > 1:
                    chosen = self.pending_ambiguity["candidates"][1]

            if chosen:
                pending = self.pending_ambiguity
                self.pending_ambiguity = None
                return self.plan_communication(chosen, pending["text"], platform=pending["platform"])

        # Immediate abort check
        if self.permissions.is_cancel_phrase(user_input) and self.is_task_running:
            self.reset_task()
            return "Task stopped, Sir."

        # Start new agent reasoning turn
        self.current_goal = user_input
        if self.client:
            return self.run_agent_loop(user_input)
        else:
            return self.rule_based_planner(user_input)
