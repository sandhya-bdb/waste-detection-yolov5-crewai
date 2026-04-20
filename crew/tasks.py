"""
CrewAI Tasks for WasteGuard Society AI
4 sequential tasks: Detection → Classification → Alert → Ticket & Reply
"""
import os
from crewai import Task
from crew.agents import (
    get_detector_agent,
    get_classifier_agent,
    get_alert_agent,
    get_ticket_agent,
)


def create_tasks(image_path: str, from_number: str) -> tuple:
    """
    Build the 4 CrewAI tasks and return them with their agents.

    Args:
        image_path:   Local path to the uploaded waste image
        from_number:  Resident's WhatsApp number (without 'whatsapp:' prefix)

    Returns:
        (tasks_list, agents_list)
    """
    detector    = get_detector_agent()
    classifier  = get_classifier_agent()
    alerter     = get_alert_agent()
    ticket_mgr  = get_ticket_agent()

    rwa_number   = os.getenv("RWA_WHATSAPP_NUMBER",   "+919999999999")
    guard_number = os.getenv("GUARD_WHATSAPP_NUMBER", "+918888888888")

    # ── TASK 1: Detect waste ─────────────────────────────────────────────────
    detection_task = Task(
        description=(
            f"A resident has sent a photo via WhatsApp. Analyze the image at:\n"
            f"  IMAGE PATH: {image_path}\n\n"
            f"Use the *Waste Detection Tool* with this exact path.\n"
            f"Return the complete raw JSON from the tool — do not paraphrase.\n"
            f"The JSON must include: waste_detected, num_detections, detections "
            f"(list with class_id and confidence), output_image_path, and message."
        ),
        expected_output=(
            "A JSON string with keys: waste_detected (bool), num_detections (int), "
            "detections (list), output_image_path (str or null), message (str)."
        ),
        agent=detector,
    )

    # ── TASK 2: Classify waste ───────────────────────────────────────────────
    classification_task = Task(
        description=(
            "Take the exact JSON string from the previous detection task.\n"
            "Pass it directly to the *Waste Classifier Tool* as the detection_result argument.\n"
            "Return the complete raw JSON from the classifier tool.\n"
            "The JSON must include: classified, primary_waste, category, bin_color, "
            "bin_location, urgency, estimated_eta, disposal_tip."
        ),
        expected_output=(
            "A JSON string with keys: classified (bool), primary_waste (str), "
            "category (str), bin_color (str), bin_location (str), urgency (str), "
            "estimated_eta (str), disposal_tip (str), output_image_path (str)."
        ),
        agent=classifier,
        context=[detection_task],
    )

    # ── TASK 3: Send alerts ─────────────────────────────────────────────────
    alert_task = Task(
        description=(
            f"Based on the classification result, send WhatsApp alerts using these rules:\n\n"
            f"  • urgency = Critical OR High → alert BOTH:\n"
            f"      Guard : {guard_number}\n"
            f"      RWA   : {rwa_number}\n"
            f"  • urgency = Medium → alert Guard only: {guard_number}\n"
            f"  • urgency = Low    → no alert needed, skip the tool call\n\n"
            f"Message template:\n"
            f"'🚨 WasteGuard Alert!\n"
            f"Waste Detected: [primary_waste]\n"
            f"Category: [category] | Urgency: [urgency]\n"
            f"Location: Society Common Area\n"
            f"Please arrange cleanup. Ticket being created.'\n\n"
            f"Use the *WhatsApp Messenger* tool for each recipient.\n"
            f"Report back which numbers were alerted and their status."
        ),
        expected_output=(
            "A summary of alerts sent: list of phone numbers contacted and "
            "their send status (sent / demo_logged / skipped)."
        ),
        agent=alerter,
        context=[classification_task],
    )

    # ── TASK 4: Create ticket & compose resident reply ───────────────────────
    ticket_task = Task(
        description=(
            f"Do two things:\n\n"
            f"1. Call the *Ticket Manager* tool with:\n"
            f"   - waste_type   : from classification result (primary_waste)\n"
            f"   - category     : from classification result\n"
            f"   - urgency      : from classification result\n"
            f"   - location     : 'Society Common Area (WhatsApp Report)'\n"
            f"   - reported_by  : {from_number}\n"
            f"   - disposal_tip : from classification result\n\n"
            f"2. Compose a warm, friendly WhatsApp reply for the resident using:\n"
            f"   - The ticket ID returned by the tool\n"
            f"   - All classification details\n\n"
            f"Reply format (use this exactly, fill in values):\n"
            f"♻️ *WasteGuard Society AI*\n\n"
            f"✅ Waste detected & processed!\n\n"
            f"🔍 *Detected:* [primary_waste]\n"
            f"🏷️ *Category:* [category]\n"
            f"🗑️ *Bin:* [bin_location]\n"
            f"⚠️ *Urgency:* [urgency]\n\n"
            f"🎫 *Ticket #[ticket_id]* created\n"
            f"👷 Assigned to: Cleaning Staff\n"
            f"[estimated_eta]\n\n"
            f"💡 *Tip:* [disposal_tip]\n\n"
            f"🙏 Thank you for keeping Greenview Heights clean!\n"
            f"Your complaint will be resolved soon. 🌿\n\n"
            f"Return BOTH the ticket_id number AND the full reply_message text."
        ),
        expected_output=(
            "Two things: (1) ticket_id as a number, "
            "(2) reply_message as the complete formatted WhatsApp message string."
        ),
        agent=ticket_mgr,
        context=[detection_task, classification_task, alert_task],
    )

    tasks  = [detection_task, classification_task, alert_task, ticket_task]
    agents = [detector, classifier, alerter, ticket_mgr]
    return tasks, agents
