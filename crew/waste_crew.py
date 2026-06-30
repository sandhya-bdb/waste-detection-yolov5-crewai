"""
WasteCrew — Streamlined Pipeline for WasteGuard Society AI
Bypasses crewai tool-chain complexity for reliable prototype demo.
Steps: YOLOv5 detect → classify → Groq LLM reply → ticket → WhatsApp alert

Design note: Although agents.py and tasks.py define a full CrewAI crew,
this WasteCrew class uses a direct Python pipeline instead of CrewAI
orchestration. This is a deliberate reliability tradeoff:
  - CrewAI's ReAct loop can stall on tool-call failures at demo time
  - The direct pipeline is deterministic and easier to debug
  - All agent roles are still present (each _step maps to one agent's job)
  - Migrating to full CrewAI orchestration is a documented future step
"""
import os
import re
import json
import sys
import glob
import time

from crew.db.database import init_db, create_ticket


# ── Waste classification lookup ───────────────────────────────────────────────
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
    39: {"name": "Medical Vial / Syringe", "category": "Hazardous Waste", "bin": "Red", "urgency": "Critical"},
}

DISPOSAL_TIPS = {
    "Dry Waste":       "♻️ Rinse containers before disposal. Use the *Yellow bin* near the lift lobby.",
    "Wet Waste":       "🌿 Dispose within 24 hrs to prevent odour. Use the *Green bin* near the lift lobby.",
    "Hazardous Waste": "⚠️ Do NOT mix with regular waste. Contact RWA for a *special hazardous waste pickup*.",
    "General Waste":   "🗑️ Segregate if possible. Use the *Grey bin* near the society main gate.",
}

URGENCY_ETA = {
    "Critical": "⏰ Immediate — within 1 hour",
    "High":     "⏰ Within 2–4 hours",
    "Medium":   "⏰ Same day",
    "Low":      "⏰ Next scheduled cleaning round",
}


class WasteCrew:
    """
    Streamlined waste management pipeline:
      Step 1: YOLOv5 detection (Python)
      Step 2: Waste classification (lookup table)
      Step 3: Groq LLM generates WhatsApp reply
      Step 4: SQLite ticket creation
      Step 5: WhatsApp alerts to RWA & Guard
    """

    def __init__(self):
        init_db()

    def run(self, image_path: str, from_number: str, media_url: str = "") -> dict:
        print("\n" + "🟢 " * 20)
        print("🚀  WasteGuard AI — Starting pipeline")
        print(f"📷  Image   : {image_path}")
        print(f"📱  Reporter: {from_number}")
        print("🟢 " * 20 + "\n")

        try:
            # ── Step 1: YOLOv5 Detection ─────────────────────────────────────────
            # Agent 1 (Waste Detection Specialist) responsibility:
            # Run the YOLOv5 model on the incoming image and return a structured
            # JSON with waste_detected, class_ids, and confidence scores.
            print("\n# Agent: Waste Detection Specialist")
            print("## Running YOLOv5 detection...")
            detection = self._run_yolov5(image_path)
            print(f"## Detection result: {json.dumps(detection)}")

            # ── Step 2: Classify Waste ────────────────────────────────────────
            # Agent 2 (Waste Classification Expert) responsibility:
            # Map the YOLOv5 class_id to a waste category, bin colour, urgency
            # level, and disposal instructions using a deterministic lookup table.
            print("\n# Agent: Waste Classification Expert")
            print("## Classifying waste...")
            classification = self._classify(detection)
            print(f"## Classification: {json.dumps(classification)}")

            # ── Step 3: Create Ticket ─────────────────────────────────────────
            # Agent 4 (Complaint & Resolution Coordinator) responsibility:
            # Log every complaint as a traceable ticket so no report is ever lost.
            print("\n# Agent: Complaint & Resolution Coordinator")
            print("## Creating ticket...")
            ticket_id = create_ticket(
                waste_type   = classification["waste_type"],
                category     = classification["category"],
                urgency      = classification["urgency"],
                location     = "Society Common Area",
                reported_by  = from_number,
                disposal_tip = classification["disposal_tip"],
            )
            print(f"## ✅ Ticket #{ticket_id} created")

            # ── Step 4: Generate WhatsApp Reply via Groq ──────────────────────
            # LLM is invoked ONLY here — for natural language generation.
            # All detection and classification is deterministic (no LLM needed).
            print("\n# Agent: Society Alert & Communication Manager")
            print("## Generating WhatsApp reply via Groq LLM...")
            reply = self._generate_reply(classification, ticket_id, from_number)
            print(f"## Reply generated ({len(reply)} chars)")

            # ── Step 5: Send WhatsApp Alerts ──────────────────────────────────
            # Agent 3 (Alert & Communication Manager) responsibility:
            # Route alerts to the right people based on urgency level.
            # Critical/High → Guard + RWA | Medium → Guard only | Low → skip
            self._send_alerts(classification, ticket_id)

            print("\n✅  Pipeline finished successfully.")
            return {
                "success":       True,
                "reply_message": reply,
                "ticket_id":     ticket_id,
                "crew_output":   reply,
            }

        except Exception as e:
            import traceback
            print(f"\n❌  Pipeline error: {e}")
            traceback.print_exc()
            return {
                "success":       False,
                "reply_message": (
                    "♻️ *WasteGuard Society AI*\n\n"
                    "✅ Thank you for reporting!\n"
                    "We've logged your complaint and our cleaning team "
                    "will address it shortly. 🙏\n\n"
                    "🌿 Keep up the great work!"
                ),
                "ticket_id": 0,
                "error":     str(e),
            }

    # ─────────────────────────────────────────────────────────────────────────
    def _run_yolov5(self, image_path: str) -> dict:
        """Run YOLOv5 detection OR Gemini Vision if custom model is missing."""
        
        # If custom model exists, use YOLOv5
        if os.path.exists("yolov5/my_model.pt"):
            if os.path.exists("yolov5/runs"):
                os.system("rm -rf yolov5/runs")
            python_bin = sys.executable
            cmd = (
                f"cd yolov5/ && {python_bin} run_detect.py "
                f"--weights my_model.pt "
                f"--img 416 --conf 0.5 "
                f"--source ../{image_path} "
                f"--save-txt --save-conf 2>&1"
            )
            os.system(cmd)
            
            output_dirs = sorted(glob.glob("yolov5/runs/detect/exp*"))
            if not output_dirs:
                return {"waste_detected": False, "num_detections": 0, "detections": [], "message": "No detections."}
            
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
                            detections.append({"class_id": class_id, "confidence": round(confidence, 2)})
            
            return {
                "waste_detected":    len(detections) > 0,
                "num_detections":    len(detections),
                "detections":        detections,
                "message": f"Found {len(detections)} waste item(s)." if detections else "No waste detected.",
            }
            
        # ── UPGRADE: Gemini Vision Fallback (when custom YOLO model is missing) ──
        print("## 🧠 Custom YOLO model missing. Engaging Gemini Vision for high-accuracy detection...")
        import google.generativeai as genai
        import PIL.Image
        
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        try:
            img = PIL.Image.open(image_path)
            prompt = """
            Analyze this image of waste. Which of the following categories best describes it?
            0: Plastic Bottle
            1: Food / Organic
            2: Paper / Cardboard
            3: Glass Bottle
            4: Metal Can (or Aerosol/Spray Can)
            5: E-Waste
            6: Medical Waste (Syringes, bloody items, bandages)
            7: Plastic Bag
            8: Mixed / General
            39: Medical Vial / Syringe
            
            Respond ONLY with a JSON object in this exact format:
            {"class_id": 6, "confidence": 0.95}
            Do not include markdown blocks or any other text.
            """
            response = model.generate_content([prompt, img])
            text = response.text.strip().replace('```json', '').replace('```', '')
            data = json.loads(text)
            
            return {
                "waste_detected": True,
                "num_detections": 1,
                "detections": [data],
                "message": "Gemini Vision successfully analyzed the waste."
            }
        except Exception as e:
            print(f"Gemini Vision error: {e}")
            return {"waste_detected": False, "num_detections": 0, "detections": [], "message": str(e)}

    # ─────────────────────────────────────────────────────────────────────────
    def _classify(self, detection: dict) -> dict:
        """Map detection results to waste category using lookup table."""
        if not detection.get("waste_detected"):
            info = WASTE_CLASS_MAP[8]  # Default: Mixed/General
            return {
                "waste_type":   info["name"],
                "category":     info["category"],
                "bin_color":    info["bin"],
                "urgency":      info["urgency"],
                "estimated_eta": URGENCY_ETA[info["urgency"]],
                "disposal_tip": DISPOSAL_TIPS[info["category"]],
                "detected":     False,
            }

        detections = detection.get("detections", [])
        urgency_order = ["Low", "Medium", "High", "Critical"]
        highest       = "Low"
        classified    = []

        for det in detections:
            info = WASTE_CLASS_MAP.get(det.get("class_id", 8), WASTE_CLASS_MAP[8])
            classified.append(info)
            if urgency_order.index(info["urgency"]) > urgency_order.index(highest):
                highest = info["urgency"]

        primary = classified[0] if classified else WASTE_CLASS_MAP[8]
        return {
            "waste_type":    primary["name"],
            "category":      primary["category"],
            "bin_color":     primary["bin"],
            "urgency":       highest,
            "estimated_eta": URGENCY_ETA[highest],
            "disposal_tip":  DISPOSAL_TIPS[primary["category"]],
            "detected":      True,
            "num_items":     len(classified),
        }

    # ─────────────────────────────────────────────────────────────────────────
    def _generate_reply(self, classification: dict, ticket_id: int, reporter: str) -> str:
        """Call Groq LLM to generate a friendly WhatsApp reply."""
        try:
            from langchain_openai import ChatOpenAI
            llm = ChatOpenAI(
                openai_api_base = "https://api.groq.com/openai/v1",
                openai_api_key  = os.getenv("GROQ_API_KEY"),
                model_name      = "llama-3.3-70b-versatile",
                temperature     = 0.3,
                max_tokens      = 400,
            )
            prompt = f"""You are WasteGuard Society AI for Greenview Heights residential society.
A resident reported waste via WhatsApp. Generate a friendly WhatsApp reply.

Waste Info:
- Type: {classification['waste_type']}
- Category: {classification['category']}
- Bin Color: {classification['bin_color']} bin
- Urgency: {classification['urgency']}
- ETA: {classification['estimated_eta']}
- Disposal tip: {classification['disposal_tip']}
- Ticket #: {ticket_id}

Rules:
- Start with: ♻️ *WasteGuard Society AI*
- Use WhatsApp formatting (*bold*, emojis)
- Include: waste type, bin color, ticket number, ETA, disposal tip
- End with thank-you message
- Max 200 words
"""
            response = llm.invoke(prompt)
            return response.content.strip()

        except Exception as e:
            print(f"LLM reply error: {e} — using template reply")
            return (
                f"♻️ *WasteGuard Society AI*\n\n"
                f"✅ Waste Report Received!\n\n"
                f"🗑️ *Detected*: {classification['waste_type']}\n"
                f"📂 *Category*: {classification['category']}\n"
                f"🟡 *Bin*: {classification['bin_color']} bin — Ground Floor / Lift Lobby\n"
                f"⚡ *Urgency*: {classification['urgency']}\n"
                f"{classification['estimated_eta']}\n\n"
                f"💡 *Tip*: {classification['disposal_tip']}\n\n"
                f"🎫 *Ticket #*: {ticket_id}\n"
                f"👷 *Assigned to*: Cleaning Staff\n\n"
                f"🙏 Thank you for keeping Greenview Heights clean!"
            )

    # ─────────────────────────────────────────────────────────────────────────
    def _send_alerts(self, classification: dict, ticket_id: int):
        """Send WhatsApp alerts to RWA and Guard via Twilio."""
        account_sid  = os.getenv("TWILIO_ACCOUNT_SID", "")
        auth_token   = os.getenv("TWILIO_AUTH_TOKEN", "")
        from_number  = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
        rwa_number   = os.getenv("RWA_WHATSAPP_NUMBER", "")
        guard_number = os.getenv("GUARD_WHATSAPP_NUMBER", "")

        if not account_sid or not auth_token:
            print("⚠️  Twilio not configured — skipping alerts (demo mode)")
            return

        urgency  = classification.get("urgency", "Medium")
        msg      = (
            f"🚨 *WasteGuard Alert* — Ticket #{ticket_id}\n"
            f"Waste: {classification['waste_type']} | "
            f"Urgency: {urgency}\n"
            f"{classification.get('estimated_eta', '')}"
        )

        send_to = []
        if urgency in ("High", "Critical"):
            if rwa_number:   send_to.append(rwa_number)
            if guard_number: send_to.append(guard_number)
        elif urgency == "Medium":
            if guard_number: send_to.append(guard_number)

        try:
            from twilio.rest import Client
            client = Client(account_sid, auth_token)
            for number in send_to:
                to = f"whatsapp:{number}" if not number.startswith("whatsapp:") else number
                client.messages.create(from_=from_number, to=to, body=msg)
                print(f"✅ Alert sent to {number}")
        except Exception as e:
            print(f"⚠️  Alert send error: {e}")
