"""
Terminal Shell Execution Tool with Safety Gating (run_shell)
"""

import re
import subprocess
from config import log_event, DANGEROUS_SHELL_PATTERNS

def is_dangerous(command: str) -> bool:
    """Check if shell command contains destructive or privileged operations."""
    for pattern in DANGEROUS_SHELL_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return True
    return False

def run_shell(command: str, confirmed: bool = False) -> str:
    """
    Execute a shell command in the terminal.
    Requires spoken confirmation before executing anything destructive (rm, sudo, mv, install, kill).
    """
    log_event("TOOL:RUN_SHELL", f"Command: '{command}', Confirmed: {confirmed}")

    if is_dangerous(command) and not confirmed:
        log_event("TOOL:RUN_SHELL:BLOCKED", f"Safety confirmation required for command: '{command}'")
        return (
            f"SAFETY_REQUIRED: This command may modify system files or delete data ('{command}'). "
            "Please confirm with 'yes' to proceed."
        )

    try:
        res = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        output = res.stdout.strip() or res.stderr.strip()
        if not output:
            output = "Command executed successfully with zero output."

        # Keep output concise for vocal delivery
        first_few = output.splitlines()[:3]
        summary = " ".join(first_few)[:200]
        log_event("TOOL:RUN_SHELL", f"Result code {res.returncode}: {summary}")
        return f"Execution completed: {summary}"

    except subprocess.TimeoutExpired:
        log_event("TOOL:RUN_SHELL:ERROR", "Command timed out after 15 seconds.")
        return "Command execution timed out after 15 seconds, Sir."
    except Exception as e:
        log_event("TOOL:RUN_SHELL:ERROR", f"Shell execution error: {e}")
        return f"Shell execution failed: {e}"
