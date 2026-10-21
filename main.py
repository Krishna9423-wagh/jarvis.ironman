#!/usr/bin/env python3
"""
J.A.R.V.I.S. Autonomous Agent for macOS
---------------------------------------
Features:
- Multi-Step Autonomous Reasoning & Tool Execution (agent.py)
- 3-Tier Permission System (SAFE, ASK, BLOCKED) (permissions.py)
- Voice Confirmation & Modification Flow ("Should I send it?" -> "Yes" / "Change it")
- Instant Voice Stop ("stop", "cancel", "ruko") and Keyboard Kill Switch (Ctrl+C / Esc)
- WhatsApp, iMessage, Mail, FaceTime, Spotlight & Shell Control
- Hand Gesture Module Integration (MediaPipe / OpenCV)
- Ambient Noise Calibration & Resilient STT
- Logging to jarvis.log
"""

import sys
import time
import re
import subprocess
import speech_recognition as sr
from config import VOICE_NAME, WAKE_WORD, log_event
from jarvis_voice import SoundDeviceMicrophone
from agent import JarvisAgent

def speak(text: str):
    """Vocal output using macOS built-in UK English voice."""
    clean_text = re.sub(r"[#*`_]", "", text).strip()
    log_event("VOICE:OUT", clean_text)
    try:
        subprocess.run(["say", "-v", VOICE_NAME, clean_text], check=False)
    except Exception:
        subprocess.run(["say", clean_text], check=False)

def check_macos_permissions():
    """Print required macOS permissions banner."""
    print("\n" + "=" * 68)
    print("  J.A.R.V.I.S. // macOS Autonomous Voice Assistant & Agent")
    print("=" * 68)
    print("\033[94m[REQUIRED MACOS PERMISSIONS]\033[0m")
    print("Enable the following in System Settings > Privacy & Security:")
    print("  1. Camera            -> Toggle ON for Terminal / VS Code (Hand Gestures)")
    print("  2. Accessibility     -> Toggle ON for Terminal / VS Code (Mouse Control & Keystrokes)")
    print("  3. Microphone        -> Toggle ON for Terminal / VS Code (Voice Input)")
    print("  4. Automation        -> Toggle ON for System Events, Messages, Mail, Contacts")
    print("  5. Contacts          -> Toggle ON for Terminal / VS Code (Contact Resolution)")
    print("  6. Screen Recording  -> Toggle ON if taking screenshots")
    print("=" * 68 + "\n")

def is_wake_word(text: str) -> bool:
    """Detect wake word variations (Jarvis, jarvisi, hey jarvis, etc.)."""
    pattern = r"\b(hey|hi|hello|ok|okay)?\s*(jarvis[a-z]*|jarvish|jarvys|jervis|travis|javis[a-z]*)\b"
    return bool(re.search(pattern, text, re.IGNORECASE))

def strip_wake_word(text: str) -> str:
    """Strip leading wake word to isolate user command."""
    pattern = r"^(hey|hi|hello|ok|okay)?\s*(jarvis[a-z]*|jarvish|jarvys|jervis|travis|javis[a-z]*)[,\s.:!?-]*"
    return re.sub(pattern, "", text, flags=re.IGNORECASE).strip()

def run_loop():
    check_macos_permissions()
    agent = JarvisAgent()
    recognizer = sr.Recognizer()
    recognizer.dynamic_energy_threshold = True

    with SoundDeviceMicrophone() as source:
        print("\033[93m[CALIBRATION]\033[0m Measuring ambient room noise (1 second)...")
        recognizer.adjust_for_ambient_noise(source, duration=1.0)
        log_event("MIC:CALIBRATED", f"Ambient energy threshold set to: {recognizer.energy_threshold:.2f}")
        print(f"\033[92m[READY]\033[0m Ambient energy threshold: {recognizer.energy_threshold:.2f}")

        speak("Jarvis online and listening, Sir. Say Jarvis or ask me anything.")

        active_mode = False
        consecutive_timeouts = 0

        while True:
            try:
                # If an action is waiting for user permission, keep active mode engaged
                is_awaiting_approval = bool(agent.permissions.pending_action)
                if is_awaiting_approval:
                    active_mode = True

                prompt_label = (
                    "[AWAITING PERMISSION APPROVAL: 'YES' / 'CHANGE IT' / 'CANCEL']"
                    if is_awaiting_approval
                    else ("[JARVIS ACTIVE - LISTENING...]" if active_mode else "[WAITING FOR WAKE WORD: 'JARVIS'...]")
                )
                print(f"\n\033[96m{prompt_label}\033[0m")

                timeout_val = 8.0 if active_mode else 10.0
                audio = recognizer.listen(source, timeout=timeout_val, phrase_time_limit=8.0)
                consecutive_timeouts = 0

                # Speech-to-text
                text = recognizer.recognize_google(audio, language="en-IN")
                print(f"\033[92m[HEARD]:\033[0m \"{text}\"")
                log_event("SPEECH:HEARD", text)

                # Check wake word
                wake_hit = is_wake_word(text)

                # If waiting for permission or in active conversation, user doesn't need to repeat wake word
                if not active_mode and not is_awaiting_approval and not wake_hit:
                    continue

                command = strip_wake_word(text) if wake_hit else text

                # Immediate Cancel check
                if agent.permissions.is_cancel_phrase(command) and (active_mode or is_awaiting_approval):
                    agent.reset_task()
                    reply = "Task stopped, Sir. Standing down."
                    print(f"\033[95m[JARVIS]:\033[0m {reply}")
                    speak(reply)
                    active_mode = False
                    continue

                if not command:
                    # Bare wake word spoken ("Jarvis")
                    reply = "At your service, Sir. What would you like me to do?"
                    print(f"\033[95m[JARVIS]:\033[0m {reply}")
                    speak(reply)
                    active_mode = True
                    continue

                active_mode = True
                print(f"\033[94m[PROCESSING]:\033[0m \"{command}\"")

                # Multi-step Agent Reasoning & Permission Processing
                reply = agent.process_turn(command)
                print(f"\033[95m[JARVIS]:\033[0m {reply}")
                speak(reply)

                # If an action was just gated, stay active so user can say 'Yes'
                if agent.permissions.pending_action:
                    active_mode = True

            except sr.WaitTimeoutError:
                if active_mode and not agent.permissions.pending_action:
                    consecutive_timeouts += 1
                    if consecutive_timeouts >= 2:
                        active_mode = False
                        print("\033[90m[JARVIS]: Standing down to wake-word mode.\033[0m")
                continue
            except sr.UnknownValueError:
                if active_mode:
                    print("\033[93m[RETRY]: Speech unclear. Please repeat, Sir.\033[0m")
                continue
            except sr.RequestError as e:
                log_event("MIC:ERROR", f"Network error: {e}")
                time.sleep(2)
                continue
            except KeyboardInterrupt:
                print("\n[JARVIS]: Shutting down. Goodbye, Sir.")
                speak("Shutting down. Goodbye, Sir.")
                break
            except Exception as e:
                log_event("MAIN:ERROR", str(e))
                print(f"\033[91m[ERROR]:\033[0m {e}")
                continue

def run_single(query: str):
    """Direct single command test mode."""
    check_macos_permissions()
    agent = JarvisAgent()
    print(f"\033[94m[COMMAND TEST]:\033[0m \"{query}\"")
    reply = agent.process_turn(query)
    print(f"\033[95m[JARVIS RESULT]:\033[0m {reply}")
    speak(reply)

def run_cli_session():
    """Interactive text session for rapid testing of multi-step and permission flows."""
    check_macos_permissions()
    agent = JarvisAgent()
    print("\n\033[92m[J.A.R.V.I.S. INTERACTIVE AGENT SESSION ONLINE]\033[0m")
    print("Type your goals, confirmations ('yes'), modifications ('change it to...'), or 'exit':\n")
    
    while True:
        try:
            status_prompt = "You (Pending Approval)" if agent.permissions.pending_action else "You"
            q = input(f"\033[96m{status_prompt}: \033[0m")
            if q.lower() in ["exit", "quit", "q"]:
                break
            if not q.strip():
                continue
            res = agent.process_turn(q)
            print(f"\033[95mJarvis: \033[0m{res}\n")
            speak(res)
        except (KeyboardInterrupt, EOFError):
            print("\nExiting session.")
            break

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--cli":
            run_cli_session()
        else:
            run_single(" ".join(sys.argv[1:]))
    else:
        run_loop()
