from app.schemas.base import BaseSchema
from app.schemas.location import Coordinate

class County(BaseSchema):
	fips: str
	state_abbr: str
	state_fips: str
	name: str
	centroid: Coordinate