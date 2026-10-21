"""
J.A.R.V.I.S. Tool Registry and Claude Tool Definitions
"""

from tools.apps import open_app, close_app
from tools.browser import open_website, web_search, play_youtube
from tools.files import open_file_or_folder
from tools.system import system_control
from tools.shell import run_shell
from tools.keystrokes import type_text, press_keys
from tools.whatsapp import send_whatsapp_message
from tools.productivity import tell_time, tell_date, get_weather, set_timer, set_reminder
from tools.gestures import start_gesture_control, stop_gesture_control, toggle_gesture_debug

# Direct execution dispatch map
DISPATCH_MAP = {
    "open_app": open_app,
    "close_app": close_app,
    "open_website": open_website,
    "web_search": web_search,
    "play_youtube": play_youtube,
    "open_file_or_folder": open_file_or_folder,
    "system_control": system_control,
    "run_shell": run_shell,
    "type_text": type_text,
    "press_keys": press_keys,
    "send_whatsapp_message": send_whatsapp_message,
    "tell_time": tell_time,
    "tell_date": tell_date,
    "get_weather": get_weather,
    "set_timer": set_timer,
    "set_reminder": set_reminder,
    "start_gesture_control": start_gesture_control,
    "stop_gesture_control": stop_gesture_control,
    "toggle_gesture_debug": toggle_gesture_debug,
}

# Anthropic Claude Tool Calling Specifications
CLAUDE_TOOLS = [
    {
        "name": "open_app",
        "description": "Open any installed application on macOS (e.g. WhatsApp, Instagram, Chrome, VS Code, Notes, Spotify). Fuzzy matches if exact name differs.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "The name of the application to open, e.g. 'WhatsApp', 'Instagram', 'Chrome'."}
            },
            "required": ["name"]
        }
    },
    {
        "name": "close_app",
        "description": "Close or quit a running application on macOS (e.g. WhatsApp, Chrome).",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Name of the application to quit."}
            },
            "required": ["name"]
        }
    },
    {
        "name": "open_website",
        "description": "Open any website, URL, or service in the browser (e.g. Instagram, WhatsApp Web, YouTube, LeetCode, GitHub).",
        "input_schema": {
            "type": "object",
            "properties": {
                "url_or_query": {"type": "string", "description": "The website name or URL, e.g. 'instagram', 'https://github.com', 'leetcode'."}
            },
            "required": ["url_or_query"]
        }
    },
    {
        "name": "web_search",
        "description": "Perform a Google search for any query or topic.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search keywords."}
            },
            "required": ["query"]
        }
    },
    {
        "name": "play_youtube",
        "description": "Search and play a video or tutorial on YouTube (e.g. 'Python tutorials', 'Iron Man theme').",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The video search terms."}
            },
            "required": ["query"]
        }
    },
    {
        "name": "open_file_or_folder",
        "description": "Locate and open a personal file, resume, document, or folder on macOS using Spotlight.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name_or_query": {"type": "string", "description": "Name of the file, e.g. 'resume', 'thesis.pdf', 'Downloads'."}
            },
            "required": ["name_or_query"]
        }
    },
    {
        "name": "system_control",
        "description": "Adjust macOS system settings: volume (0-100), mute, unmute, lock screen, sleep, screenshot, wifi, battery.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Action name: 'volume', 'mute', 'unmute', 'lock_screen', 'sleep', 'screenshot', 'wifi', 'battery'."
                },
                "value": {"type": "string", "description": "Optional value, e.g. '30' for volume 30, 'on' or 'off' for wifi."}
            },
            "required": ["action"]
        }
    },
    {
        "name": "run_shell",
        "description": "Run a terminal command on macOS. Dangerous commands (rm, sudo, delete, mv) require explicit spoken confirmation.",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "The shell command line."},
                "confirmed": {"type": "boolean", "description": "True if user explicitly confirmed execution with 'yes'."}
            },
            "required": ["command"]
        }
    },
    {
        "name": "type_text",
        "description": "Type text into the active frontmost window.",
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to type."}
            },
            "required": ["text"]
        }
    },
    {
        "name": "press_keys",
        "description": "Simulate keyboard keystrokes, e.g. 'enter', 'tab', 'escape', 'command+c'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "The key or key combination to press."}
            },
            "required": ["key"]
        }
    },
    {
        "name": "send_whatsapp_message",
        "description": "Send a WhatsApp message. Requires confirmation before dispatching.",
        "input_schema": {
            "type": "object",
            "properties": {
                "contact": {"type": "string", "description": "The recipient contact name or phone number."},
                "message": {"type": "string", "description": "The text message body."},
                "confirmed": {"type": "boolean", "description": "True if user confirmed with 'yes'."}
            },
            "required": ["contact", "message"]
        }
    },
    {
        "name": "tell_time",
        "description": "Report current local time.",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "tell_date",
        "description": "Report today's full date.",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "get_weather",
        "description": "Fetch live ambient weather condition and temperature.",
        "input_schema": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "Optional city name."}
            }
        }
    },
    {
        "name": "set_timer",
        "description": "Set a timer for specified seconds.",
        "input_schema": {
            "type": "object",
            "properties": {
                "seconds": {"type": "integer", "description": "Timer duration in seconds."},
                "label": {"type": "string", "description": "Label for the timer."}
            },
            "required": ["seconds"]
        }
    },
    {
        "name": "set_reminder",
        "description": "Create a desktop reminder notification.",
        "input_schema": {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "Reminder text."},
                "time_str": {"type": "string", "description": "When to remind."}
            },
            "required": ["message"]
        }
    },
    {
        "name": "start_gesture_control",
        "description": "Start or activate the MediaPipe hand gesture control system on macOS. Supports camera debug window.",
        "input_schema": {
            "type": "object",
            "properties": {
                "show_debug": {"type": "boolean", "description": "Whether to open the OpenCV debug window."}
            }
        }
    },
    {
        "name": "stop_gesture_control",
        "description": "Stop or deactivate the MediaPipe hand gesture control system.",
        "input_schema": {"type": "object", "properties": {}}
    }
]
