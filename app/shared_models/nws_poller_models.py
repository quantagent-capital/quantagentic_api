"""
Structured Pydantic output models for disaster polling tasks.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from app.schemas.location import Location


class FilteredNWSAlert(BaseModel):
	"""Single filtered NWS alert from polling."""
	alert_id: str = Field(description="Unique alert identifier from the NWS")
	key: str = Field(description="VTEC key in format: Office + Phenomena + Significance + ETN + Year")
	is_watch: bool = Field(description="Whether the alert is a watch")
	is_warning: bool = Field(description="Whether the alert is a warning")
	event_type: str = Field(description="Event type code (e.g., TOR, SVR)")
	message_type: str = Field(description="NEW, CON, CANCEL, EXP, UPDATE")
	severity: str = Field(description="Alert severity")
	urgency: str = Field(description="Alert urgency")
	certainty: str = Field(description="Alert certainty")
	effective: str = Field(description="Effective datetime")
	affected_zones_ugc_endpoints: List[str] = Field(description="List of UGC endpoints for the affected zones")
	affected_zones_raw_ugc_codes: List[str] = Field(description="List of raw UGC codes for the affected zones")
	referenced_alerts: List[dict] = Field(description="List of referenced alert IDs")
	expires: Optional[str] = Field(default=None, description="Expiration datetime")
	expected_end: Optional[str] = Field(default=None, description="Expected end datetime") 
	headline: Optional[str] = Field(default=None, description="Alert headline")
	description: Optional[str] = Field(default=None, description="Alert description")
	raw_vtec: str = Field(description="Raw VTEC string from the alert")
	locations: List[Location] = Field(default_factory=list, description="List of location geometries extracted from the alert feature, one per SAME code")

class ClassifiedAlertsOutput(BaseModel):
	"""Structured output from alert classification task."""
	new_events: List[FilteredNWSAlert] = Field(
		description="List of new events (warnings) that need to be created"
	)
	updated_events: List[FilteredNWSAlert] = Field(
		description="List of existing events (warnings) that need to be updated"
	)
	total_classified: int = Field(description="Total number of classified alerts")
	
