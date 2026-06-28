"""
WasteGuard Society AI — Google Antigravity Agent
==================================================
This script demonstrates the Google Antigravity SDK integrated with:

  1. The WasteGuard MCP Server (mcp_server/waste_mcp_server.py)
     → Gives the agent 5 tools: detect_waste, classify_waste, create_ticket,
       get_dashboard_stats, send_whatsapp_alert

  2. A custom WasteGuard Agent Skill (skills/wasteguard/SKILL.md)
     → Gives the agent domain expertise in society waste management,
       classification rules, alert routing, and reply formatting

Together, this creates an Antigravity-powered AI agent that can:
  - Analyse a waste image end-to-end
  - Classify waste type and urgency automatically
  - Create a complaint ticket in the database
  - Send WhatsApp alerts to the right stakeholders
  - Answer questions about waste management and complaint status

Requirements:
  pip install google-antigravity
  pip install -r requirements_mcp.txt  (for the MCP server)

  Set GEMINI_API_KEY in your .env file or environment:
    export GEMINI_API_KEY=your_key_here

Usage:
  # Interactive mode — chat with the WasteGuard agent in your terminal
  python antigravity_agent.py

  # Single query mode — useful for quick tests
  python antigravity_agent.py --query "How many open tickets are there?"

  # Analyse a specific image
  python antigravity_agent.py --query "Detect and classify waste in data/inputImage.jpg and create a ticket for +919876543210"
"""

import os
import sys
import asyncio
import argparse

from dotenv import load_dotenv

# Load environment variables (.env file must contain GEMINI_API_KEY)
load_dotenv()

# ── Validate API key before starting ─────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
if not GEMINI_API_KEY:
    print(
        "❌  GEMINI_API_KEY not found in environment.\n"
        "    Add it to your .env file:\n"
        "      GEMINI_API_KEY=your_key_here\n"
        "    Get a free key at: https://aistudio.google.com/app/api-keys"
    )
    sys.exit(1)

from google.antigravity import Agent, LocalAgentConfig, types

# ── Paths ─────────────────────────────────────────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# Path to the MCP server script (exposes WasteGuard tools to the agent)
MCP_SERVER_SCRIPT = os.path.join(PROJECT_ROOT, "mcp_server", "waste_mcp_server.py")

# Path to the skills directory (contains skills/wasteguard/SKILL.md)
SKILLS_DIR = os.path.join(PROJECT_ROOT, "skills")


def build_agent_config() -> LocalAgentConfig:
    """
    Build the LocalAgentConfig for the WasteGuard Antigravity agent.

    Configuration includes:
      - System instructions: WasteGuard persona and operating rules
      - MCP server: WasteGuard pipeline tools via stdio transport
      - Skills: WasteGuard domain expertise loaded from skills/wasteguard/SKILL.md
    """

    # ── System instructions ────────────────────────────────────────────────────
    # These define the agent's persona, scope, and operating principles.
    system_instructions = """
You are WasteGuard Society AI — an intelligent waste management assistant for
Greenview Heights residential society (400 families).

Your purpose is to help residents report waste, get disposal guidance, and
track complaints — and to help the RWA and guards manage waste incidents.

You have access to WasteGuard tools via the MCP server to detect waste, classify waste, create tickets, view dashboard stats, and send WhatsApp alerts. Use the exact tool names provided in your environment.

Your WasteGuard skill (loaded from skills/wasteguard/) gives you full domain
expertise — use it for classification rules, alert routing, and reply formatting.

Operating principles:
  1. Always be warm, helpful, and civic-minded
  2. For waste images, run the full pipeline: detect → classify → ticket → alert
  3. Use urgency rules strictly (Critical/High → alert Guard + RWA, Medium → Guard only)
  4. Never skip creating a ticket — accountability is core to this system
  5. Format resident replies using the template in your WasteGuard skill
  6. If no GEMINI_API_KEY or Twilio credentials are set, work in demo mode and
     explain what would happen in a live deployment
  7. When asked for dashboard stats, always use the get_dashboard_stats tool. You can pass '24h', '7d', or 'all' based on the user's request. Do NOT attempt to run terminal commands to fetch stats manually.
  8. If you need to gather information from the user (like details for a ticket), ask them directly in your normal text response. Do NOT use the `ask_question` tool for free-text inputs.
""".strip()

    # ── MCP Server configuration ───────────────────────────────────────────────
    # The Antigravity SDK launches waste_mcp_server.py as a subprocess and
    # communicates with it via stdio transport. This gives the agent access
    # to all 5 WasteGuard tools automatically.
    mcp_servers = [
        types.McpStdioServer(
            name="waste_mcp",
            command=sys.executable,          # Use the current Python environment
            args=[MCP_SERVER_SCRIPT],        # Launch the WasteGuard MCP server
            env={
                # Pass through all relevant environment variables to the MCP server
                "GROQ_API_KEY":         os.getenv("GROQ_API_KEY", ""),
                "TWILIO_ACCOUNT_SID":   os.getenv("TWILIO_ACCOUNT_SID", ""),
                "TWILIO_AUTH_TOKEN":    os.getenv("TWILIO_AUTH_TOKEN", ""),
                "TWILIO_WHATSAPP_FROM": os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886"),
                "RWA_WHATSAPP_NUMBER":  os.getenv("RWA_WHATSAPP_NUMBER", ""),
                "GUARD_WHATSAPP_NUMBER":os.getenv("GUARD_WHATSAPP_NUMBER", ""),
                "PYTHONPATH":           PROJECT_ROOT,  # So mcp_server can import crew.*
            },
        )
    ]

    # ── Agent Skills configuration ─────────────────────────────────────────────
    # skills_paths points to the parent directory containing skill folders.
    # The SDK discovers skills/wasteguard/SKILL.md automatically.
    # The skill provides the agent with domain knowledge about waste categories,
    # disposal rules, alert routing logic, and WhatsApp reply formatting.
    skills_paths = [SKILLS_DIR]

    return LocalAgentConfig(
        model="gemini-2.5-flash",
        system_instructions=system_instructions,
        mcp_servers=mcp_servers,
        skills_paths=skills_paths,
    )


async def run_interactive():
    """
    Run the WasteGuard agent in interactive mode.
    The user types queries in the terminal; the agent responds using its tools.
    Great for recording a demo video showing the full Antigravity + MCP integration.
    """
    print("\n" + "🟢 " * 25)
    print("♻️   WasteGuard Society AI — Antigravity Agent")
    print("    Powered by: Google Antigravity SDK + MCP Server + Agent Skills")
    print("🟢 " * 25 + "\n")
    print("📋  Available tools (via MCP server):")
    print("    • detect_waste       — Run YOLOv5 on an image")
    print("    • classify_waste     — Map detections to category/bin/urgency")
    print("    • create_ticket      — Log complaint in SQLite DB")
    print("    • get_dashboard_stats — View open/resolved counts")
    print("    • send_whatsapp_alert — Send WhatsApp via Twilio")
    print("\n🎓  Agent Skill loaded: skills/wasteguard/SKILL.md")
    print("\nType 'exit' or 'quit' to end the session.\n")

    config = build_agent_config()

    async with Agent(config) as agent:
        print("Starting interactive loop. Type 'exit' or 'quit' to end.")
        while True:
            try:
                user_input = input("User: ")
                if user_input.strip().lower() in ['exit', 'quit']:
                    break
                if not user_input.strip():
                    continue
                
                print("Agent: ", end="", flush=True)
                response = await agent.chat(user_input)
                async for token in response:
                    print(token, end="", flush=True)
                print()
            except (KeyboardInterrupt, EOFError):
                break


async def run_single_query(query: str):
    """
    Run the WasteGuard agent with a single query and print the response.
    Useful for automated tests or quick demonstrations.
    """
    print(f"\n♻️  WasteGuard AI | Query: {query}\n")

    config = build_agent_config()

    async with Agent(config) as agent:
        response = await agent.chat(query)
        # Stream the response token-by-token for a live feel
        async for token in response:
            print(token, end="", flush=True)
        print("\n")  # Final newline after streaming


def main():
    parser = argparse.ArgumentParser(
        description="WasteGuard Society AI — Google Antigravity Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive session
  python antigravity_agent.py

  # Dashboard query
  python antigravity_agent.py --query "Show me the dashboard stats"

  # Full waste analysis pipeline
  python antigravity_agent.py --query "Detect and classify waste in data/inputImage.jpg and create a ticket for reporter +919876543210"

  # Urgency question
  python antigravity_agent.py --query "What should I do if I find medical waste in the lobby?"
        """
    )
    parser.add_argument(
        "--query", "-q",
        type=str,
        default=None,
        help="Run a single query and exit (omit for interactive mode)"
    )
    args = parser.parse_args()

    if args.query:
        asyncio.run(run_single_query(args.query))
    else:
        asyncio.run(run_interactive())


if __name__ == "__main__":
    main()
