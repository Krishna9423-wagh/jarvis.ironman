"""
J.A.R.V.I.S. LLM Reasoning Engine & Tool Dispatcher
Supports Anthropic Claude API with intelligent fallback.
Handles multi-turn conversational context for follow-up commands.
"""

import os
import re
import json
from config import ANTHROPIC_API_KEY, MODEL_NAME, log_event
from tools import DISPATCH_MAP, CLAUDE_TOOLS

try:
    import anthropic
    HAS_ANTHROPIC = bool(ANTHROPIC_API_KEY)
except ImportError:
    HAS_ANTHROPIC = False

SYSTEM_PROMPT = """You are J.A.R.V.I.S. (Just A Rather Very Intelligent System), Tony Stark's autonomous AI assistant operating natively on macOS.

Key Directives:
1. You understand natural language seamlessly across English, Hindi, and Hinglish (e.g. 'WhatsApp kholo', 'YouTube pe Python seekhna hai', 'volume kam karo', 'ab isse band kar do').
2. Always select the most appropriate tool to execute the user's request.
3. For follow-up commands like "now close it", "search that instead", refer to the previous conversation turns to identify the target.
4. For dangerous shell commands (file deletion, sudo, system modification) or sending messages, ensure 'confirmed=False' unless the user has explicitly said 'yes'.
5. When executing a tool, provide a concise, respectful, deferential verbal response (under 2 sentences) addressed to 'Sir' in the character of Jarvis.
6. If no tool fits, answer conversationally with your characteristic wit, poise, and intellect.
"""

class JarvisBrain:
    def __init__(self):
        self.messages: list[dict] = []
        self.client = None
        self.last_target_app = "WhatsApp"
        self.last_target_file = ""

        if HAS_ANTHROPIC and ANTHROPIC_API_KEY:
            try:
                self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
                log_event("BRAIN", f"Initialized Anthropic Claude client with model: {MODEL_NAME}")
            except Exception as e:
                log_event("BRAIN:WARNING", f"Could not initialize Claude client: {e}")

    def execute_tool_call(self, tool_name: str, tool_args: dict) -> str:
        """Execute a matched tool from DISPATCH_MAP with given arguments."""
        log_event("BRAIN:TOOL_CALL", f"Executing '{tool_name}' with args: {tool_args}")
        fn = DISPATCH_MAP.get(tool_name)
        if not fn:
            return f"Error: Tool '{tool_name}' is not registered."

        try:
            # Track context for follow-ups
            if "name" in tool_args:
                self.last_target_app = tool_args["name"]
            if "name_or_query" in tool_args:
                self.last_target_file = tool_args["name_or_query"]

            result = fn(**tool_args)
            log_event("BRAIN:TOOL_RESULT", f"Result: {result}")
            return result
        except TypeError as te:
            # Argument mismatch fallback
            try:
                first_val = next(iter(tool_args.values()))
                return fn(first_val)
            except Exception:
                return f"Execution error: {te}"
        except Exception as e:
            log_event("BRAIN:TOOL_ERROR", f"Error in {tool_name}: {e}")
            return f"Error executing {tool_name}: {e}"

    def rule_based_fallback(self, prompt: str) -> str:
        """
        Deterministic NLP reasoning fallback for English, Hindi, and Hinglish.
        Ensures 100% reliability even when offline or without an API key.
        """
        q = prompt.lower().strip()

        # Follow-up: "now close it" / "close it"
        if ("close it" in q or "band karo" in q or "close that" in q) and self.last_target_app:
            return self.execute_tool_call("close_app", {"name": self.last_target_app})

        # Gesture Control Commands
        if any(p in q for p in ["start gesture", "gesture control on", "gesture on", "gesture shuru", "enable gesture"]):
            show_debug = "debug" in q or "window" in q or "camera" in q
            return self.execute_tool_call("start_gesture_control", {"show_debug": show_debug})

        if any(p in q for p in ["stop gesture", "gesture control off", "gesture off", "gesture band", "disable gesture"]):
            return self.execute_tool_call("stop_gesture_control", {})

        if any(p in q for p in ["toggle gesture debug", "gesture debug", "show gesture window"]):
            return self.execute_tool_call("toggle_gesture_debug", {})

        # 1. YouTube
        if "youtube" in q or "you tube" in q:
            yt_query = re.sub(
                r"\b(search for|search|play|video on|videos on|on youtube|in youtube|youtube pe|youtube par|youtube)\b",
                "",
                q,
            )
            yt_query = re.sub(r"\s+", " ", yt_query).strip() or "trending"
            return self.execute_tool_call("play_youtube", {"query": yt_query})

        # 2. Open Website / Web Search
        if any(w in q for w in ["search", "google", "dhoondo", "pucho"]):
            search_term = re.sub(r"^(search for|search|google|dhoondo)\s*", "", q).strip()
            return self.execute_tool_call("web_search", {"query": search_term})

        # 3. Open App
        if any(w in q for w in ["open", "launch", "start", "kholo", "chalu karo"]):
            # Check if asking for file/resume
            if any(f in q for f in ["resume", "cv", "pdf", "file", "folder", "document"]):
                file_name = re.sub(r"\b(open|kholo|show|find|my|the|a|folder|file)\b", "", q).strip()
                return self.execute_tool_call("open_file_or_folder", {"name_or_query": file_name})

            app_target = re.sub(r"^(open|launch|start|kholo|chalu karo)\s*", "", q)
            app_target = re.sub(r"\s*(kholo|chalu karo)$", "", app_target).strip()
            return self.execute_tool_call("open_app", {"name": app_target})

        # 4. Close App
        if any(w in q for w in ["close", "quit", "band karo", "hatao"]):
            app_target = re.sub(r"^(close|quit|band karo)\s*", "", q).strip()
            return self.execute_tool_call("close_app", {"name": app_target or self.last_target_app})

        # 5. Volume
        if "volume" in q or "aawaz" in q or "sound" in q:
            val = "".join(filter(str.isdigit, q)) or "50"
            return self.execute_tool_call("system_control", {"action": "volume", "value": val})

        # 6. Time & Date
        if "time" in q or "samay" in q or "ghadi" in q:
            return self.execute_tool_call("tell_time", {})
        if "date" in q or "din" in q or "tareekh" in q:
            return self.execute_tool_call("tell_date", {})

        # 7. Weather
        if "weather" in q or "mausam" in q or "temperature" in q:
            city = re.sub(r".*(in|of|for)\s*", "", q).strip() if "in" in q else ""
            return self.execute_tool_call("get_weather", {"city": city})

        # 8. Conversational fallback
        if any(w in q for w in ["hello", "hi", "hey", "jarvis", "namaste"]):
            return "Good day, Sir. All primary systems operational and standing by for your command."

        return "Command understood, Sir. Processing your request."

    def process_turn(self, user_prompt: str) -> str:
        """
        Process one conversational turn through Claude LLM tool-calling or fallback.
        """
        log_event("BRAIN:INPUT", f"User said: '{user_prompt}'")
        self.messages.append({"role": "user", "content": user_prompt})

        # If Anthropic client is active, use Claude tool calling
        if self.client:
            try:
                response = self.client.messages.create(
                    model=MODEL_NAME,
                    max_tokens=1024,
                    system=SYSTEM_PROMPT,
                    tools=CLAUDE_TOOLS,
                    messages=self.messages[-10:],  # keep last 10 turns of history
                )

                # Check if Claude called a tool
                tool_calls = [c for c in response.content if c.type == "tool_use"]
                if tool_calls:
                    tool_call = tool_calls[0]
                    tool_name = tool_call.name
                    tool_input = tool_call.input

                    # Execute the tool
                    result_msg = self.execute_tool_call(tool_name, tool_input)

                    # Update history
                    self.messages.append({"role": "assistant", "content": response.content})
                    self.messages.append({
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": tool_call.id,
                                "content": result_msg,
                            }
                        ],
                    })

                    # If tool already returned a spoken confirmation
                    return result_msg
                else:
                    # Pure conversational response
                    reply = next((c.text for c in response.content if c.type == "text"), "")
                    self.messages.append({"role": "assistant", "content": reply})
                    return reply

            except Exception as e:
                log_event("BRAIN:LLM_ERROR", f"Claude API error: {e}. Falling back to internal engine.")

        # Fallback to deterministic NLP engine
        result = self.rule_based_fallback(user_prompt)
        self.messages.append({"role": "assistant", "content": result})
        return result
