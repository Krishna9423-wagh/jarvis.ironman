"""
Configuration and logging setup for J.A.R.V.I.S.
"""

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Base directory of the repository
BASE_DIR = Path(__file__).resolve().parent

# Load environment variables (.env, then .env.local)
load_dotenv(BASE_DIR / ".env")
load_dotenv(BASE_DIR / ".env.local", override=True)

# API Keys
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY") or os.getenv("CLAUDE_API_KEY") or ""
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""

# LLM Model Settings
MODEL_NAME = os.getenv("JARVIS_MODEL", "claude-3-5-sonnet-20241022")

# Voice and Audio
VOICE_NAME = os.getenv("JARVIS_VOICE", "Daniel")  # High quality British UK voice on macOS
WAKE_WORD = os.getenv("JARVIS_WAKE_WORD", "jarvis").lower()

# Safety & Confirmation Settings
DANGEROUS_SHELL_PATTERNS = [
    r"\brm\b", r"\bdelete\b", r"\bdrop\b", r"\bmv\b", r"\bsudo\b",
    r"\bkill\b", r"\bshutdown\b", r"\breboot\b", r"\bchmod\b", r"\bchown\b"
]

# File Logging Setup
LOG_FILE = BASE_DIR / "jarvis.log"

logger = logging.getLogger("JARVIS")
logger.setLevel(logging.INFO)

# File handler
file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
file_handler.setLevel(logging.INFO)
file_fmt = logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
file_handler.setFormatter(file_fmt)

# Console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_fmt = logging.Formatter("\033[90m[%(asctime)s]\033[0m %(message)s", datefmt="%H:%M:%S")
console_handler.setFormatter(console_fmt)

if not logger.handlers:
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

def log_event(category: str, message: str):
    """Structured event logging."""
    logger.info(f"[{category}] {message}")
