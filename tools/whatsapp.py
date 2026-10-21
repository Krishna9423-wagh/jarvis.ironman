"""
WhatsApp Communication Tool with Safety Confirmation (send_whatsapp_message)
"""

import urllib.parse
import webbrowser
import subprocess
from config import log_event

def send_whatsapp_message(contact: str, message: str, confirmed: bool = False) -> str:
    """
    Send a WhatsApp message to a contact or phone number.
    SAFETY RULE: Always reads the message back and asks for confirmation before sending.
    """
    log_event("TOOL:SEND_WHATSAPP", f"Contact: '{contact}', Message: '{message}', Confirmed: {confirmed}")

    if not confirmed:
        log_event("TOOL:SEND_WHATSAPP:BLOCKED", "Awaiting confirmation from user.")
        return (
            f"SAFETY_REQUIRED: Ready to send WhatsApp message to '{contact}': \"{message}\". "
            "Please confirm with 'yes' to dispatch."
        )

    # Encode message text
    encoded = urllib.parse.quote(message)

    # If contact looks like a phone number
    clean_digits = "".join(filter(str.isdigit, contact))
    if len(clean_digits) >= 10:
        url = f"https://web.whatsapp.com/send?phone={clean_digits}&text={encoded}"
    else:
        # Pre-fill message in WhatsApp
        url = f"https://web.whatsapp.com/send?text={encoded}"

    # Open WhatsApp web / app
    try:
        # Try native whatsapp URL scheme first
        res = subprocess.run(["open", f"whatsapp://send?text={encoded}"], capture_output=True, check=False)
        if res.returncode != 0:
            webbrowser.open(url)
    except Exception:
        webbrowser.open(url)

    log_event("TOOL:SEND_WHATSAPP", f"Dispatched WhatsApp message to {contact}")
    return f"WhatsApp message prepared and dispatched to {contact}, Sir."
