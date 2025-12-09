"""
Structured Pydantic output models for event profile crew.
"""
from pydantic import BaseModel, Field
from app.schemas.event import Event
from app.schemas.location import Location

class VerifiedEventModel(BaseModel):
	"""Structured output from the ensure_event_model_is_sound task."""
	event: Event = Field(description="The final, definitive Event model")

class ConstructedEventModel(BaseModel):
	"""Structured output from the construct_event_model task."""
	event: Event = Field(description="The initially constructed Event model")

class HumanReadableEvent(BaseModel):
	"""Human-readable name for the event type."""
	event_name: str = Field(description="The human-readable event name")
	event_code: str = Field(description="The abbreviated event code")

class Locations(BaseModel):
	"""List of locations for the event."""
	locations: list[Location] = Field(description="The list of Location objects for the event")
