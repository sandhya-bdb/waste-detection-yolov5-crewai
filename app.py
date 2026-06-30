import sys, os
import threading
import requests as req_lib
from dotenv import load_dotenv
from wasteDetection.pipeline.training_pipeline import TrainPipeline
from wasteDetection.utils.main_utils import decodeImage, encodeImageIntoBase64
from flask import Flask, request, jsonify, render_template, Response
from flask_cors import CORS, cross_origin
from wasteDetection.constant.application import APP_HOST, APP_PORT

# ── Security: import WasteGuard security modules ─────────────────────────────
# Security Feature 1: Twilio HMAC-SHA1 webhook signature validation
from crew.security.auth import validate_twilio_signature, validate_image
# Security Feature 3: Per-number sliding-window rate limiter
from crew.security.rate_limiter import limiter

load_dotenv()  # Load .env file


app = Flask(__name__)
CORS(app)

class ClientApp:
    def __init__(self):
        self.filename = "inputImage.jpg"



@app.route("/train")
def trainRoute():
    obj = TrainPipeline()
    obj.run_pipeline()
    return "Training Successfull!!" 


@app.route("/")
def home():
    return render_template("index.html")



@app.route("/predict", methods=['POST','GET'])
@cross_origin()
def predictRoute():
    try:
        image = request.json['image']
        decodeImage(image, clApp.filename)

        os.system("cd yolov5/ && python detect.py --weights yolov5s.pt --img 416 --conf 0.5 --source ../data/inputImage.jpg")

        opencodedbase64 = encodeImageIntoBase64("yolov5/runs/detect/exp/inputImage.jpg")
        result = {"image": opencodedbase64.decode('utf-8')}
        os.system("rm -rf yolov5/runs")

    except ValueError as val:
        print(val)
        return Response("Value not found inside  json data")
    except KeyError:
        return Response("Key value error incorrect key passed")
    except Exception as e:
        print(e)
        result = "Invalid input"

    return jsonify(result)



@app.route("/live", methods=['GET'])
@cross_origin()
def predictLive():
    try:
        os.system("cd yolov5/ && python detect.py --weights yolov5s.pt --img 416 --conf 0.5 --source 0")
        os.system("rm -rf yolov5/runs")
        return "Camera starting!!" 

    except ValueError as val:
        print(val)
        return Response("Value not found inside  json data")
    



# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# WHATSAPP WEBHOOK  (Twilio → Flask → CrewAI)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@app.route("/whatsapp", methods=["POST"])
@cross_origin()
@validate_twilio_signature  # Security Feature 1: reject requests not signed by Twilio
def whatsapp_webhook():
    """Twilio WhatsApp webhook — receives messages and orchestrates CrewAI"""
    from crew.waste_crew import WasteCrew
    try:
        from twilio.twiml.messaging_response import MessagingResponse
    except ImportError:
        return "Twilio not installed. Run: pip install twilio", 500

    resp         = MessagingResponse()
    from_number  = request.form.get("From", "").replace("whatsapp:", "")
    num_media    = int(request.form.get("NumMedia", 0))
    body         = request.form.get("Body", "").lower().strip()

    # ── Security Feature 3: Rate limiting ────────────────────────────────────
    # Prevent a single number from flooding the pipeline (max 5 requests / 10 min)
    allowed, wait_secs = limiter.check(from_number)
    if not allowed:
        resp.message(
            f"⏳ *WasteGuard Society AI*\n\n"
            f"You've sent too many requests recently.\n"
            f"Please wait {wait_secs // 60} min {wait_secs % 60} sec before sending another photo.\n"
            f"This limit helps us serve all {400} residents fairly. 🙏"
        )
        return str(resp)

    # ── Text-only messages ───────────────────────────────────────────────────
    if num_media == 0:
        if any(kw in body for kw in ["hi", "hello", "help", "start"]):
            resp.message(
                "👋 Welcome to *WasteGuard Society AI* 🌿\n\n"
                "📸 Send a *photo* of any waste in the society area and I will:\n"
                "  ✅ Detect & classify the waste\n"
                "  🔔 Alert the cleaning team\n"
                "  🎫 Create a complaint ticket\n"
                "  💡 Give you disposal tips\n\n"
                "Let's keep Greenview Heights clean! 🏘️"
            )
        else:
            resp.message(
                "📸 Please send a *photo* of the waste you want to report.\n"
                "Type *help* for more information."
            )
        return str(resp)

    # ── Image message ────────────────────────────────────────────────────────
    media_url     = request.form.get("MediaUrl0", "")
    content_type  = request.form.get("MediaContentType0", "")

    if not media_url or "image" not in content_type:
        resp.message("⚠️ Please send an *image* file. Other formats are not supported yet.")
        return str(resp)

    # Immediate acknowledgment (Twilio requires response within 15 s)
    resp.message(
        "📸 Image received! 🤖\n"
        "Our AI crew is analysing it...\n"
        "⏳ Detailed report coming in a few seconds!"
    )

    # ── Download image from Twilio ───────────────────────────────────────────
    account_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
    auth_token  = os.getenv("TWILIO_AUTH_TOKEN", "")
    # Use credentials for authenticated Twilio media download
    auth        = (account_sid, auth_token) if account_sid else None

    img_response = req_lib.get(media_url, auth=auth, timeout=15)

    # ── Security Feature 2: Validate image content-type and size ────────────
    # Ensures only safe image files are written to disk (prevents malicious uploads)
    content_type   = img_response.headers.get("Content-Type", "")
    image_bytes    = img_response.content
    is_valid, reason = validate_image(content_type, image_bytes)
    if not is_valid:
        resp.message(
            f"⚠️ *WasteGuard Society AI*\n\n"
            f"We couldn't process your file: {reason}\n"
            f"Please send a clear photo (JPG/PNG) under 10 MB."
        )
        return str(resp)

    os.makedirs("data", exist_ok=True)
    image_path = "data/inputImage.jpg"
    with open(image_path, "wb") as f:
        f.write(image_bytes)  # Write only after security validation passes

    # ── Run CrewAI in background, send result via Twilio ────────────────────
    def run_crew_and_reply():
        try:
            waste_crew = WasteCrew()
            result     = waste_crew.run(
                image_path=image_path,
                from_number=from_number,
                media_url=media_url,
            )
            reply = result["reply_message"]
        except Exception as e:
            reply = (
                "♻️ *WasteGuard Society AI*\n\n"
                "✅ Report received! Our team has been notified.\n"
                "🙏 Thank you for keeping our society clean!"
            )
            print(f"Crew error: {e}")

        # Send the detailed reply back via Twilio
        if account_sid and auth_token:
            try:
                from twilio.rest import Client
                client = Client(account_sid, auth_token)
                client.messages.create(
                    from_=os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886"),
                    to=f"whatsapp:{from_number}",
                    body=reply,
                )
            except Exception as e:
                print(f"Twilio reply error: {e}")
        else:
            # Demo mode — print to console
            print("\n" + "="*55)
            print("📱  [DEMO] WhatsApp Reply to resident:")
            print(reply)
            print("="*55 + "\n")

    threading.Thread(target=run_crew_and_reply, daemon=True).start()
    return str(resp)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# RWA DASHBOARD — view all tickets
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@app.route("/dashboard")
def dashboard():
    """Web interface for monitoring WasteGuard AI pipeline"""
    return render_template("dashboard.html")

@app.route("/api/dashboard")
def api_dashboard():
    """Returns JSON dashboard stats and tickets list for AJAX calls."""
    from crew.db.database import get_all_tickets, get_stats
    return jsonify({
        "stats":   get_stats(),
        "tickets": get_all_tickets(),
    })


@app.route("/api/update_ticket", methods=["POST"])
def api_update_ticket():
    """Endpoint to update a ticket's status (Open, In Progress, Resolved)."""
    from crew.db.database import update_ticket_status
    try:
        data = request.json
        ticket_id = int(data.get("ticket_id"))
        status = data.get("status")
        update_ticket_status(ticket_id, status)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400


@app.route("/api/demo_predict", methods=["POST"])
def api_demo_predict():
    """Runs the YOLOv5 and Agent pipeline on a sample or uploaded image."""
    from crew.waste_crew import WasteCrew
    try:
        data = request.json
        image_path = data.get("image_path")
        image_base64 = data.get("image_base64")
        from_number = data.get("from_number", "+919876543210")

        # Handle custom base64 image upload
        if image_base64:
            os.makedirs("data", exist_ok=True)
            target_path = "data/demo_upload.jpg"
            decodeImage(image_base64, target_path)
            image_path = target_path
        elif not image_path:
            return jsonify({"success": False, "message": "No image source provided"}), 400

        # Execute waste pipeline synchronously for the demo tester
        waste_crew = WasteCrew()
        result = waste_crew.run(
            image_path=image_path,
            from_number=from_number,
            media_url=""
        )

        if result.get("success", False):
            # Parse database stats & classification to return cleanly
            from crew.db.database import get_ticket
            ticket_id = result.get("ticket_id", 0)
            ticket_info = get_ticket(ticket_id) if ticket_id else {}
            
            # --- NEW: Actually send the WhatsApp message to the provided phone number ---
            account_sid = os.getenv("TWILIO_ACCOUNT_SID")
            auth_token = os.getenv("TWILIO_AUTH_TOKEN")
            if account_sid and auth_token and from_number:
                try:
                    from twilio.rest import Client
                    client = Client(account_sid, auth_token)
                    client.messages.create(
                        from_=os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886"),
                        to=f"whatsapp:{from_number}" if not from_number.startswith("whatsapp:") else from_number,
                        body=result.get("reply_message")
                    )
                    print(f"✅ Sent demo WhatsApp reply to {from_number}")
                except Exception as e:
                    print(f"⚠️ Could not send Twilio message to {from_number}: {e}")
            # --------------------------------------------------------------------------

            # Form simulated alerts response details
            urgency = ticket_info.get("urgency", "Low")
            alerts = []
            if urgency in ["Critical", "High"]:
                alerts = ["Guard notified (+918888888888)", "RWA notified (+919999999999)"]
            elif urgency == "Medium":
                alerts = ["Guard notified (+918888888888)"]
            else:
                alerts = ["No alerts routed (low urgency)"]

            return jsonify({
                "success": True,
                "pipeline_output": {
                    "reply_message": result.get("reply_message"),
                    "ticket_id": ticket_id,
                    "detections": result.get("detections", []),
                    "classification": {
                        "waste_type": ticket_info.get("waste_type"),
                        "category": ticket_info.get("category"),
                        "urgency": urgency,
                        "bin": ticket_info.get("disposal_tip")
                    },
                    "alerts": alerts
                }
            })
        else:
            return jsonify({"success": False, "message": result.get("error", "Unknown pipeline error")})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": str(e)}), 500


# ── Static directory routing for images and data ──────────────────────────────
@app.route("/images/<path:filename>")
def serve_images_dir(filename):
    from flask import send_from_directory
    return send_from_directory("images", filename)


@app.route("/data/<path:filename>")
def serve_data_dir(filename):
    from flask import send_from_directory
    return send_from_directory("data", filename)


if __name__ == "__main__":
    clApp = ClientApp()
    app.run(host=APP_HOST, port=APP_PORT)

