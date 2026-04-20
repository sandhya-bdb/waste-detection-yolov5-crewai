"""
WhatsApp Notification Tool for CrewAI
Sends WhatsApp messages via Twilio API
Falls back to console logging when Twilio is not configured (demo/dev mode)
"""
import os
import json
from typing import Type
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool


class WhatsAppInputSchema(BaseModel):
    to_number: str = Field(
        ...,
        description="Recipient's WhatsApp phone number with country code (e.g. +919876543210)"
    )
    message: str = Field(
        ...,
        description="The text message to send via WhatsApp"
    )


class WhatsAppTool(BaseTool):
    name: str = "WhatsApp Messenger"
    description: str = (
        "Sends a WhatsApp text message to a specified phone number using Twilio. "
        "Use this to alert the security guard, RWA committee, or cleaning staff. "
        "Provide the recipient's phone number with country code and the message text."
    )
    args_schema: Type[BaseModel] = WhatsAppInputSchema

    def _run(self, to_number: str = "", message: str = "", **kwargs) -> str:
        # Handle dict input from crewai's ReAct agent
        if isinstance(to_number, dict):
            d = to_number
            to_number = d.get("to_number", "")
            message   = d.get("message", message)
        to_number = to_number or os.getenv("RWA_WHATSAPP_NUMBER", "+919999999999")
        message   = message or "Alert: Waste detected in society area."

        account_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
        auth_token  = os.getenv("TWILIO_AUTH_TOKEN", "")
        from_number = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")

        # ── DEMO / DEV MODE when Twilio not configured ──────────────────────
        if not account_sid or not auth_token:
            print("\n" + "="*55)
            print("📱  [WHATSAPP DEMO — Twilio not configured]")
            print(f"   TO      : {to_number}")
            print(f"   MESSAGE :\n{message}")
            print("="*55 + "\n")
            return json.dumps({
                "status":  "demo_logged",
                "to":      to_number,
                "message": message,
                "note":    "Twilio credentials missing — message printed to console."
            })

        # ── PRODUCTION MODE via Twilio ───────────────────────────────────────
        try:
            from twilio.rest import Client
            client = Client(account_sid, auth_token)

            to_formatted = (
                f"whatsapp:{to_number}"
                if not to_number.startswith("whatsapp:")
                else to_number
            )

            msg = client.messages.create(
                from_=from_number,
                to=to_formatted,
                body=message,
            )
            return json.dumps({
                "status": "sent",
                "sid":    msg.sid,
                "to":     to_number,
            })

        except Exception as e:
            print(f"⚠️  WhatsApp send error: {e}")
            return json.dumps({
                "status":  "error",
                "to":      to_number,
                "message": message,
                "error":   str(e),
            })
