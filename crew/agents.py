"""
CrewAI Agents for WasteGuard Society AI
All 4 agents: Detector, Classifier, Alert, TicketManager
LLM: Groq via OpenAI-compatible endpoint

Architecture Note:
  These agent and task definitions represent the FULL CrewAI orchestration design
  for WasteGuard. In the current prototype, waste_crew.py uses a direct Python
  pipeline instead of invoking Crew.kickoff(), because:
    1. CrewAI's ReAct agent loop can stall on tool-call parse failures at demo time
    2. The direct pipeline gives deterministic, predictable output for demos
  These agent definitions remain as the intended production architecture.
  Switching to full CrewAI orchestration is a documented next step.
LLM: Groq via OpenAI-compatible endpoint
"""
import os
from crewai import Agent
from langchain_openai import ChatOpenAI

from crew.tools.yolov5_tool    import YOLOv5DetectionTool
from crew.tools.classifier_tool import WasteClassifierTool
from crew.tools.whatsapp_tool  import WhatsAppTool
from crew.tools.ticket_tool    import TicketManagerTool

# ── Groq LLM via OpenAI-compatible endpoint ──────────────────────────────────
# ChatOpenAI pointed at Groq's endpoint bypasses litellm routing issues in crewai 0.63
groq_llm = ChatOpenAI(
    openai_api_base="https://api.groq.com/openai/v1",
    openai_api_key=os.getenv("GROQ_API_KEY"),
    model_name="llama-3.1-8b-instant",
    temperature=0.1,
    max_tokens=1024,
)

# ── Tool instances ────────────────────────────────────────────────────────────
yolov5_tool    = YOLOv5DetectionTool()
classifier_tool = WasteClassifierTool()
whatsapp_tool  = WhatsAppTool()
ticket_tool    = TicketManagerTool()



# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# AGENT 1 — Waste Detector
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def get_detector_agent() -> Agent:
    return Agent(
        role="Waste Detection Specialist",
        goal=(
            "Accurately detect whether waste is present in an image and "
            "return a structured JSON detection result."
        ),
        backstory=(
            "You are a computer vision specialist deployed at Greenview Heights — "
            "a residential society with 400 families. Residents send you photos via "
            "WhatsApp and you run them through the YOLOv5 waste detection model. "
            "You always use the Waste Detection Tool and return the raw JSON result. "
            "You never make up detections — if the tool says nothing is found, you report that."
        ),
        tools=[yolov5_tool],
        llm=groq_llm,
        verbose=True,
        allow_delegation=False,
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# AGENT 2 — Waste Classifier
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def get_classifier_agent() -> Agent:
    return Agent(
        role="Waste Classification Expert",
        goal=(
            "Classify detected waste into categories (Dry/Wet/Hazardous) "
            "and provide bin location, urgency level, and disposal tips."
        ),
        backstory=(
            "You are an environmental expert who knows all municipality waste "
            "management rules. Given a detection result, you classify the waste type, "
            "assign the correct bin colour, estimate urgency, and generate clear "
            "disposal instructions for residents. You always call the Waste Classifier Tool."
        ),
        tools=[classifier_tool],
        llm=groq_llm,
        verbose=True,
        allow_delegation=False,
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# AGENT 3 — Alert Agent
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def get_alert_agent() -> Agent:
    rwa_number   = os.getenv("RWA_WHATSAPP_NUMBER",   "+919999999999")
    guard_number = os.getenv("GUARD_WHATSAPP_NUMBER", "+918888888888")

    return Agent(
        role="Society Alert & Communication Manager",
        goal=(
            "Send targeted WhatsApp alerts to the right stakeholders "
            "based on the waste urgency level."
        ),
        backstory=(
            f"You are the communication manager for Greenview Heights society. "
            f"You know exactly who to notify for each incident:\n"
            f"  • Critical / High  → Alert both Guard ({guard_number}) AND RWA ({rwa_number})\n"
            f"  • Medium           → Alert Guard ({guard_number}) only\n"
            f"  • Low              → No alert needed, just log it\n"
            f"You craft short, clear messages with waste type, location, and urgency. "
            f"Always use the WhatsApp Messenger tool to send alerts."
        ),
        tools=[whatsapp_tool],
        llm=groq_llm,
        verbose=True,
        allow_delegation=False,
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# AGENT 4 — Ticket Manager
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def get_ticket_agent() -> Agent:
    return Agent(
        role="Complaint & Resolution Coordinator",
        goal=(
            "Create a complaint ticket for every incident and compose a "
            "clear, friendly WhatsApp confirmation message for the reporting resident."
        ),
        backstory=(
            "You are the operations coordinator for Greenview Heights. "
            "You log every waste complaint in the database using the Ticket Manager tool, "
            "then compose a warm and informative WhatsApp reply for the resident including: "
            "detected waste type, category, correct bin, ticket number, assigned staff, "
            "estimated resolution time, and a disposal tip. "
            "Your messages always start with '♻️ *WasteGuard Society AI*' and end with "
            "a thank-you for keeping the society clean."
        ),
        tools=[ticket_tool],
        llm=groq_llm,
        verbose=True,
        allow_delegation=False,
    )
