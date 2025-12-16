import logging
from typing import Optional, List
from app.schemas.base import BaseSchema

logger = logging.getLogger(__name__)

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
	shape: List[Coordinate]
	full_zone_ugc_endpoint: str

	@staticmethod
	def get_state_fips(state_abbr: str) -> str:
		"""
		Maps a 2-letter state abbreviation to its official 2-digit FIPS code.
		
		Args:
			state_abbr (str): The 2-letter state abbreviation (e.g., 'AL', 'ny').
			
		Returns:
			str: The 2-digit FIPS code (e.g., '01', '36'). Returns None if not found.
		"""
		
		# Official US Census Bureau FIPS codes
		# Note: Codes are strings to preserve leading zeros
		mapping = {
			'AL': '01', 'AK': '02', 'AZ': '04', 'AR': '05', 'CA': '06',
			'CO': '08', 'CT': '09', 'DE': '10', 'DC': '11', 'FL': '12',
			'GA': '13', 'HI': '15', 'ID': '16', 'IL': '17', 'IN': '18',
			'IA': '19', 'KS': '20', 'KY': '21', 'LA': '22', 'ME': '23',
			'MD': '24', 'MA': '25', 'MI': '26', 'MN': '27', 'MS': '28',
			'MO': '29', 'MT': '30', 'NE': '31', 'NV': '32', 'NH': '33',
			'NJ': '34', 'NM': '35', 'NY': '36', 'NC': '37', 'ND': '38',
			'OH': '39', 'OK': '40', 'OR': '41', 'PA': '42', 'RI': '44',
			'SC': '45', 'SD': '46', 'TN': '47', 'TX': '48', 'UT': '49',
			'VT': '50', 'VA': '51', 'WA': '53', 'WV': '54', 'WI': '55',
			'WY': '56', 'PR': '72'
		}
		
		# Normalize input to uppercase and strip whitespace
		clean_abbr = str(state_abbr).strip().upper()
		
		if clean_abbr not in mapping:
			logger.warning(f"Could not find state FIPS for state abbreviation: {state_abbr}. Returning UNKNOWN.")
			return "UNKNOWN"

		return mapping.get(clean_abbr)
