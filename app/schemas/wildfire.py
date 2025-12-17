from typing import Optional
from datetime import datetime
from app.schemas.base import BaseSchema
from app.schemas.location import Location

class Wildfire(BaseSchema):
	"""
	Wildfire event model for tracking wildfire incidents.
	
	Data Freshness Note:
	--------------------
	If you query the API at Noon on Tuesday, you are usually looking at exactly 
	where the fire was at Midnight on Monday.
	"""
	event_key: str
	episode_key: Optional[str] = None
	arcgis_id: str
	location: Location
	acres_burned: int
	severity: int  # Type 1 (worst), 2, or 3 Incident (mapped to 1, 2, 3)
	start_date: datetime
	last_modified: datetime
	end_date: Optional[datetime] = None
	cost: Optional[int] = None
	description: Optional[str] = None
	fuel_source: Optional[str] = None
	active: bool
	percent_contained: Optional[int] = None
