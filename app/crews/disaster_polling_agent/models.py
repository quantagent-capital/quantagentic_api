"""
Structured Pydantic output models for disaster polling tasks.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class FilteredNWSAlert(BaseModel):
	"""Single filtered NWS alert from polling."""
	alert_id: str = Field(description="Unique alert identifier")
	event_type: str = Field(description="Event type code (e.g., TOR, SVR)")
	message_type: str = Field(description="Message type (WARNING or WATCH)")
	severity: str = Field(description="Alert severity")
	urgency: str = Field(description="Alert urgency")
	certainty: str = Field(description="Alert certainty")
	effective: str = Field(description="Effective datetime")
	expires: Optional[str] = Field(default=None, description="Expiration datetime")
	headline: Optional[str] = Field(default=None, description="Alert headline")
	description: Optional[str] = Field(default=None, description="Alert description")
	raw_data: Dict[str, Any] = Field(description="Full alert properties")


class PolledNWSAlertsOutput(BaseModel):
	"""Structured output from NWS polling task."""
	filtered_alerts: List[FilteredNWSAlert] = Field(
		description="List of filtered NWS alerts that meet severity/urgency/certainty criteria"
	)
	total_count: int = Field(description="Total number of filtered alerts")
	poll_timestamp: str = Field(description="Timestamp when polling occurred")


class VTECKeyInfo(BaseModel):
	"""VTEC key information for a single alert."""
	alert_id: str = Field(description="Alert identifier")
	vtec_key: str = Field(description="VTEC key in format: Office + Phenomena + Significance + ETN + Year")
	office: Optional[str] = Field(default=None, description="NWS office code")
	phenomena: Optional[str] = Field(default=None, description="Phenomena code")
	significance: Optional[str] = Field(default=None, description="Significance code (W=Warning, A=Watch)")
	etn: Optional[str] = Field(default=None, description="Event Tracking Number")
	year: Optional[str] = Field(default=None, description="Year (2-digit)")


class VTECKeysOutput(BaseModel):
	"""Structured output from VTEC key creation task."""
	vtec_keys: List[VTECKeyInfo] = Field(
		description="List of VTEC keys created for each alert"
	)
	total_keys: int = Field(description="Total number of VTEC keys created")
	validation_status: str = Field(description="Overall validation status")


class VerifiedVTECKey(BaseModel):
	"""Verified VTEC key with validation status."""
	alert_id: str = Field(description="Alert identifier")
	vtec_key: str = Field(description="VTEC key")
	is_valid: bool = Field(description="Whether the key is valid")
	validation_errors: List[str] = Field(default_factory=list, description="List of validation errors if any")
	key_pattern: str = Field(description="Expected pattern: Office + Phenomena + Significance + ETN + Year")


class VerifiedVTECKeysOutput(BaseModel):
	"""Structured output from VTEC key verification task."""
	verified_keys: List[VerifiedVTECKey] = Field(
		description="List of verified VTEC keys with validation status"
	)
	total_verified: int = Field(description="Total number of verified keys")
	valid_count: int = Field(description="Number of valid keys")
	invalid_count: int = Field(description="Number of invalid keys")
	all_valid: bool = Field(description="Whether all keys are valid")


class ClassifiedAlert(BaseModel):
	"""Single classified alert."""
	alert_id: str = Field(description="Alert identifier")
	vtec_key: str = Field(description="VTEC key")
	message_type: str = Field(description="Message type from VTEC (NEW, CON, CANCEL, EXP)")
	classification: str = Field(description="Classification: new_event, updated_event, new_episode, or updated_episode")
	event_type: str = Field(description="Event type code")
	overlaps_with_episode: Optional[bool] = Field(default=None, description="Whether alert overlaps with existing episode")
	associated_episode_key: Optional[str] = Field(default=None, description="Associated episode key if linked")


class ClassifiedAlertsOutput(BaseModel):
	"""Structured output from alert classification task."""
	new_events: List[ClassifiedAlert] = Field(
		description="List of new events (warnings) that need to be created"
	)
	updated_events: List[ClassifiedAlert] = Field(
		description="List of existing events (warnings) that need to be updated"
	)
	new_episodes: List[ClassifiedAlert] = Field(
		description="List of new episodes (watches) that need to be created"
	)
	updated_episodes: List[ClassifiedAlert] = Field(
		description="List of existing episodes (watches) that need to be updated"
	)
	total_classified: int = Field(description="Total number of classified alerts")

