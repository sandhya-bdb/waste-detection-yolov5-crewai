"""
Ticket Manager Tool for CrewAI
Creates and manages waste complaint tickets in SQLite
"""
import os
import sys
import json
from typing import Type
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from crew.db.database import create_ticket, update_ticket_status


class TicketCreateSchema(BaseModel):
    waste_type: str   = Field(..., description="Name of the waste detected (e.g. 'Plastic Bottle')")
    category:   str   = Field(..., description="Waste category: Dry Waste, Wet Waste, Hazardous Waste, or General Waste")
    urgency:    str   = Field(..., description="Urgency level: Low, Medium, High, or Critical")
    location:   str   = Field(default="Society Common Area", description="Location where waste was found")
    reported_by: str  = Field(..., description="WhatsApp number of the resident who reported")
    disposal_tip: str = Field(default="", description="Disposal tip to store with the ticket")


class TicketManagerTool(BaseTool):
    name: str = "Ticket Manager"
    description: str = (
        "Creates a waste complaint ticket in the society database. "
        "Returns the ticket ID, assigned staff, and confirmation. "
        "Call this for every waste incident to maintain proper records for the RWA."
    )
    args_schema: Type[BaseModel] = TicketCreateSchema

    def _run(self, waste_type: str = "Unknown", category: str = "General Waste",
             urgency: str = "Medium", location: str = "Society Common Area",
             reported_by: str = "unknown", disposal_tip: str = "", **kwargs) -> str:
        # Handle dict input from crewai's ReAct agent
        if isinstance(waste_type, dict):
            d = waste_type
            waste_type   = d.get("waste_type", "Unknown")
            category     = d.get("category", "General Waste")
            urgency      = d.get("urgency", "Medium")
            location     = d.get("location", "Society Common Area")
            reported_by  = d.get("reported_by", "unknown")
            disposal_tip = d.get("disposal_tip", "")

        try:
            ticket_id = create_ticket(
                waste_type=waste_type,
                category=category,
                urgency=urgency,
                location=location,
                reported_by=reported_by,
                disposal_tip=disposal_tip,
            )
            return json.dumps({
                "ticket_id":   ticket_id,
                "assigned_to": "Cleaning Staff",
                "status":      "Open",
                "message":     f"✅ Ticket #{ticket_id} created and assigned to Cleaning Staff."
            })
        except Exception as e:
            return json.dumps({
                "ticket_id": 0,
                "error":     str(e),
                "message":   "❌ Ticket creation failed."
            })
