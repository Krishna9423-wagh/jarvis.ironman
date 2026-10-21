import asyncio
import os
import sys
from google.antigravity import Agent, LocalAgentConfig

# ---------------------------------------------------------------------------
# J.A.R.V.I.S. Custom Agentic Tools
# ---------------------------------------------------------------------------

def get_system_status() -> str:
    """Return the current operating status and telemetry for Mark VII armor systems."""
    return "All core systems operational. CPU load: 12%. Armor integrity: 100%."

def get_arc_reactor_status() -> str:
    """Return the current power output and core temperature of the Arc Reactor."""
    return "Arc Reactor output: 8.4 GW. Core temperature: 32°C. Harmonic stability: 99.8%."

def run_radar_sweep() -> str:
    """Initiate a 360-degree perimeter radar scan for incoming threats or targets."""
    return "Perimeter scan complete. 0 hostile signatures detected within radar envelope."

# ---------------------------------------------------------------------------
# Main Execution
# ---------------------------------------------------------------------------

async def run_jarvis(prompt: str = "Perform system diagnostic."):
    api_key = (
        os.getenv("GEMINI_API_KEY")
        or os.getenv("GOOGLE_API_KEY")
        or "YOUR_GEMINI_API_KEY"
    )

    config = LocalAgentConfig(
        api_key=api_key,
        system_instructions=(
            "You are J.A.R.V.I.S. (Just A Rather Very Intelligent System), "
            "an autonomous AI assistant created by Tony Stark. "
            "You speak concisely, deferentially, and in-character as Stark's AI butler. "
            "Use your custom diagnostic tools when asked about suit status, reactor, or radar."
        ),
        tools=[get_system_status, get_arc_reactor_status, run_radar_sweep],
    )

    print("\n" + "=" * 55)
    print("  J.A.R.V.I.S. // Autonomous Google Antigravity Agent")
    print("=" * 55)
    print(f"[Query]: {prompt}\n")

    try:
        async with Agent(config) as agent:
            response = await agent.chat(prompt)
            output = await response.text()
            print(output)
            print()

    except Exception as exc:
        print(f"[JARVIS System Notice]: {exc}")
        print("\nTip: Set your Gemini API key in the environment:")
        print("  export GEMINI_API_KEY=\"your-gemini-key\"")
        print("  python3 jarvis_agent.py\n")

if __name__ == "__main__":
    query = sys.argv[1] if len(sys.argv) > 1 else "Perform system diagnostic."
    asyncio.run(run_jarvis(query))
