"""
J.A.R.V.I.S. Tool Registry and Claude Tool Definitions
-------------------------------------------------------
Consolidates all tools across apps, communication, screen, files, shell, system, and gestures.
"""

from tools.apps import open_app, close_app
from tools.browser import open_website, web_search, play_youtube
from tools.files import open_file_or_folder, find_file_path, read_file_content, create_file, write_code_file, summarize_document
from tools.system import system_control
from tools.shell import run_shell
from tools.keystrokes import type_text, press_keys
from tools.communication import send_whatsapp, send_imessage, send_email, make_call, send_instagram_dm, resolve_contact
from tools.screen import take_screenshot, click_screen, type_on_screen, press_key
from tools.productivity import tell_time, tell_date, get_weather, set_timer, set_reminder, add_calendar_event
from tools.gestures import start_gesture_control, stop_gesture_control, toggle_gesture_debug

# Direct execution dispatch map
DISPATCH_MAP = {
    # Apps & Browser
    "open_app": open_app,
    "close_app": close_app,
    "open_website": open_website,
    "web_search": web_search,
    "play_youtube": play_youtube,

    # Communication & Contacts
    "resolve_contact": resolve_contact,
    "send_whatsapp": send_whatsapp,
    "send_imessage": send_imessage,
    "send_email": send_email,
    "make_call": make_call,
    "send_instagram_dm": send_instagram_dm,

    # Files & Documents
    "open_file_or_folder": open_file_or_folder,
    "find_file_path": find_file_path,
    "read_file_content": read_file_content,
    "create_file": create_file,
    "write_code_file": write_code_file,
    "summarize_document": summarize_document,

    # Screen & GUI Automation
    "take_screenshot": take_screenshot,
    "click_screen": click_screen,
    "type_on_screen": type_on_screen,
    "press_key": press_key,
    "type_text": type_text,
    "press_keys": press_keys,

    # Shell & System
    "run_shell": run_shell,
    "system_control": system_control,

    # Productivity
    "tell_time": tell_time,
    "tell_date": tell_date,
    "get_weather": get_weather,
    "set_timer": set_timer,
    "set_reminder": set_reminder,
    "add_calendar_event": add_calendar_event,

    # Gestures
    "start_gesture_control": start_gesture_control,
    "stop_gesture_control": stop_gesture_control,
    "toggle_gesture_debug": toggle_gesture_debug,
}

# Anthropic Claude Tool Calling Specifications
CLAUDE_TOOLS = [
    {
        "name": "open_app",
        "description": "Open any installed application on macOS (e.g. WhatsApp, Instagram, Chrome, VS Code, Spotify). Fuzzy matches if name differs.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Application name."}
            },
            "required": ["name"]
        }
    },
    {
        "name": "close_app",
        "description": "Quit a running macOS application.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Application name to quit."}
            },
            "required": ["name"]
        }
    },
    {
        "name": "open_website",
        "description": "Open any website or URL in the default browser.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url_or_query": {"type": "string", "description": "Target website or URL."}
            },
            "required": ["url_or_query"]
        }
    },
    {
        "name": "web_search",
        "description": "Perform a Google web search.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query keywords."}
            },
            "required": ["query"]
        }
    },
    {
        "name": "play_youtube",
        "description": "Search and play a video or tutorial on YouTube.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Video search query."}
            },
            "required": ["query"]
        }
    },
    {
        "name": "resolve_contact",
        "description": "Search macOS Contacts app to resolve person name, phone numbers, and email addresses.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Name or query to look up."}
            },
            "required": ["name"]
        }
    },
    {
        "name": "send_whatsapp",
        "description": "Send a WhatsApp message. Requires user permission.",
        "input_schema": {
            "type": "object",
            "properties": {
                "contact": {"type": "string", "description": "Recipient name or phone number."},
                "text": {"type": "string", "description": "Message body."}
            },
            "required": ["contact", "text"]
        }
    },
    {
        "name": "send_imessage",
        "description": "Send an iMessage / SMS via macOS Messages. Requires user permission.",
        "input_schema": {
            "type": "object",
            "properties": {
                "contact": {"type": "string", "description": "Recipient name, phone, or Apple ID."},
                "text": {"type": "string", "description": "Message content."}
            },
            "required": ["contact", "text"]
        }
    },
    {
        "name": "send_email",
        "description": "Send an email via macOS Mail.app or SMTP. Requires user permission.",
        "input_schema": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Recipient email address or contact name."},
                "subject": {"type": "string", "description": "Email subject line."},
                "body": {"type": "string", "description": "Email body content."},
                "attachment_path": {"type": "string", "description": "Optional file path to attach."}
            },
            "required": ["to", "subject", "body"]
        }
    },
    {
        "name": "make_call",
        "description": "Place a phone or video call via FaceTime or WhatsApp. Requires user permission.",
        "input_schema": {
            "type": "object",
            "properties": {
                "contact": {"type": "string", "description": "Contact name or number."},
                "platform": {"type": "string", "enum": ["facetime", "whatsapp"], "description": "Calling platform."}
            },
            "required": ["contact"]
        }
    },
    {
        "name": "send_instagram_dm",
        "description": "Open Instagram DM and draft message to user. Requires user permission.",
        "input_schema": {
            "type": "object",
            "properties": {
                "user": {"type": "string", "description": "Instagram username."},
                "text": {"type": "string", "description": "Direct message content."}
            },
            "required": ["user", "text"]
        }
    },
    {
        "name": "open_file_or_folder",
        "description": "Locate and open a file or folder using macOS Spotlight.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name_or_query": {"type": "string", "description": "File or folder name to find and open."}
            },
            "required": ["name_or_query"]
        }
    },
    {
        "name": "find_file_path",
        "description": "Find absolute path of a file (e.g. resume.pdf) on macOS using Spotlight without opening it.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name_or_query": {"type": "string", "description": "File name query (e.g. 'resume')."}
            },
            "required": ["name_or_query"]
        }
    },
    {
        "name": "read_file_content",
        "description": "Read text content of a file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to file."}
            },
            "required": ["path"]
        }
    },
    {
        "name": "create_file",
        "description": "Create a new text or document file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path to create."},
                "content": {"type": "string", "description": "File content."}
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "take_screenshot",
        "description": "Capture screenshot of current macOS display.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "Optional file path to save screenshot."}
            }
        }
    },
    {
        "name": "click_screen",
        "description": "Click on screen at coordinates (x, y).",
        "input_schema": {
            "type": "object",
            "properties": {
                "x": {"type": "integer", "description": "X coordinate."},
                "y": {"type": "integer", "description": "Y coordinate."}
            },
            "required": ["x", "y"]
        }
    },
    {
        "name": "type_on_screen",
        "description": "Type text into active macOS window.",
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to type."}
            },
            "required": ["text"]
        }
    },
    {
        "name": "system_control",
        "description": "Control macOS system settings (volume, brightness, wifi, bluetooth, lock, sleep).",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "description": "Action: volume, brightness, wifi, bluetooth, lock, sleep."},
                "value": {"type": "string", "description": "Optional value (e.g. '30' for volume, 'on'/'off')."}
            },
            "required": ["action"]
        }
    },
    {
        "name": "run_shell",
        "description": "Run a shell command on macOS. Safety tier enforced.",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Shell command line."}
            },
            "required": ["command"]
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
        "description": "Fetch live ambient weather condition.",
        "input_schema": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "Optional city."}
            }
        }
    },
    {
        "name": "set_timer",
        "description": "Set a countdown timer in seconds.",
        "input_schema": {
            "type": "object",
            "properties": {
                "seconds": {"type": "integer", "description": "Duration in seconds."},
                "label": {"type": "string", "description": "Label."}
            },
            "required": ["seconds"]
        }
    },
    {
        "name": "set_reminder",
        "description": "Set a reminder notification in macOS Reminders.",
        "input_schema": {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "Reminder text."},
                "time_str": {"type": "string", "description": "Time reference."}
            },
            "required": ["message"]
        }
    },
    {
        "name": "add_calendar_event",
        "description": "Add an event to macOS Calendar app.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Event title."},
                "start_time": {"type": "string", "description": "Date or time."},
                "notes": {"type": "string", "description": "Optional notes."}
            },
            "required": ["title"]
        }
    },
    {
        "name": "start_gesture_control",
        "description": "Start hand gesture control with camera.",
        "input_schema": {
            "type": "object",
            "properties": {
                "show_debug": {"type": "boolean", "description": "Show OpenCV HUD window."}
            }
        }
    },
    {
        "name": "stop_gesture_control",
        "description": "Stop hand gesture control.",
        "input_schema": {"type": "object", "properties": {}}
    }
]
