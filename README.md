# 🗑️ WasteGuard Society AI — Multi-Agent Waste Detection System

> A real-time, WhatsApp-powered AI pipeline for residential societies to detect, classify, and manage waste complaints — built with YOLOv5, CrewAI, Groq LLM, and Twilio.

---

## 📌 Why I Built This

Living in a residential society, I noticed one core problem: **waste complaints get lost**.

A resident spots garbage dumped in the wrong place, messages the group chat, and... nothing happens. No ticket. No accountability. No follow-up.

I wanted to fix that with AI — not just as a detection model, but as a **complete workflow**: a resident snaps a photo, WhatsApp does the rest.

---

## 🎯 What It Does

Send a **photo of waste** to a WhatsApp number, and within seconds:

1. **YOLOv5** detects whether waste is present and what type
2. A **Classifer Agent** maps it to a category (Dry / Wet / Hazardous / General)
3. A **Ticket Manager** creates a traceable complaint in a local database
4. **Groq LLM (llama-3.3-70b)** generates a contextual, friendly WhatsApp reply
5. **Twilio** sends the reply to the resident + an alert to the RWA/Guard

All of this happens automatically, in under 30 seconds.

---

## 🏗️ System Architecture

```
Resident (WhatsApp)
      │
      ▼
 Twilio Sandbox  ──────────────────────────────────────►  Resident Reply
      │                                                    (♻️ WasteGuard AI)
      ▼
 Flask Webhook (app.py)
      │
      ▼
┌─────────────────────────────────────────────────────────┐
│                    WasteGuard Pipeline                   │
│                                                         │
│  ┌────────────────┐   ┌──────────────────┐              │
│  │ Agent 1        │   │ Agent 2           │              │
│  │ Waste Detector │──►│ Waste Classifier  │              │
│  │ (YOLOv5)      │   │ (Lookup + LLM)   │              │
│  └────────────────┘   └──────────────────┘              │
│                              │                          │
│              ┌───────────────┘                          │
│              ▼                                          │
│  ┌──────────────────┐   ┌──────────────────────────┐   │
│  │ Agent 3          │   │ Agent 4                   │   │
│  │ Ticket Manager   │   │ Alert & Communication     │   │
│  │ (SQLite)         │   │ (Groq LLM + Twilio)       │   │
│  └──────────────────┘   └──────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
      │
      ▼
 RWA / Guard Alert (WhatsApp)
```

---

## 🧰 Tech Stack

| Layer | Technology |
|---|---|
| Object Detection | YOLOv5 (custom-trained / yolov5s.pt) |
| Agent Orchestration | CrewAI 0.63 |
| LLM | Groq — `llama-3.3-70b-versatile` |
| WhatsApp | Twilio Sandbox API |
| Backend | Flask (Python) |
| Database | SQLite (lightweight, zero-config) |
| Tunnel (local dev) | ngrok |
| Environment | Conda (Python 3.10) |

---

## 📁 Project Structure

```
End-to-end-Waste-Detection/
│
├── app.py                    # Flask app — Twilio webhook handler
│
├── crew/
│   ├── waste_crew.py         # Main pipeline orchestrator
│   ├── agents.py             # 4 CrewAI agent definitions
│   ├── tasks.py              # Task definitions for each agent
│   ├── tools/
│   │   ├── yolov5_tool.py    # YOLOv5 detection tool
│   │   ├── classifier_tool.py# Waste classification + disposal tips
│   │   ├── whatsapp_tool.py  # Twilio WhatsApp sender
│   │   └── ticket_tool.py    # SQLite ticket creator
│   └── db/
│       └── database.py       # DB schema + CRUD operations
│
├── yolov5/                   # YOLOv5 submodule (Ultralytics)
│   └── run_detect.py         # PyTorch 2.6+ compatible detection wrapper
│
├── data/                     # Runtime image storage (gitignored)
├── templates/                # Flask HTML templates (dashboard)
├── .env.example              # Environment variable template
├── requirements.txt          # Core Python dependencies
├── requirements_crew.txt     # CrewAI-specific dependencies
└── setup_guide.md            # Full local setup walkthrough
```

---

## ⚡ Quick Start

### 1. Clone and set up the environment

```bash
git clone https://github.com/entbappy/End-to-end-Waste-Detection-Using-Yolo-v5.git
cd End-to-end-Waste-Detection-Using-Yolo-v5

conda create -n waste python=3.10 -y
conda activate waste
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
pip install -r requirements_crew.txt
```

### 3. Configure environment variables

```bash
cp .env.example .env
# Fill in your API keys
```

Your `.env` file needs:

```env
GROQ_API_KEY=your_groq_api_key_here
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
RWA_WHATSAPP_NUMBER=+91XXXXXXXXXX
GUARD_WHATSAPP_NUMBER=+91XXXXXXXXXX
```

**Get your keys:**
- Groq API — [console.groq.com](https://console.groq.com) (free tier works)
- Twilio — [twilio.com/console](https://www.twilio.com/console) → WhatsApp Sandbox

### 4. Set up Twilio WhatsApp Sandbox

1. Go to **Twilio Console → Messaging → Try it out → Send a WhatsApp message**
2. Send the sandbox join code from your phone (e.g. `join bright-owl`)
3. Note your sandbox number (usually `+14155238886`)

### 5. Run the app

```bash
# Terminal 1 — Start Flask
conda activate waste
python app.py

# Terminal 2 — Start ngrok tunnel
./ngrok http 8080

# Copy the ngrok HTTPS URL into Twilio sandbox webhook:
# https://your-id.ngrok-free.app/whatsapp
```

### 6. Test it!

Send any photo to your Twilio sandbox WhatsApp number.
You'll receive a detailed waste analysis report within seconds.

---

## 💬 Sample WhatsApp Interaction

**You send:** *[photo of plastic packaging on the floor]*

**WasteGuard replies:**

```
🤖 Image received!
Our AI crew is analysing it...
⏳ Detailed report coming in a few seconds!

♻️ WasteGuard Society AI

We've received your report of *Dry Waste*. 🙏
Please use the *Yellow bin* for disposal. ♻️

Your ticket number is *#9*.
We'll take care of it on the *same day* ⏰

💡 Tip: Rinse containers before disposal. Use
the Yellow bin near the lift lobby.

Thank you for helping keep Greenview Heights clean! 🌿
```

**Guard receives simultaneously:**

```
🚨 WasteGuard Alert — Ticket #9
Waste: Plastic Bag | Urgency: Medium
⏰ Same day
```

---

## 🗄️ Ticket Database Schema

Each waste complaint is stored as a ticket:

| Field | Description |
|---|---|
| `ticket_id` | Auto-incremented unique ID |
| `waste_type` | Detected waste class (e.g. Plastic Bag) |
| `category` | Dry / Wet / Hazardous / General |
| `urgency` | Low / Medium / High / Critical |
| `location` | Reported location |
| `reported_by` | WhatsApp number of reporter |
| `disposal_tip` | Bin color + disposal instructions |
| `status` | Open / In Progress / Resolved |
| `created_at` | Timestamp |

Access the dashboard at `http://localhost:8080/dashboard` while the app is running.

---

## 🔍 Waste Classification Map

| Class ID | Waste Type | Category | Bin Color | Urgency |
|---|---|---|---|---|
| 0 | Plastic Bottle | Dry Waste | 🟡 Yellow | Medium |
| 1 | Food / Organic | Wet Waste | 🟢 Green | High |
| 2 | Paper / Cardboard | Dry Waste | 🟡 Yellow | Low |
| 3 | Glass Bottle | Dry Waste | 🟡 Yellow | Medium |
| 4 | Metal Can | Dry Waste | 🟡 Yellow | Low |
| 5 | E-Waste | Hazardous | 🔴 Red | High |
| 6 | Medical Waste | Hazardous | 🔴 Red | Critical |
| 7 | Plastic Bag | Dry Waste | 🟡 Yellow | Medium |
| 8 | Mixed / General | General | ⬜ Grey | Medium |

---

## 🚧 Known Limitations & Future Work

- **Free Groq tier**: Rate limits apply (~12k tokens/min). A paid tier removes this constraint.
- **YOLOv5 model**: Currently using the generic `yolov5s.pt`. A fine-tuned waste-specific model will improve detection accuracy significantly.
- **Single-society demo**: The system is designed for one society. Multi-tenancy support (multiple societies, separate databases) is a clear next step.
- **Database**: SQLite is great for a prototype. Production deployments should use PostgreSQL.

---

## 🛠️ Compatibility Notes

This project was built to work with some specific version constraints:

- `ultralytics==8.0.20` — Required for YOLOv5 compatibility (newer versions removed `ultralytics.yolo`)
- `crewai==0.63.0` — Stable version compatible with Python 3.10 tool interfaces
- `torch` with `weights_only=False` — Applied via `yolov5/run_detect.py` wrapper for PyTorch 2.6+ compatibility

---

## 👤 About

Built as a practical prototype for **Greenview Heights** residential society.  
The goal was to show that AI doesn't have to be a research project — it can solve everyday civic problems with tools that are free to use.

If you're building something similar or have questions, feel free to open an issue or connect on [LinkedIn](https://linkedin.com/in/sandhya-bdb).

---

## 📄 License

This project is licensed under the MIT License — see [LICENSE](LICENSE) for details.
