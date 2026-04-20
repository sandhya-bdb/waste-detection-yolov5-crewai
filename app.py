import sys, os
import threading
import requests as req_lib
from dotenv import load_dotenv
from wasteDetection.pipeline.training_pipeline import TrainPipeline
from wasteDetection.utils.main_utils import decodeImage, encodeImageIntoBase64
from flask import Flask, request, jsonify, render_template, Response
from flask_cors import CORS, cross_origin
from wasteDetection.constant.application import APP_HOST, APP_PORT

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

        os.system("cd yolov5/ && python detect.py --weights my_model.pt --img 416 --conf 0.5 --source ../data/inputImage.jpg")

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
        os.system("cd yolov5/ && python detect.py --weights my_model.pt --img 416 --conf 0.5 --source 0")
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
    auth        = (account_sid, auth_token) if account_sid else None

    img_response = req_lib.get(media_url, auth=auth, timeout=15)
    os.makedirs("data", exist_ok=True)
    image_path = "data/inputImage.jpg"
    with open(image_path, "wb") as f:
        f.write(img_response.content)

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
    """Simple JSON dashboard for RWA to see all tickets and stats."""
    from crew.db.database import get_all_tickets, get_stats
    return jsonify({
        "stats":   get_stats(),
        "tickets": get_all_tickets(),
    })


if __name__ == "__main__":
    clApp = ClientApp()
    app.run(host=APP_HOST, port=APP_PORT)

