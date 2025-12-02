from typing import Optional
from app.schemas.base import BaseSchema

class Location(BaseSchema):
	episode_id: int
	event_key: str
	state_fips: str
	county_fips: str
	ugc_code: str
	shape: str  # polygon string

