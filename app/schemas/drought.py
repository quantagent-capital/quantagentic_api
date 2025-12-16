from typing import Optional
from datetime import datetime
from app.schemas.base import BaseSchema
from app.schemas.location import Location

class Drought(BaseSchema):
	"""Drought event model for tracking drought conditions."""
	event_key: str
	episode_key: Optional[str] = None
	start_date: datetime
	end_date: Optional[datetime] = None
	updated_at: Optional[datetime] = None
	description: Optional[str] = None
	is_active: bool
	location: Location
	severity: str  # D2-D4 severity level

