# 🗑️ WasteGuard Society AI — Multi-Agent Waste Detection System

> A real-time, WhatsApp-powered AI pipeline for residential societies to detect, classify, and manage waste complaints — built with YOLOv5, CrewAI, Groq LLM, Twilio, MCP Server, and Google Antigravity.

[![Python](https://img.shields.io/badge/Python-3.10-blue)](https://python.org)
[![CrewAI](https://img.shields.io/badge/CrewAI-0.63-green)](https://crewai.com)
[![YOLOv5](https://img.shields.io/badge/YOLOv5-PyTorch-red)](https://github.com/ultralytics/yolov5)
[![Kaggle](https://img.shields.io/badge/Kaggle-Agent%20for%20Good-orange)](https://www.kaggle.com/competitions/vibecoding-agents-capstone-project)

---

## 📌 Abstract

Living in a residential society, I noticed one core problem: **waste complaints get lost**. A resident spots garbage, messages the group chat, and nothing happens — no ticket, no accountability, no follow-up.

WasteGuard Society AI fixes this with a **4-agent AI pipeline**: a resident sends a WhatsApp photo, and within 30 seconds the waste is detected (YOLOv5), classified, a complaint ticket is logged in a database, the cleaning guard is alerted, and the resident receives a detailed, friendly reply — all automatically, with no app to install.

This project was built for the **AI Agents: Intensive Vibe Coding Capstone** by Google & Kaggle, submitted to the **Agents for Good** category.

---

## 🎯 What It Does

Send a **photo of waste** to a WhatsApp number, and within 30 seconds:

1. **YOLOv5 + Gemini Vision** detects whether waste is present and what type
2. A **Classifier Agent** maps it to a category (Dry / Wet / Hazardous / General)
3. A **Ticket Manager** creates a traceable complaint in the SQLite database (Viewable on the **Web Dashboard** at `/dashboard`)
4. **Groq LLM (llama-3.3-70b)** generates a contextual, friendly WhatsApp reply
5. **Twilio** sends the reply to the resident + an alert to the RWA/Guard

All of this happens automatically, in under 30 seconds.

---

## 🏗️ System Architecture

```
Resident (WhatsApp Photo)
        │
        ▼
  Twilio Sandbox ──────────────────────────────────► Resident Reply
        │                                             (♻️ WasteGuard AI)
        ▼
  Flask Webhook (app.py)
  [Security Layer: Twilio Signature ✓ | Rate Limiter ✓ | Image Validation ✓]
        │
        ▼
┌────────────────────────────────────────────────────┐
│                WasteGuard Pipeline                  │
│                                                     │
│  Agent 1: Waste Detection Specialist                │
│  Tool: YOLOv5DetectionTool                          │
│           │                                         │
│           ▼                                         │
│  Agent 2: Waste Classification Expert               │
│  Tool: WasteClassifierTool (lookup table)           │
│           │                                         │
│           ▼                                         │
│  Agent 3: Alert & Communication Manager             │
│  Tool: WhatsAppTool (Twilio)                        │
│  Rule: Critical/High→Guard+RWA | Medium→Guard       │
│           │                                         │
│           ▼                                         │
│  Agent 4: Complaint & Resolution Coordinator        │
│  Tool: TicketManagerTool (SQLite)                   │
│  LLM: Groq llama-3.3-70b (reply generation)         │
└────────────────────────────────────────────────────┘
        │
        ▼
  Resident gets full report ✅  Guard gets alert 🚨  Ticket logged 🗄️
```

### Flowcharts

**Data Ingestion Pipeline**
![Data Ingestion](flowcharts/Data%20Ingetions.png)

**Data Validation Pipeline**
![Data Validation](flowcharts/Data%20validation.png)

**Model Training Pipeline**
![Model Training](flowcharts/Model%20trainer.png)

---

## 🧰 Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Object Detection | YOLOv5 + Gemini Vision | Identify waste type from image (with Multimodal fallback) |
| Agent Orchestration | CrewAI 0.63 | Define 4 specialized agents |
| LLM | Groq — `llama-3.3-70b-versatile` | Natural language reply generation |
| WhatsApp | Twilio Sandbox API | Resident & guard messaging |
| Backend | Flask + threading | Async webhook handling |
| Database | SQLite | Zero-config complaint persistence |
| MCP Server | FastMCP (`mcp` SDK) | Expose tools to AI assistants |
| AI Agent SDK | Google Antigravity | MCP-connected Antigravity agent |
| Agent Skills | agentskills.io spec | Domain expertise as a reusable skill |
| Security | HMAC-SHA1 + Rate Limiter | Webhook auth & abuse prevention |
| Tunnel | ngrok | Local dev → public HTTPS |
| Environment | Conda (Python 3.10) | Dependency isolation |

---

## 🔑 Key Concepts Demonstrated (Kaggle Rubric)

| Concept | Implementation |
|---|---|
| ✅ Agent / Multi-agent system | 4 CrewAI agents with distinct roles and tools |
| ✅ MCP Server | FastMCP server with 5 WasteGuard tools (`mcp_server/`) |
| ✅ Security features | Twilio signature validation, per-number rate limiting, image validation |
| ✅ Deployability | Docker + ngrok + full `setup_guide.md` |
| ✅ Antigravity | Google Antigravity agent connected to MCP server (`antigravity_agent.py`) |
| ✅ Agent Skills | `skills/wasteguard/SKILL.md` loaded via `skills_paths` |

---

## 📁 Project Structure

```
End-to-end-Waste-Detection/
│
├── app.py                      # Flask app — Twilio webhook + security layer
├── antigravity_agent.py        # Google Antigravity agent (MCP + Skills)
│
├── crew/
│   ├── waste_crew.py           # Main pipeline orchestrator (all 4 agents)
│   ├── agents.py               # CrewAI agent definitions
│   ├── tasks.py                # Task definitions for each agent
│   ├── security/
│   │   ├── auth.py             # Twilio signature validation + image validation
│   │   └── rate_limiter.py     # Per-number sliding-window rate limiter
│   ├── tools/
│   │   ├── yolov5_tool.py      # YOLOv5 detection tool
│   │   ├── classifier_tool.py  # Waste classification + disposal tips
│   │   ├── whatsapp_tool.py    # Twilio WhatsApp sender
│   │   └── ticket_tool.py      # SQLite ticket creator
│   └── db/
│       └── database.py         # DB schema + CRUD operations
│
├── mcp_server/
│   ├── waste_mcp_server.py     # MCP server (5 tools for AI assistants)
│   └── README_MCP.md           # MCP setup + Claude Desktop config
│
├── skills/
│   └── wasteguard/
│       └── SKILL.md            # WasteGuard agent skill (agentskills.io spec)
│
├── yolov5/                     # YOLOv5 submodule (Ultralytics)
│   └── run_detect.py           # PyTorch 2.6+ compatible detection wrapper
│
├── flowcharts/                 # Pipeline architecture diagrams
├── data/                       # Runtime image storage (gitignored)
├── templates/                  # Flask HTML templates
├── .env.example                # Environment variable template
├── requirements.txt            # Core Python dependencies
├── requirements_crew.txt       # CrewAI-specific dependencies
├── requirements_mcp.txt        # MCP server dependency
├── requirements_antigravity.txt# Google Antigravity SDK dependency
├── Dockerfile                  # Docker deployment
└── setup_guide.md              # Full local setup walkthrough
```

---

## ⚡ Quick Start

### 1. Clone and set up the environment

```bash
git clone https://github.com/sandhya-bdb/waste-detection-yolov5-crewai.git
cd waste-detection-yolov5-crewai

conda create -n waste python=3.10 -y
conda activate waste
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
pip install -r requirements_crew.txt
pip install -r requirements_mcp.txt          # For MCP server
pip install -r requirements_antigravity.txt  # For Antigravity agent
```

### 3. Configure environment variables

```bash
cp .env.example .env
# Fill in your API keys
```

Your `.env` file needs:

```env
# Gemini (for Antigravity agent)
GEMINI_API_KEY=your_gemini_api_key_here

# Groq (for CrewAI WhatsApp reply generation)
GROQ_API_KEY=your_groq_api_key_here

# Twilio (for WhatsApp)
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886

# Society contacts
RWA_WHATSAPP_NUMBER=+91XXXXXXXXXX
GUARD_WHATSAPP_NUMBER=+91XXXXXXXXXX
```

**Get your keys:**
- Gemini API — [aistudio.google.com/app/api-keys](https://aistudio.google.com/app/api-keys) (free)
- Groq API — [console.groq.com](https://console.groq.com) (free tier works)
- Twilio — [twilio.com/console](https://www.twilio.com/console) → WhatsApp Sandbox

### 4. Set up Twilio WhatsApp Sandbox

1. Go to **Twilio Console → Messaging → Try it out → Send a WhatsApp message**
2. Send the sandbox join code from your phone (e.g. `join bright-owl`)
3. Note your sandbox number (usually `+14155238886`)

### 5. Run the Flask app

```bash
# Terminal 1 — Start Flask
conda activate waste
python app.py

# Terminal 2 — Start ngrok tunnel
./ngrok http 8080

# Copy the ngrok HTTPS URL into Twilio sandbox webhook:
# https://your-id.ngrok-free.app/whatsapp
```

### 6. Run the Antigravity Agent (interactive)

```bash
python antigravity_agent.py
```

Then try:
- `"Show me the current dashboard stats"`
- `"Detect and classify waste in data/inputImage.jpg and create a ticket for +919876543210"`
- `"What should I do if I find medical waste near the lift?"`

### 7. Run the MCP Server (standalone)

```bash
python mcp_server/waste_mcp_server.py
```

See [`mcp_server/README_MCP.md`](mcp_server/README_MCP.md) for Claude Desktop integration.

---

## 🔒 Security Features

The `/whatsapp` webhook is protected by three independent security layers:

| Security Feature | Implementation | File |
|---|---|---|
| **Twilio Signature Validation** | HMAC-SHA1 verification — rejects requests not signed by Twilio | `crew/security/auth.py` |
| **Per-number Rate Limiting** | Max 5 requests per 10-minute window per WhatsApp number | `crew/security/rate_limiter.py` |
| **Image Content Validation** | Rejects non-image files and files > 10 MB before writing to disk | `crew/security/auth.py` |

In demo mode (no `TWILIO_AUTH_TOKEN` set), signature validation is skipped automatically.

---

## 🔌 MCP Server Tools

The MCP server at `mcp_server/waste_mcp_server.py` exposes 5 tools to any MCP-compatible AI client:

| Tool | Description |
|---|---|
| `detect_waste` | Run YOLOv5 on an image file → returns detections JSON |
| `classify_waste` | Map detections → category, bin colour, urgency, ETA |
| `create_ticket` | Insert a complaint into the SQLite database |
| `get_dashboard_stats` | Return open/resolved ticket counts by category |
| `send_whatsapp_alert` | Send a WhatsApp message via Twilio |

---

## 💬 Sample WhatsApp Interaction

**You send:** *[photo of plastic packaging on the floor]*

**Immediate reply (< 2 seconds):**
```
📸 Image received! 🤖
Our AI crew is analysing it...
⏳ Detailed report coming in a few seconds!
```

**Full AI report (15–30 seconds):**
```
♻️ WasteGuard Society AI

✅ Waste detected & processed!

🔍 Detected: Plastic Bag
🏷️ Category: Dry Waste
🗑️ Bin: Yellow bin — Ground Floor / Lift Lobby
⚠️ Urgency: Medium

🎫 Ticket #12 created
👷 Assigned to: Cleaning Staff
⏰ Same day

💡 Tip: Rinse containers before disposal.
Use the Yellow bin near the lift lobby.

🙏 Thank you for keeping Greenview Heights clean!
Your complaint will be resolved soon. 🌿
```

**Guard receives simultaneously:**
```
🚨 WasteGuard Alert — Ticket #12
Waste: Plastic Bag | Urgency: Medium
⏰ Same day
```

---

## 🗄️ Ticket Database Schema

Each waste complaint is stored as a traceable ticket:

| Field | Description |
|---|---|
| `ticket_id` | Auto-incremented unique ID |
| `waste_type` | Detected waste class (e.g. Plastic Bag) |
| `category` | Dry / Wet / Hazardous / General |
| `urgency` | Low / Medium / High / Critical |
| `location` | Reported location |
| `reported_by` | WhatsApp number of reporter |
| `disposal_tip` | Bin color + disposal instructions |
| `assigned_to` | Cleaning Staff (default) |
| `status` | Open / In Progress / Resolved |
| `created_at` | Timestamp |

Access the dashboard at `http://localhost:8080/dashboard` while the app is running.

---

## 🔍 Waste Classification Map

| Class | Waste Type | Category | Bin | Urgency | ETA |
|---|---|---|---|---|---|
| 0 | Plastic Bottle | Dry Waste | 🟡 Yellow | Medium | Same day |
| 1 | Food / Organic | Wet Waste | 🟢 Green | High | 2–4 hours |
| 2 | Paper / Cardboard | Dry Waste | 🟡 Yellow | Low | Next round |
| 3 | Glass Bottle | Dry Waste | 🟡 Yellow | Medium | Same day |
| 4 | Metal Can | Dry Waste | 🟡 Yellow | Low | Next round |
| 5 | E-Waste | Hazardous | 🔴 Red | High | 2–4 hours |
| 6 | Medical Waste | Hazardous | 🔴 Red | Critical | Within 1 hour |
| 7 | Plastic Bag | Dry Waste | 🟡 Yellow | Medium | Same day |
| 8 | Mixed / General | General | ⬜ Grey | Medium | Same day |

---

## 🚧 Known Limitations & Future Work

- **YOLOv5 model**: Currently using generic `yolov5s.pt`. Fine-tuning on TACO/TrashNet dataset would improve detection accuracy significantly.
- **Free Groq tier**: Rate limits apply (~12k tokens/min). A paid tier removes this constraint.
- **Single-society demo**: The system is designed for one society. Multi-tenancy is a clear next step.
- **SQLite**: Great for prototype. Production should use PostgreSQL.
- **Image retention**: Images saved locally; production should use GCS/S3 with auto-expiry.

---

## 🛠️ Compatibility Notes

- `ultralytics==8.0.20` — Required for YOLOv5 compatibility (newer versions removed `ultralytics.yolo`)
- `crewai==0.63.0` — Stable version compatible with Python 3.10 tool interfaces
- `torch` with `weights_only=False` — Applied via `yolov5/run_detect.py` wrapper for PyTorch 2.6+

---

## 👤 About

Built by **Sandhya Bantidutta Borah** as a capstone project for the **AI Agents: Intensive Vibe Coding** course by Google & Kaggle.

The goal: show that AI can solve everyday civic problems with tools that residents already have (WhatsApp), creating real accountability without any app install.

Connect on [LinkedIn](https://linkedin.com/in/sandhya-bdb) | Questions? Open an issue.

---

## 📄 License

This project is licensed under the MIT License — see [LICENSE](LICENSE) for details.
