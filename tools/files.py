"""
File and Folder Controller Tools
--------------------------------
Features:
- Find and open files using macOS Spotlight (`mdfind`)
- Locate file paths for email attachments or inspection
- Read text, code, or markdown files
- Create documents and write code files
- Summarize document contents
"""

import os
import subprocess
from pathlib import Path
from config import log_event

EXCLUDE_PATTERNS = ["node_modules", ".git", ".cache", "Library", "site-packages"]

def find_file_path(name_or_query: str) -> str:
    """Locate full absolute path of a file on macOS using Spotlight."""
    query = name_or_query.strip()
    expanded = Path(os.path.expanduser(query))
    if expanded.exists():
        return str(expanded.resolve())

    home = os.path.expanduser("~")
    cmd = ["mdfind", "-onlyin", home, f"kMDItemFSName == '*{query}*'cd"]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        lines = [l.strip() for l in res.stdout.splitlines() if l.strip()]
        valid_paths = [p for p in lines if not any(exc in p for exc in EXCLUDE_PATTERNS) and os.path.exists(p)]
        
        if not valid_paths:
            res_broad = subprocess.run(["mdfind", query], capture_output=True, text=True, check=False)
            valid_paths = [
                l.strip() for l in res_broad.stdout.splitlines()
                if l.strip() and not any(exc in l for exc in EXCLUDE_PATTERNS) and os.path.exists(l.strip())
            ]

        if valid_paths:
            def score_path(p: str):
                prio = 2
                if "/Documents/" in p or "/Desktop/" in p or "/Downloads/" in p:
                    prio = 0
                elif not any(c in p for c in ["node_modules", ".git", "venv"]):
                    prio = 1
                return (prio, len(p))
            return min(valid_paths, key=score_path)
    except Exception as e:
        log_event("FILES:ERR", f"Spotlight search error: {e}")
    return ""

def open_file_or_folder(name_or_query: str) -> str:
    """Find and open file or folder using macOS Spotlight."""
    log_event("TOOL:OPEN_FILE", f"Searching for file/folder: '{name_or_query}'")
    path = find_file_path(name_or_query)
    if path and os.path.exists(path):
        subprocess.run(["open", path], check=False)
        log_event("TOOL:OPEN_FILE", f"Opened '{path}'")
        return f"Found and opened '{Path(path).name}', Sir."
    return f"I could not locate any file or folder named '{name_or_query}' on your Mac, Sir."

def read_file_content(path: str) -> str:
    """Read textual content of a file."""
    full_path = find_file_path(path) or path
    if not os.path.exists(full_path):
        return f"File '{path}' does not exist, Sir."
    try:
        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read(4000)
        return f"Content of '{Path(full_path).name}':\n{content}"
    except Exception as e:
        return f"Could not read file: {e}"

def create_file(path: str, content: str) -> str:
    """Create a new file with specified content."""
    p = Path(os.path.expanduser(path))
    p.parent.mkdir(parents=True, exist_ok=True)
    try:
        p.write_text(content, encoding="utf-8")
        log_event("FILE:CREATE", f"Created file {p}")
        return f"Successfully created file '{p.name}'."
    except Exception as e:
        return f"Failed to create file: {e}"

def write_code_file(path: str, code: str) -> str:
    """Write source code to a file."""
    return create_file(path, code)

def summarize_document(path: str) -> str:
    """Read document and provide a concise summary."""
    content = read_file_content(path)
    if content.startswith("File '"):
        return content
    preview = content[:500] + ("..." if len(content) > 500 else "")
    return f"Document summary for '{Path(path).name}':\n{preview}"
