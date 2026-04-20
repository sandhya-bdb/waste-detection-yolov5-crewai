"""
Waste Classifier Tool for CrewAI
Maps YOLOv5 detection results to waste categories, bin info, and disposal tips
"""
import json
from typing import Type
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool


class ClassifierInputSchema(BaseModel):
    detection_result: str = Field(
        ...,
        description="The JSON string output from the Waste Detection Tool"
    )


# ── Waste class map — update class IDs to match your trained model's classes ──
WASTE_CLASS_MAP = {
    0: {"name": "Plastic Bottle",   "category": "Dry Waste",       "bin": "Yellow", "urgency": "Medium"},
    1: {"name": "Food / Organic",   "category": "Wet Waste",       "bin": "Green",  "urgency": "High"},
    2: {"name": "Paper / Cardboard","category": "Dry Waste",       "bin": "Yellow", "urgency": "Low"},
    3: {"name": "Glass Bottle",     "category": "Dry Waste",       "bin": "Yellow", "urgency": "Medium"},
    4: {"name": "Metal Can",        "category": "Dry Waste",       "bin": "Yellow", "urgency": "Low"},
    5: {"name": "E-Waste",          "category": "Hazardous Waste", "bin": "Red",    "urgency": "High"},
    6: {"name": "Medical Waste",    "category": "Hazardous Waste", "bin": "Red",    "urgency": "Critical"},
    7: {"name": "Plastic Bag",      "category": "Dry Waste",       "bin": "Yellow", "urgency": "Medium"},
    8: {"name": "Mixed / General",  "category": "General Waste",   "bin": "Grey",   "urgency": "Medium"},
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

URGENCY_ORDER = ["Low", "Medium", "High", "Critical"]


class WasteClassifierTool(BaseTool):
    name: str = "Waste Classifier Tool"
    description: str = (
        "Classifies the detected waste into categories (Dry/Wet/Hazardous/General) "
        "and returns bin color, bin location, urgency level, estimated resolution "
        "time, and disposal instructions. "
        "Input must be the JSON string from the Waste Detection Tool."
    )
    args_schema: Type[BaseModel] = ClassifierInputSchema

    def _run(self, detection_result: str = "", **kwargs) -> str:
        # Handle both string and dict inputs from crewai's ReAct agent
        if isinstance(detection_result, dict):
            detection_result = detection_result.get("detection_result", "{}")
        if not detection_result:
            detection_result = "{}"

        try:
            data = json.loads(detection_result)

            if not data.get("waste_detected"):
                return json.dumps({
                    "classified": False,
                    "message": "No waste detected — nothing to classify."
                })

            detections      = data.get("detections", [])
            highest_urgency = "Low"
            classified      = []

            for det in detections:
                info = WASTE_CLASS_MAP.get(det.get("class_id", 8), WASTE_CLASS_MAP[8])
                classified.append({
                    "name":       info["name"],
                    "category":   info["category"],
                    "bin_color":  info["bin"],
                    "urgency":    info["urgency"],
                    "confidence": det.get("confidence", 0.75),
                })
                if URGENCY_ORDER.index(info["urgency"]) > URGENCY_ORDER.index(highest_urgency):
                    highest_urgency = info["urgency"]

            # Use primary (first) detection as the lead
            primary = classified[0] if classified else WASTE_CLASS_MAP[8]

            return json.dumps({
                "classified":         True,
                "primary_waste":      primary["name"] if isinstance(primary, dict) and "name" in primary else primary.get("name","Unknown"),
                "category":           primary["category"] if isinstance(primary, dict) else primary.get("category","General Waste"),
                "bin_color":          primary["bin_color"] if isinstance(primary, dict) else primary.get("bin","Grey"),
                "bin_location":       f"{primary['bin_color'] if isinstance(primary, dict) else primary.get('bin','Grey')} bin — Ground Floor / Lift Lobby",
                "urgency":            highest_urgency,
                "estimated_eta":      URGENCY_ETA[highest_urgency],
                "disposal_tip":       DISPOSAL_TIPS.get(
                                          primary["category"] if isinstance(primary, dict) else primary.get("category","General Waste"),
                                          DISPOSAL_TIPS["General Waste"]
                                      ),
                "all_items":          classified,
                "output_image_path":  data.get("output_image_path"),
                "num_items":          len(classified),
            })

        except Exception as e:
            return json.dumps({
                "classified": False,
                "error": str(e),
                "message": "Classification failed."
            })
