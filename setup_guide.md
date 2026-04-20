# 🚀 WasteGuard Society AI — Complete Setup Guide
### WhatsApp + CrewAI + YOLOv5 Prototype

---

## 📋 What You'll Set Up

| Service | Purpose | Cost |
|---|---|---|
| **Groq** | Free LLM for CrewAI agents | ✅ Free |
| **Twilio** | WhatsApp Sandbox | ✅ Free |
| **ngrok** | Expose local server to internet | ✅ Free |

---

## STEP 1 — Install Dependencies

```bash
# Activate your environment first
conda activate waste

# Install existing requirements
pip install -r requirements.txt

# Install CrewAI + Twilio layer
pip install -r requirements_crew.txt
```

---

## STEP 2 — Get Your FREE Groq API Key

1. Go to 👉 https://console.groq.com
2. Click **Sign Up** (free — no credit card)
3. Go to **API Keys** → **Create API Key**
4. Copy the key (starts with `gsk_...`)

---

## STEP 3 — Set Up FREE Twilio WhatsApp Sandbox

### 3a. Create Twilio Account
1. Go to 👉 https://www.twilio.com/try-twilio
2. Sign up with your email (free trial — no credit card needed initially)
3. Verify your phone number

### 3b. Activate WhatsApp Sandbox
1. In Twilio Console → left sidebar → **Messaging** → **Try it out** → **Send a WhatsApp message**
2. You'll see a sandbox number like: `+1 415 523 8886`
3. You'll see a join code like: `join silver-elephant`
4. **From your personal WhatsApp**: send that join code to `+1 415 523 8886`
5. You'll receive: *"You have joined the sandbox..."* ✅

### 3c. Get Your Credentials
1. Twilio Console → **Account Info** (top right or dashboard)
2. Copy:
   - **Account SID** → starts with `AC...`
   - **Auth Token** → click the eye icon to reveal

---

## STEP 4 — Create Your .env File

```bash
cp .env.example .env
```

Edit `.env` and fill in your values:

```env
GROQ_API_KEY=gsk_your_actual_groq_key_here

TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886

RWA_WHATSAPP_NUMBER=+91your_rwa_number
GUARD_WHATSAPP_NUMBER=+91your_guard_number
```

> ⚠️ **Never commit .env to GitHub!** It's already in `.gitignore`

---

## STEP 5 — Install & Start ngrok

ngrok creates a public HTTPS URL that Twilio can reach.

```bash
# Install ngrok (one-time)
brew install ngrok                    # macOS

# Authenticate (free account at ngrok.com)
ngrok config add-authtoken YOUR_NGROK_TOKEN

# Start tunnel (run this in a separate terminal)
ngrok http 8080
```

You'll see output like:
```
Forwarding  https://abc123.ngrok-free.app -> http://localhost:8080
```

**Copy the https URL** — you'll need it for Twilio.

---

## STEP 6 — Configure Twilio Webhook

1. Twilio Console → **Messaging** → **Try it out** → **WhatsApp** → **Sandbox settings**
2. In **"WHEN A MESSAGE COMES IN"** field, paste:
   ```
   https://abc123.ngrok-free.app/whatsapp
   ```
   (use your actual ngrok URL)
3. Method: **HTTP POST**
4. Click **Save**

---

## STEP 7 — Run the App

```bash
# Terminal 1: Run ngrok (if not already running)
ngrok http 8080

# Terminal 2: Run the Flask app
python app.py
```

You should see:
```
✅ Database initialized.
 * Running on http://0.0.0.0:8080
```

---

## STEP 8 — Test It! 🎉

1. Open WhatsApp on your phone
2. Send `hi` to **+1 415 523 8886** (Twilio sandbox number)
3. You should receive the welcome message
4. Now send any **photo of waste** (plastic bottle, food waste, etc.)
5. Watch the terminal — you'll see all 4 CrewAI agents running!
6. In ~10-15 seconds, you'll receive the full report on WhatsApp ✅

---

## 🎬 For LinkedIn Demo Recording

**Terminal setup** (for a clean demo video):
```bash
# Clear terminal for clean recording
clear

# Run with verbose output so agents are visible
python app.py
```

**What to show in your LinkedIn video:**
1. Show the WhatsApp chat on your phone
2. Send a waste photo
3. Show terminal with CrewAI agents executing
4. Show the WhatsApp reply arriving with ticket number
5. Open `http://localhost:8080/dashboard` to show the ticket logged

---

## 🔧 Testing Without WhatsApp (Demo Mode)

You can test the CrewAI crew directly without any WhatsApp setup:

```python
# Run this from project root
python -c "
from dotenv import load_dotenv
load_dotenv()
from crew.waste_crew import WasteCrew
crew = WasteCrew()
result = crew.run(
    image_path='data/inputImage.jpg',
    from_number='+919876543210'
)
print(result['reply_message'])
"
```

This runs all 4 agents and prints the WhatsApp reply to terminal.

---

## 📁 New Project Structure

```
End-to-end-Waste-Detection/
├── crew/                          🆕 CrewAI Layer
│   ├── agents.py                  🆕 4 AI agents (Groq LLM)
│   ├── tasks.py                   🆕 4 sequential tasks
│   ├── waste_crew.py              🆕 Crew orchestrator
│   ├── tools/
│   │   ├── yolov5_tool.py         🆕 YOLOv5 detection tool
│   │   ├── classifier_tool.py     🆕 Waste classifier tool
│   │   ├── whatsapp_tool.py       🆕 WhatsApp alert tool
│   │   └── ticket_tool.py         🆕 SQLite ticket tool
│   └── db/
│       ├── database.py            🆕 SQLite CRUD operations
│       └── waste_tickets.db       🆕 Auto-created on first run
├── app.py                         ✏️ Added /whatsapp + /dashboard routes
├── .env.example                   🆕 Credential template
├── requirements_crew.txt          🆕 CrewAI dependencies
├── setup_guide.md                 🆕 This file
├── wasteDetection/                ✅ Existing ML package
└── yolov5/                        ✅ Existing YOLOv5
```

---

## ❓ Troubleshooting

| Problem | Solution |
|---|---|
| `ModuleNotFoundError: crewai` | Run `pip install -r requirements_crew.txt` |
| `GROQ_API_KEY not set` | Check your `.env` file has the key |
| Twilio not sending messages | Check sandbox join code was sent from YOUR WhatsApp |
| ngrok URL expired | Free ngrok resets each session — update Twilio webhook URL |
| YOLOv5 model not found | Ensure `yolov5/my_model.pt` exists (run training first) |
| Crew takes too long | Normal for first run — Groq is fast, YOLOv5 takes ~5-10s |

---

## 🏆 LinkedIn Post Tips

**Post title suggestion:**
> "Built a Multi-Agent WhatsApp AI for Society Waste Management using CrewAI + YOLOv5 + Groq 🚀"

**Key points to highlight:**
- 🤖 4 specialized AI agents collaborating
- 📱 WhatsApp as the resident interface (400 families!)
- ♻️ Real-time waste detection + classification
- 🎫 Automated complaint ticketing
- 🔔 Instant alerts to security and RWA
- 💸 Zero cost (Groq free tier + Twilio sandbox)

**Hashtags:**
`#CrewAI #MultiAgentAI #YOLOv5 #ComputerVision #GenAI #AgenticAI #Python #MachineLearning #SmartCity #WasteManagement`
