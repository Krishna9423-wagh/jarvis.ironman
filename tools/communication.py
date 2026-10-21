"""
J.A.R.V.I.S. Communication Tools for macOS
------------------------------------------
Features:
- macOS Contacts integration with ambiguity resolution
- WhatsApp messaging (WhatsApp Desktop URI & Web automation)
- iMessage via AppleScript (Messages.app)
- Email sending via macOS Mail.app or SMTP fallback
- Calls via FaceTime & WhatsApp
- Instagram direct messages
"""

import re
import urllib.parse
import subprocess
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os
from pathlib import Path
from config import log_event

def resolve_contact(name: str) -> dict:
    """
    Search macOS Contacts app for contact matching 'name'.
    Returns dictionary with match status, ambiguous candidates, phone, and email.
    """
    clean_name = re.sub(r"[^\w\s]", "", name).strip()
    if not clean_name:
        return {"status": "NOT_FOUND", "candidates": [], "phone": "", "email": "", "name": ""}

    scpt = """
    on run argv
        set query to item 1 of argv
        tell application "Contacts"
            set matched to (every person whose name contains query)
            set res to {}
            repeat with p in matched
                set pName to name of p
                set pPhone to ""
                try
                    set pPhone to value of first phone of p
                end try
                set pEmail to ""
                try
                    set pEmail to value of first email of p
                end try
                set end of res to pName & "|" & pPhone & "|" & pEmail
            end repeat
            return res
        end tell
    end run
    """
    try:
        proc = subprocess.run(["osascript", "-e", scpt, clean_name], capture_output=True, text=True, timeout=5)
        raw_output = proc.stdout.strip()
        if not raw_output:
            return {"status": "NOT_FOUND", "candidates": [], "phone": "", "email": "", "name": clean_name}

        entries = [e.strip() for e in raw_output.split(", ") if e.strip()]
        candidates = []
        for entry in entries:
            parts = entry.split("|")
            p_name = parts[0].strip() if len(parts) > 0 else clean_name
            p_phone = parts[1].strip() if len(parts) > 1 else ""
            p_email = parts[2].strip() if len(parts) > 2 else ""
            candidates.append({"name": p_name, "phone": p_phone, "email": p_email})

        if len(candidates) == 1:
            return {
                "status": "EXACT",
                "name": candidates[0]["name"],
                "phone": candidates[0]["phone"],
                "email": candidates[0]["email"],
                "candidates": candidates
            }
        elif len(candidates) > 1:
            # Check if one is an exact whole-word match
            exact_matches = [c for c in candidates if c["name"].lower() == clean_name.lower()]
            if len(exact_matches) == 1:
                return {
                    "status": "EXACT",
                    "name": exact_matches[0]["name"],
                    "phone": exact_matches[0]["phone"],
                    "email": exact_matches[0]["email"],
                    "candidates": candidates
                }
            return {
                "status": "AMBIGUOUS",
                "name": clean_name,
                "candidates": candidates,
                "phone": "",
                "email": ""
            }

        return {"status": "NOT_FOUND", "candidates": [], "phone": "", "email": "", "name": clean_name}

    except Exception as e:
        log_event("CONTACT:ERR", f"Contacts lookup failed: {e}")
        return {"status": "ERROR", "error": str(e), "candidates": [], "phone": "", "email": "", "name": clean_name}


def send_whatsapp(contact: str, text: str) -> str:
    """
    Send WhatsApp message to recipient.
    Resolves contact phone number from Mac Contacts.
    """
    log_event("WHATSAPP:DRAFT", f"Recipient: {contact}, Message: {text}")
    res = resolve_contact(contact)
    
    phone = ""
    # If contact argument is already digits or phone
    clean_digits = re.sub(r"[^\d+]", "", contact)
    if len(clean_digits) >= 10:
        phone = clean_digits
    elif res.get("status") == "AMBIGUOUS":
        c_names = [c["name"] for c in res.get("candidates", [])]
        return f"Ambiguous recipient: Found multiple contacts: {', '.join(c_names)}. Which one should I message?"
    elif res.get("phone"):
        phone = re.sub(r"[^\d+]", "", res["phone"])

    # Fallback to direct app opening with search if no phone found
    encoded_text = urllib.parse.quote(text)
    
    if phone:
        # Standardize country code (defaults to +91 if 10-digit Indian number)
        if len(phone) == 10 and not phone.startswith("+"):
            phone = "+91" + phone
            
        url = f"whatsapp://send?phone={phone}&text={encoded_text}"
        try:
            subprocess.run(["open", url], check=False)
            time.sleep(1.0)
            # Press enter via AppleScript to confirm send
            press_enter_scpt = 'tell application "System Events" to key code 36'
            subprocess.run(["osascript", "-e", press_enter_scpt], check=False)
            log_event("WHATSAPP:SENT", f"Dispatched to {phone}")
            return f"Sent WhatsApp message to {res.get('name', contact)}."
        except Exception as e:
            # Web fallback
            web_url = f"https://web.whatsapp.com/send?phone={phone}&text={encoded_text}"
            subprocess.run(["open", web_url], check=False)
            return f"Opened WhatsApp Web draft for {contact}."

    # If no phone found in contacts, open WhatsApp and search contact
    subprocess.run(["open", "-a", "WhatsApp"], check=False)
    time.sleep(1.5)
    # Search contact name in WhatsApp and type message
    scpt = f"""
    tell application "System Events"
        tell process "WhatsApp"
            set frontmost to true
            keystroke "f" using {{command down}}
            delay 0.5
            keystroke "{contact}"
            delay 0.8
            key code 36 -- Enter to select contact
            delay 0.5
            keystroke "{text}"
            delay 0.5
            key code 36 -- Enter to send
        end tell
    end tell
    """
    try:
        subprocess.run(["osascript", "-e", scpt], check=False)
        return f"Sent WhatsApp message to {contact}."
    except Exception as e:
        return f"Opened WhatsApp for {contact}. Could not auto-press send: {e}"


def send_imessage(contact: str, text: str) -> str:
    """Send iMessage via macOS Messages.app."""
    log_event("IMESSAGE:DRAFT", f"Recipient: {contact}, Message: {text}")
    res = resolve_contact(contact)
    target = contact
    
    if res.get("status") == "AMBIGUOUS":
        names = [c["name"] for c in res.get("candidates", [])]
        return f"Ambiguous recipient: Found {', '.join(names)}. Which one did you mean?"
    elif res.get("phone"):
        target = res["phone"]
    elif res.get("email"):
        target = res["email"]

    escaped_text = text.replace('"', '\\"')
    scpt = f"""
    tell application "Messages"
        try
            set targetService to 1st account whose service type = iMessage
            set targetBuddy to participant "{target}" of targetService
            send "{escaped_text}" to targetBuddy
            return "SUCCESS"
        on error err
            return "ERROR: " & err
        end try
    end tell
    """
    out = subprocess.run(["osascript", "-e", scpt], capture_output=True, text=True)
    if "SUCCESS" in out.stdout:
        log_event("IMESSAGE:SENT", f"Sent to {target}")
        return f"Sent iMessage to {res.get('name', contact)}: '{text}'."
    else:
        # Fallback using SMS service
        sms_scpt = f"""
        tell application "Messages"
            try
                set targetService to 1st service whose service type = SMS
                set targetBuddy to participant "{target}" of targetService
                send "{escaped_text}" to targetBuddy
                return "SUCCESS"
            on error err
                return "ERROR: " & err
            end try
        end tell
        """
        out2 = subprocess.run(["osascript", "-e", sms_scpt], capture_output=True, text=True)
        if "SUCCESS" in out2.stdout:
            return f"Sent message to {res.get('name', contact)}."
        return f"Could not send message to {contact}: {out.stdout.strip() or out2.stdout.strip()}"


def send_email(to: str, subject: str, body: str, attachment_path: str = "") -> str:
    """Send an email using macOS Mail.app or SMTP fallback."""
    log_event("EMAIL:DRAFT", f"To: {to}, Subject: {subject}")
    
    # Check if 'to' is a contact name instead of email
    if "@" not in to:
        res = resolve_contact(to)
        if res.get("email"):
            to = res["email"]
        elif res.get("status") == "AMBIGUOUS":
            names = [c["name"] for c in res.get("candidates", [])]
            return f"Ambiguous contact: Found multiple emails for: {', '.join(names)}. Which one should I email?"

    # Check for SMTP credentials in environment
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    smtp_user = os.getenv("SMTP_USER") or os.getenv("EMAIL_USER") or ""
    smtp_pass = os.getenv("SMTP_PASSWORD") or os.getenv("EMAIL_APP_PASSWORD") or ""

    if smtp_user and smtp_pass:
        try:
            msg = MIMEMultipart()
            msg["From"] = smtp_user
            msg["To"] = to
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))

            if attachment_path and os.path.exists(attachment_path):
                with open(attachment_path, "rb") as f:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(f.read())
                    encoders.encode_base64(part)
                    part.add_header("Content-Disposition", f"attachment; filename={Path(attachment_path).name}")
                    msg.attach(part)

            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, to, msg.as_string())
            server.quit()
            log_event("EMAIL:SENT", f"Sent via SMTP to {to}")
            return f"Email sent successfully to {to}."
        except Exception as e:
            log_event("EMAIL:SMTP_ERR", f"SMTP failed: {e}. Falling back to macOS Mail app.")

    # macOS Mail.app AppleScript dispatch
    escaped_sub = subject.replace('"', '\\"')
    escaped_body = body.replace('"', '\\"').replace("\n", "\\n")
    attach_clause = ""
    if attachment_path and os.path.exists(attachment_path):
        abs_path = os.path.abspath(attachment_path)
        attach_clause = f'make new attachment with properties {{file name:POSIX file "{abs_path}"}} at after the last paragraph'

    scpt = f"""
    tell application "Mail"
        set newMsg to make new outgoing message with properties {{subject:"{escaped_sub}", content:"{escaped_body}", visible:true}}
        tell newMsg
            make new to recipient at end of to recipients with properties {{address:"{to}"}}
            {attach_clause}
            send
        end tell
    end tell
    """
    try:
        proc = subprocess.run(["osascript", "-e", scpt], capture_output=True, text=True)
        if proc.returncode == 0:
            log_event("EMAIL:SENT", f"Sent via Mail.app to {to}")
            return f"Email with subject '{subject}' sent to {to} via Mail."
        return f"Mail app error: {proc.stderr.strip()}"
    except Exception as e:
        return f"Failed to send email to {to}: {e}"


def make_call(contact: str, platform: str = "facetime") -> str:
    """Place a FaceTime or WhatsApp audio/video call."""
    res = resolve_contact(contact)
    target = contact
    
    if res.get("status") == "AMBIGUOUS":
        names = [c["name"] for c in res.get("candidates", [])]
        return f"Ambiguous contact: Found {', '.join(names)}. Who would you like to call?"
    elif res.get("phone"):
        target = res["phone"]
    elif res.get("email"):
        target = res["email"]

    clean_target = re.sub(r"[^\w@.+]", "", target)

    if platform.lower() == "whatsapp":
        digits = re.sub(r"[^\d+]", "", target)
        subprocess.run(["open", f"whatsapp://call?phone={digits}"], check=False)
        return f"Initiated WhatsApp call to {res.get('name', contact)}."
    else:
        # Default FaceTime
        subprocess.run(["open", f"facetime://{clean_target}"], check=False)
        return f"Initiated FaceTime call to {res.get('name', contact)}."


def send_instagram_dm(user: str, text: str) -> str:
    """Open Instagram Direct message draft."""
    clean_user = re.sub(r"[@\s]", "", user)
    url = f"https://www.instagram.com/direct/t/{clean_user}/"
    subprocess.run(["open", url], check=False)
    return f"Opened Instagram Direct conversation with @{clean_user}."
