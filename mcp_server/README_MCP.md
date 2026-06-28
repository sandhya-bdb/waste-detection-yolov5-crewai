# WasteGuard MCP Server

## What is this?

This is a **Model Context Protocol (MCP) server** that exposes WasteGuard's AI pipeline as callable tools to any MCP-compatible AI assistant (Claude Desktop, Cursor, etc.).

MCP is an open standard that lets AI models call external tools in a structured, safe way — similar to how a browser can call external APIs.

## Tools Available

| Tool | Description |
|---|---|
| `detect_waste` | Run YOLOv5 on an image → returns detected waste items |
| `classify_waste` | Map detections → bin colour, urgency, disposal tip |
| `create_ticket` | Log a complaint in the SQLite database |
| `get_dashboard_stats` | Get open/resolved ticket counts by category |
| `send_whatsapp_alert` | Send a WhatsApp message via Twilio |

## Setup

```bash
# Install MCP dependency (in addition to existing requirements)
pip install -r requirements_mcp.txt

# Run the server (stdio transport — used by Claude Desktop, Cursor, etc.)
python mcp_server/waste_mcp_server.py
```

## Connect to Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "wasteguard": {
      "command": "python",
      "args": ["/absolute/path/to/End-to-end-Waste-Detection/mcp_server/waste_mcp_server.py"],
      "env": {
        "GROQ_API_KEY": "your_groq_key",
        "TWILIO_ACCOUNT_SID": "your_sid",
        "TWILIO_AUTH_TOKEN": "your_token",
        "TWILIO_WHATSAPP_FROM": "whatsapp:+14155238886"
      }
    }
  }
}
```

After restarting Claude Desktop, the WasteGuard tools will appear in the tool panel.

## Example Usage (via Claude Desktop)

> "Detect waste in this image at `data/inputImage.jpg`, classify it, and create a ticket"

Claude will automatically:
1. Call `detect_waste("data/inputImage.jpg")` 
2. Call `classify_waste(result)` 
3. Call `create_ticket(...)` with the classification output

## Demo Without an AI Client

You can test the tools directly by importing them:

```python
import sys
sys.path.insert(0, ".")
from mcp_server.waste_mcp_server import detect_waste, classify_waste, create_ticket

# Step 1: Detect
detection = detect_waste("data/inputImage.jpg")
print(detection)

# Step 2: Classify
classification = classify_waste(detection)
print(classification)

# Step 3: Ticket
ticket = create_ticket(
    waste_type="Plastic Bag",
    category="Dry Waste",
    urgency="Medium",
    reported_by="+919876543210"
)
print(ticket)
```
