"""
WasteGuard Society AI — MCP Server
====================================
This module exposes WasteGuard's core capabilities as an MCP (Model Context Protocol) server.

What is MCP?
  MCP (Model Context Protocol) is an open standard that allows AI assistants
  (Claude, Cursor, Gemini, etc.) to call external tools via a standardized
  interface. By wrapping WasteGuard's pipeline as an MCP server, any MCP-compatible
  AI client can:
    - Detect waste in images
    - Classify waste type and urgency
    - Create complaint tickets in the database
    - Query the RWA dashboard statistics
    - Send WhatsApp alerts to the guard or RWA

How it works:
  This server runs as a standalone process using stdio transport.
  An MCP client (e.g., Claude Desktop, cursor) connects to this process and
  can call the tools below by name.

Tools exposed:
  1. detect_waste       — Run YOLOv5 on an image file path
  2. classify_waste     — Map detection results to waste category + bin info
  3. create_ticket      — Insert a complaint into the SQLite database
  4. get_dashboard_stats — Return open/resolved ticket counts
  5. send_whatsapp_alert — Send a WhatsApp message via Twilio

Run this server:
  python mcp_server/waste_mcp_server.py

Configure in Claude Desktop (claude_desktop_config.json):
  {
    "mcpServers": {
      "wasteguard": {
        "command": "python",
        "args": ["/absolute/path/to/mcp_server/waste_mcp_server.py"],
        "env": {
          "GROQ_API_KEY": "your_key",
          "TWILIO_ACCOUNT_SID": "your_sid",
          "TWILIO_AUTH_TOKEN": "your_token",
          "TWILIO_WHATSAPP_FROM": "whatsapp:+14155238886"
        }
      }
    }
  }
"""

import os
import sys
import json
import glob
import asyncio
import logging

# ── Ensure project root is on the Python path ────────────────────────────────
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv
load_dotenv()  # Load .env file so API keys are available

from mcp.server.fastmcp import FastMCP
from mcp import types

# ── Waste classification lookup table (mirrors waste_crew.py) ─────────────────
WASTE_CLASS_MAP = {
    0: {"name": "Plastic Bottle",    "category": "Dry Waste",       "bin": "Yellow", "urgency": "Medium"},
    1: {"name": "Food / Organic",    "category": "Wet Waste",       "bin": "Green",  "urgency": "High"},
    2: {"name": "Paper / Cardboard", "category": "Dry Waste",       "bin": "Yellow", "urgency": "Low"},
    3: {"name": "Glass Bottle",      "category": "Dry Waste",       "bin": "Yellow", "urgency": "Medium"},
    4: {"name": "Metal Can",         "category": "Dry Waste",       "bin": "Yellow", "urgency": "Low"},
    5: {"name": "E-Waste",           "category": "Hazardous Waste", "bin": "Red",    "urgency": "High"},
    6: {"name": "Medical Waste",     "category": "Hazardous Waste", "bin": "Red",    "urgency": "Critical"},
    7: {"name": "Plastic Bag",       "category": "Dry Waste",       "bin": "Yellow", "urgency": "Medium"},
    8: {"name": "Mixed / General",   "category": "General Waste",   "bin": "Grey",   "urgency": "Medium"},
}

DISPOSAL_TIPS = {
    "Dry Waste":       "♻️ Rinse containers before disposal. Use the Yellow bin near the lift lobby.",
    "Wet Waste":       "🌿 Dispose within 24 hrs to prevent odour. Use the Green bin near the lift lobby.",
    "Hazardous Waste": "⚠️ Do NOT mix with regular waste. Contact RWA for special hazardous waste pickup.",
    "General Waste":   "🗑️ Segregate if possible. Use the Grey bin near the society main gate.",
}

URGENCY_ETA = {
    "Critical": "Immediate — within 1 hour",
    "High":     "Within 2–4 hours",
    "Medium":   "Same day",
    "Low":      "Next scheduled cleaning round",
}

# ── Initialise the MCP server ─────────────────────────────────────────────────
mcp = FastMCP(
    name="wasteguard-society-ai"
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MCP TOOL 1 — Waste Detection
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@mcp.tool()
def detect_waste(image_path: str) -> str:
    """
    Run YOLOv5 waste detection on an image file.

    Args:
        image_path: Absolute or relative path to a JPG/PNG image file.

    Returns:
        JSON string with fields:
          - waste_detected (bool): True if any waste was found
          - num_detections (int): How many waste items were detected
          - detections (list): Each item has class_id and confidence
          - message (str): Human-readable summary
          - simulated (bool): True if YOLOv5 was unavailable (demo fallback)
    """
    # Clean up any previous YOLOv5 run output
    if os.path.exists("yolov5/runs"):
        os.system("rm -rf yolov5/runs")

    # Use sys.executable so the correct Python environment is always used
    python_bin = sys.executable
    weights    = "my_model.pt" if os.path.exists("yolov5/my_model.pt") else "yolov5s.pt"

    # Run YOLOv5 detection with label saving enabled
    cmd = (
        f"cd yolov5/ && {python_bin} run_detect.py "
        f"--weights {weights} "
        f"--img 416 --conf 0.5 "
        f"--source ../{image_path} "
        f"--save-txt --save-conf 2>&1"
    )
    os.system(cmd)

    # Check for detection output directories
    output_dirs = sorted(glob.glob("yolov5/runs/detect/exp*"))
    if not output_dirs:
        # YOLOv5 unavailable — return a simulated result so the pipeline continues
        return json.dumps({
            "waste_detected": True,
            "num_detections": 1,
            "detections": [{"class_id": 7, "confidence": 0.82}],
            "message": "Simulated: Plastic Bag detected (demo mode — YOLOv5 model not loaded).",
            "simulated": True,
        })

    # Parse YOLOv5 label output files
    latest_dir  = output_dirs[-1]
    detections  = []
    label_files = glob.glob(f"{latest_dir}/labels/*.txt")

    if label_files:
        with open(label_files[0]) as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 5:
                    class_id   = int(parts[0])
                    confidence = float(parts[5]) if len(parts) > 5 else 0.75
                    detections.append({
                        "class_id":   class_id,
                        "confidence": round(confidence, 2),
                    })

    return json.dumps({
        "waste_detected":  len(detections) > 0,
        "num_detections":  len(detections),
        "detections":      detections,
        "message": f"Found {len(detections)} waste item(s)." if detections else "No waste detected.",
        "simulated": False,
    })


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MCP TOOL 2 — Waste Classification
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@mcp.tool()
def classify_waste(detection_json: str) -> str:
    """
    Classify detected waste items into categories with disposal guidance.

    Args:
        detection_json: The JSON string returned by detect_waste().

    Returns:
        JSON string with fields:
          - waste_type (str): Primary detected waste name
          - category (str): Dry / Wet / Hazardous / General Waste
          - bin_color (str): Colour of the correct disposal bin
          - bin_location (str): Where to find the bin
          - urgency (str): Low / Medium / High / Critical
          - estimated_eta (str): How soon cleanup should happen
          - disposal_tip (str): Actionable advice for the resident
    """
    try:
        data       = json.loads(detection_json)
        detections = data.get("detections", [])

        # If no waste detected, default to General Waste classification
        if not data.get("waste_detected") or not detections:
            info = WASTE_CLASS_MAP[8]
            return json.dumps({
                "waste_type":    info["name"],
                "category":      info["category"],
                "bin_color":     info["bin"],
                "bin_location":  f"{info['bin']} bin — Ground Floor / Lift Lobby",
                "urgency":       info["urgency"],
                "estimated_eta": URGENCY_ETA[info["urgency"]],
                "disposal_tip":  DISPOSAL_TIPS[info["category"]],
                "detected":      False,
            })

        # Determine highest urgency across all detected items
        urgency_order = ["Low", "Medium", "High", "Critical"]
        highest       = "Low"

        for det in detections:
            info = WASTE_CLASS_MAP.get(det.get("class_id", 8), WASTE_CLASS_MAP[8])
            if urgency_order.index(info["urgency"]) > urgency_order.index(highest):
                highest = info["urgency"]

        # Use the first detected item as the primary waste type
        primary_info = WASTE_CLASS_MAP.get(
            detections[0].get("class_id", 8), WASTE_CLASS_MAP[8]
        )

        return json.dumps({
            "waste_type":    primary_info["name"],
            "category":      primary_info["category"],
            "bin_color":     primary_info["bin"],
            "bin_location":  f"{primary_info['bin']} bin — Ground Floor / Lift Lobby",
            "urgency":       highest,
            "estimated_eta": URGENCY_ETA[highest],
            "disposal_tip":  DISPOSAL_TIPS[primary_info["category"]],
            "detected":      True,
            "num_items":     len(detections),
        })

    except Exception as e:
        return json.dumps({"error": str(e), "message": "Classification failed."})


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MCP TOOL 3 — Create Complaint Ticket
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@mcp.tool()
def create_ticket(
    waste_type:   str,
    category:     str,
    urgency:      str,
    location:     str = "Society Common Area",
    reported_by:  str = "unknown",
    disposal_tip: str = "",
) -> str:
    """
    Log a waste complaint as a ticket in the SQLite database.

    Args:
        waste_type:   Name of the waste (e.g. 'Plastic Bottle')
        category:     Waste category: Dry Waste / Wet Waste / Hazardous Waste / General Waste
        urgency:      Urgency level: Low / Medium / High / Critical
        location:     Where the waste was found
        reported_by:  WhatsApp number of the reporting resident
        disposal_tip: Disposal guidance to store with the ticket

    Returns:
        JSON string with ticket_id, assigned_to, status, and confirmation message.
    """
    try:
        # Import database module from project — handles all DB operations
        from crew.db.database import init_db, create_ticket as db_create_ticket

        init_db()  # Ensure the database and tables exist

        ticket_id = db_create_ticket(
            waste_type=waste_type,
            category=category,
            urgency=urgency,
            location=location,
            reported_by=reported_by,
            disposal_tip=disposal_tip,
        )

        return json.dumps({
            "ticket_id":   ticket_id,
            "assigned_to": "Cleaning Staff",
            "status":      "Open",
            "message":     f"✅ Ticket #{ticket_id} created and assigned to Cleaning Staff.",
        })

    except Exception as e:
        return json.dumps({"error": str(e), "message": "Ticket creation failed."})


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MCP TOOL 4 — Dashboard Statistics
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@mcp.tool()
def get_dashboard_stats(time_range: str = "all") -> str:
    """
    Return real-time waste complaint statistics from the society database.

    Args:
        time_range: The time period to filter stats for. Valid options are "24h", "7d", or "all". Default is "all".

    Returns:
        JSON string with:
          - total (int): Total tickets ever created
          - open (int): Currently unresolved tickets
          - resolved (int): Resolved tickets
          - by_category (list): Ticket counts grouped by waste category
    """
    try:
        from crew.db.database import init_db, get_stats

        init_db()
        stats = get_stats(time_range=time_range)

        return json.dumps(stats)

    except Exception as e:
        return json.dumps({"error": str(e), "message": "Could not fetch stats."})


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MCP TOOL 5 — Send WhatsApp Alert
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@mcp.tool()
def send_whatsapp_alert(to_number: str, message: str) -> str:
    """
    Send a WhatsApp message via Twilio to a guard, RWA member, or resident.

    Args:
        to_number: Recipient's phone number in international format (e.g. '+919876543210')
        message:   The message body to send (supports WhatsApp formatting: *bold*, _italic_)

    Returns:
        JSON string with status ('sent' / 'demo_logged' / 'error') and details.

    Note:
        In demo mode (no TWILIO_ACCOUNT_SID set), the message is printed to
        console instead of being sent over WhatsApp.
    """
    account_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
    auth_token  = os.getenv("TWILIO_AUTH_TOKEN", "")
    from_number = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")

    if not account_sid or not auth_token:
        # Demo mode — log to console, don't attempt real API call
        print(f"\n📱 [DEMO] WhatsApp to {to_number}:\n{message}\n", file=sys.stderr)
        return json.dumps({
            "status":  "demo_logged",
            "to":      to_number,
            "message": "Demo mode: Twilio not configured. Message printed to console.",
        })

    try:
        from twilio.rest import Client

        client = Client(account_sid, auth_token)
        to     = f"whatsapp:{to_number}" if not to_number.startswith("whatsapp:") else to_number

        msg = client.messages.create(
            from_=from_number,
            to=to,
            body=message,
        )

        return json.dumps({
            "status": "sent",
            "to":     to_number,
            "sid":    msg.sid,
            "message": f"✅ WhatsApp sent to {to_number}",
        })

    except Exception as e:
        return json.dumps({
            "status":  "error",
            "to":      to_number,
            "error":   str(e),
            "message": f"❌ Failed to send WhatsApp to {to_number}",
        })


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Entry point — run the MCP server via stdio transport
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    print("🚀 WasteGuard MCP Server starting (stdio transport)...", file=sys.stderr)
    print("   Tools available: detect_waste, classify_waste, create_ticket,", file=sys.stderr)
    print("                    get_dashboard_stats, send_whatsapp_alert", file=sys.stderr)
    mcp.run(transport="stdio")
