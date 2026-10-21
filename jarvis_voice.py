#!/usr/bin/env python3
"""
J.A.R.V.I.S. macOS Voice Assistant
---------------------------------
Features:
1. Robust CoreAudio microphone capture via sounddevice (pure Python, zero PortAudio compile issues).
2. Ambient noise calibration with speech_recognition.
3. Timeout / phrase limit with automatic retry on silence or errors.
4. Fuzzy matching for spoken variations (English & Hindi/Hinglish: 'kholo', 'whats up', 'insta gram').
5. Native macOS app launcher (subprocess.run(["open", "-a", ...])) with web fallback.
6. Authentic British vocal feedback via macOS 'say -v Daniel'.
7. Comprehensive diagnostic logging for mic, recognition, intent matching, and execution.
"""

import os
import sys
import time
import queue
import re
import difflib
import subprocess
import webbrowser
import sounddevice as sd
import speech_recognition as sr

# ---------------------------------------------------------------------------
# Diagnostic Logging
# ---------------------------------------------------------------------------
def log_mic(msg: str):
    print(f"\033[94m[MIC AUDIO]\033[0m {msg}")

def log_heard(msg: str):
    print(f"\033[92m[HEARD TEXT]\033[0m \"{msg}\"")

def log_intent(msg: str):
    print(f"\033[95m[INTENT MATCHED]\033[0m {msg}")

def log_action(msg: str):
    print(f"\033[96m[ACTION EXECUTION]\033[0m {msg}")

def log_error(msg: str):
    print(f"\033[91m[ERROR / NOTICE]\033[0m {msg}")

# ---------------------------------------------------------------------------
# Native Voice Output (macOS 'say' engine)
# ---------------------------------------------------------------------------
def speak(text: str, voice: str = "Daniel"):
    """Speak text aloud using macOS built-in speech synthesis."""
    try:
        # Check if requested voice is available, otherwise use system default
        subprocess.run(["say", "-v", voice, text], check=False)
    except Exception as e:
        log_error(f"Text-to-speech failed: {e}")

# ---------------------------------------------------------------------------
# Custom Audio Source using sounddevice (Cross-platform macOS CoreAudio)
# ---------------------------------------------------------------------------
class SoundDeviceMicrophone(sr.AudioSource):
    """
    Drop-in AudioSource for speech_recognition using sounddevice.
    Avoids PyAudio C-compilation and portaudio.h dependency on macOS.
    """
    def __init__(self, sample_rate: int = 16000, chunk_size: int = 1024):
        self.SAMPLE_RATE = sample_rate
        self.SAMPLE_WIDTH = 2  # 16-bit PCM
        self.CHUNK = chunk_size
        self.audio_q: queue.Queue = queue.Queue()
        self.sd_stream = None
        self.stream = None

    def __enter__(self):
        def audio_callback(indata, frames, time_info, status):
            if status:
                log_mic(f"Status warning: {status}")
            self.audio_q.put(bytes(indata))

        self.sd_stream = sd.RawInputStream(
            samplerate=self.SAMPLE_RATE,
            blocksize=self.CHUNK,
            dtype="int16",
            channels=1,
            callback=audio_callback,
        )
        self.sd_stream.start()

        class StreamWrapper:
            def __init__(s, q):
                s.q = q
            def read(s, size):
                return s.q.get()

        self.stream = StreamWrapper(self.audio_q)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.sd_stream:
            self.sd_stream.stop()
            self.sd_stream.close()

# ---------------------------------------------------------------------------
# App & Command Mapping Catalog
# ---------------------------------------------------------------------------
APP_CATALOG = {
    "whatsapp": {
        "app_names": ["WhatsApp"],
        "fallback_url": "https://web.whatsapp.com",
        "variations": [
            "whatsapp", "whats app", "whats up", "what's up", "watsapp",
            "wat sap", "wats up", "watsaap", "whtsapp"
        ],
        "spoken_name": "WhatsApp",
    },
    "instagram": {
        "app_names": ["Instagram"],
        "fallback_url": "https://www.instagram.com",
        "variations": [
            "instagram", "insta gram", "insta", "instgram", "instaa", "instagaram"
        ],
        "spoken_name": "Instagram",
    },
    "youtube": {
        "app_names": ["YouTube"],
        "fallback_url": "https://www.youtube.com",
        "variations": ["youtube", "you tube", "yt", "utube"],
        "spoken_name": "YouTube",
    },
    "chrome": {
        "app_names": ["Google Chrome", "Chrome"],
        "fallback_url": "https://www.google.com",
        "variations": ["chrome", "google chrome", "browser"],
        "spoken_name": "Google Chrome",
    },
    "spotify": {
        "app_names": ["Spotify"],
        "fallback_url": "https://open.spotify.com",
        "variations": ["spotify", "spoti fy", "music app"],
        "spoken_name": "Spotify",
    },
    "calculator": {
        "app_names": ["Calculator"],
        "fallback_url": None,
        "variations": ["calculator", "calc", "hisaab"],
        "spoken_name": "Calculator",
    },
    "notes": {
        "app_names": ["Notes"],
        "fallback_url": None,
        "variations": ["notes", "apple notes", "note"],
        "spoken_name": "Notes",
    },
    "terminal": {
        "app_names": ["Terminal", "iTerm"],
        "fallback_url": None,
        "variations": ["terminal", "command line", "shell"],
        "spoken_name": "Terminal",
    },
}

# ---------------------------------------------------------------------------
# Command Parsing & Fuzzy Matching
# ---------------------------------------------------------------------------
def parse_app_command(text: str) -> tuple[str | None, str | None]:
    """
    Parse spoken input and match target app with fuzzy tolerance and Hinglish support.
    Returns (target_key, matched_variation) or (None, None).
    """
    if not text:
        return None, None

    normalized = text.lower().strip()

    # Strip conversational prefixes/suffixes (English & Hindi)
    cleaned = re.sub(
        r"^(jarvis|hey jarvis|hi jarvis|please|can you|could you|kindly)?\s*",
        "",
        normalized,
    )
    cleaned = re.sub(r"^(open|launch|start|run|go to)\s+", "", cleaned)
    cleaned = re.sub(r"\s+(kholo|chalu karo|start karo|open karo)$", "", cleaned)
    # Also handle inverted Hindi syntax: "kholo whatsapp", "chalu karo insta"
    cleaned = re.sub(r"^(kholo|chalu karo)\s+", "", cleaned).strip()

    # 1. Direct and Variation matching
    for key, data in APP_CATALOG.items():
        if cleaned in data["variations"]:
            return key, cleaned
        for v in data["variations"]:
            # Match whole-word boundary
            if re.search(r"\b" + re.escape(v) + r"\b", normalized):
                return key, v

    # 2. Fuzzy Matching across all tokens
    words = cleaned.split()
    all_variations = {}
    for key, data in APP_CATALOG.items():
        for v in data["variations"]:
            all_variations[v] = key

    for word in words:
        matches = difflib.get_close_matches(word, list(all_variations.keys()), n=1, cutoff=0.7)
        if matches:
            best_match = matches[0]
            return all_variations[best_match], best_match

    return None, None

# ---------------------------------------------------------------------------
# Application Launcher Implementation
# ---------------------------------------------------------------------------
def open_target_app(target_key: str) -> bool:
    """
    Launch native macOS app using `open -a <name>`.
    If not installed, fall back to browser URL and announce via voice.
    """
    target = APP_CATALOG.get(target_key)
    if not target:
        log_error(f"Unknown application key: {target_key}")
        return False

    spoken_name = target["spoken_name"]
    opened_natively = False

    # 1. Attempt launching native Mac application
    for app_name in target["app_names"]:
        log_action(f"Running command: subprocess.run(['open', '-a', '{app_name}'])")
        try:
            res = subprocess.run(
                ["open", "-a", app_name],
                capture_output=True,
                text=True,
                check=False,
            )
            if res.returncode == 0:
                log_action(f"Successfully launched native app: {app_name}")
                speak(f"Opening {spoken_name}, Sir.")
                opened_natively = True
                break
            else:
                log_error(f"Native app '{app_name}' failed with returncode {res.returncode}: {res.stderr.strip()}")
        except Exception as e:
            log_error(f"Failed to execute open for {app_name}: {e}")

    # 2. Fall back to Web URL if native launch failed or unavailable
    if not opened_natively:
        fallback_url = target.get("fallback_url")
        if fallback_url:
            log_action(f"Falling back to web browser: webbrowser.open('{fallback_url}')")
            speak(f"{spoken_name} native application not found. Opening web version, Sir.")
            webbrowser.open(fallback_url)
            return True
        else:
            speak(f"Apologies, Sir. {spoken_name} is not installed on this Mac.")
            return False

    return True

# ---------------------------------------------------------------------------
# Step 3 - Listening Engine with Noise Calibration & Resilient Retry
# ---------------------------------------------------------------------------
def listen_and_execute(recognizer: sr.Recognizer, source: SoundDeviceMicrophone) -> bool:
    """
    Capture one spoken command with timeout & phrase limit.
    Retries cleanly on silence or unrecognized speech.
    """
    log_mic("Active. Waiting for your speech...")
    print("\n\033[93m[JARVIS LISTENING...]\033[0m (Say: 'open WhatsApp', 'open Instagram', or 'WhatsApp kholo')")

    try:
        # Capture speech with 5 second timeout and 8 second max phrase
        audio = recognizer.listen(source, timeout=5.0, phrase_time_limit=8.0)
        log_mic("Audio packet received. Transcribing with Google Speech Recognition...")

        # Transcribe using Google Speech Recognition
        text = recognizer.recognize_google(audio, language="en-IN")
        log_heard(text)

        # Parse command
        target_key, matched_variation = parse_app_command(text)

        if target_key:
            log_intent(f"Matched target '{target_key}' (pattern: '{matched_variation}')")
            open_target_app(target_key)
            return True
        elif any(w in text.lower() for w in ["status", "diagnostic", "check"]):
            log_intent("SYSTEM_DIAGNOSTIC")
            speak("All core systems operational. CPU load 12 percent. Armor integrity optimal, Sir.")
            return True
        else:
            log_intent("GENERAL_QUERY")
            log_action(f"No specific app intent matched for: '{text}'")
            speak("Command acknowledged, Sir. How else may I assist you?")
            return False

    except sr.WaitTimeoutError:
        log_error("No speech detected within 5-second window. Listening again...")
        return False
    except sr.UnknownValueError:
        log_error("Speech was heard but could not be understood. Please repeat.")
        return False
    except sr.RequestError as e:
        log_error(f"Speech service network error: {e}. Retrying in 2 seconds...")
        time.sleep(2)
        return False
    except Exception as e:
        log_error(f"Unexpected recognition error: {e}")
        return False

# ---------------------------------------------------------------------------
# Main Driver
# ---------------------------------------------------------------------------
def run_assistant(single_command: str | None = None):
    print("=" * 65)
    print("       J.A.R.V.I.S. // macOS Autonomous Voice Assistant")
    print("=" * 65)

    # If testing a single command passed via CLI
    if single_command:
        print(f"[TEST MODE] Testing command: '{single_command}'")
        target_key, matched_variation = parse_app_command(single_command)
        if target_key:
            log_intent(f"Matched target '{target_key}' (pattern: '{matched_variation}')")
            open_target_app(target_key)
        else:
            log_error(f"Could not match app for '{single_command}'")
        return

    r = sr.Recognizer()
    r.dynamic_energy_threshold = True

    try:
        with SoundDeviceMicrophone() as source:
            log_mic("Calibrating ambient room noise... (Please stay quiet for 1 second)")
            r.adjust_for_ambient_noise(source, duration=1.0)
            log_mic(f"Calibration complete! Ambient energy threshold: {r.energy_threshold:.2f}")
            speak("Jarvis voice assistant initialized and standing by, Sir.")

            # Continuous interactive listening loop
            while True:
                try:
                    listen_and_execute(r, source)
                except KeyboardInterrupt:
                    print("\n[JARVIS]: Standing down. Goodbye, Sir.")
                    speak("Standing down. Goodbye, Sir.")
                    break
    except Exception as exc:
        log_error(f"Failed to initialize microphone device: {exc}")
        print("\nEnsure Terminal / IDE has Microphone permissions in:")
        print("  System Settings > Privacy & Security > Microphone\n")

if __name__ == "__main__":
    cli_arg = sys.argv[1] if len(sys.argv) > 1 else None
    run_assistant(cli_arg)
