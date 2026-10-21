"""
File and Folder Controller Tool (open_file_or_folder using Spotlight)
"""

import os
import subprocess
from pathlib import Path
from config import log_event

EXCLUDE_PATTERNS = ["node_modules", ".git", ".cache", "Library", "site-packages"]

def open_file_or_folder(name_or_query: str) -> str:
    """
    Find files or folders by name using macOS Spotlight (`mdfind`) and open the best match.
    """
    log_event("TOOL:OPEN_FILE", f"Searching for file/folder: '{name_or_query}'")
    query = name_or_query.strip()

    # 1. Check if direct valid path
    expanded = Path(os.path.expanduser(query))
    if expanded.exists():
        subprocess.run(["open", str(expanded)], check=False)
        log_event("TOOL:OPEN_FILE", f"Opened direct path: {expanded}")
        return f"Opened {expanded.name}, Sir."

    # 2. Spotlight search
    home = os.path.expanduser("~")
    cmd = ["mdfind", "-onlyin", home, f"kMDItemFSName == '*{query}*'cd"]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        lines = [line.strip() for line in res.stdout.splitlines() if line.strip()]

        # Filter out noisy directories and ensure path exists
        valid_paths = []
        for p in lines:
            if not any(exc in p for exc in EXCLUDE_PATTERNS) and os.path.exists(p):
                valid_paths.append(p)

        if not valid_paths:
            # Broader spotlight search
            res_broad = subprocess.run(["mdfind", query], capture_output=True, text=True, check=False)
            valid_paths = [
                line.strip()
                for line in res_broad.stdout.splitlines()
                if line.strip() and not any(exc in line for exc in EXCLUDE_PATTERNS) and os.path.exists(line.strip())
            ]

        if valid_paths:
            # Prefer user Documents, Desktop, Downloads over arbitrary code folders
            def score_path(p: str) -> tuple[int, int]:
                priority = 2
                if "/Documents/" in p or "/Desktop/" in p or "/Downloads/" in p:
                    priority = 0
                elif not any(c in p for c in ["node_modules", ".git", "venv"]):
                    priority = 1
                return (priority, len(p))

            best_match = min(valid_paths, key=score_path)
            subprocess.run(["open", best_match], check=False)
            filename = Path(best_match).name
            log_event("TOOL:OPEN_FILE", f"Spotlight matched: '{best_match}'")
            return f"Found and opened '{filename}', Sir."
        else:
            log_event("TOOL:OPEN_FILE:ERROR", f"No file or folder matching '{query}' found.")
            return f"I could not locate any file or folder named '{query}' on your Mac, Sir."

    except Exception as e:
        log_event("TOOL:OPEN_FILE:ERROR", f"Spotlight search error: {e}")
        return f"Encountered an error searching for '{query}', Sir."
