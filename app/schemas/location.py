from typing import Optional, List
from app.schemas.base import BaseSchema

class Coordinate(BaseSchema):
	"""Coordinate with latitude and longitude."""
	latitude: float
	longitude: float

class Location(BaseSchema):
	episode_key: Optional[str] = None  # Can be None if event is not part of an episode
	event_key: str
	state_fips: str
	county_fips: str
	ugc_code: str
	shape: List[Coordinate]  # Changed from str to List[Coordinate]
	full_zone_ugc_endpoint: str
