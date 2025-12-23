"""
Structured output models for event confirmation crew tasks.
"""
from typing import List, Optional
from pydantic import BaseModel, Field
from app.schemas.location import Coordinate


class CoordinateExtractionOutput(BaseModel):
	"""Structured output for coordinate extraction task."""
	latitude: float = Field(description="Latitude coordinate extracted from description. Use 0.0 if not found.")
	longitude: float = Field(description="Longitude coordinate extracted from description. Use 0.0 if not found.")


class EventConfirmationOutput(BaseModel):
	"""Structured output for event confirmation task."""
	confirmed: bool = Field(description="Whether the event was confirmed.")
	observed_coordinate: Optional[Coordinate] = Field(description="Observed coordinate from LSR that is within proximity of the event's polygons.", default=None)
