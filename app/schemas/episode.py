from typing import Optional, List
from datetime import datetime
from app.schemas.base import BaseSchema
from app.schemas.location import Location

class Episode(BaseSchema):
	episode_id: int
	start_date: datetime
	end_date: Optional[datetime] = None
	total_damage: Optional[int] = None
	total_hurt: Optional[int] = None
	total_range_miles: Optional[int] = None
	included_event_types: str
	watch_description: str
	area_description: str
	locations: List[Location] = []
	is_active: bool = True

