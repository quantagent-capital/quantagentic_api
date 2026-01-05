import logging
from typing import Optional, List, Dict, Any
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
	shape: Optional[List[Coordinate]] = None # Deprecated
	full_shape: Optional[List[List[Coordinate]]] = None
	full_zone_ugc_endpoint: str
	starting_point: Optional[Coordinate] = None  # Optional starting point (e.g., for wildfires)
	observed_coordinate: Optional[Coordinate] = None  # Observed coordinate from LSR that is within proximity of the full shape

	@staticmethod
	def parse_fips(full_fips: Optional[str]) -> tuple[str, str]:
		"""
		Parse full FIPS code (e.g., "01012") into state_fips and county_fips.
		
		Args:
			full_fips: Full FIPS code (first 2 digits are state, rest is county)
		
		Returns:
			Tuple of (state_fips, county_fips)
		"""
		if not full_fips or len(full_fips) < 2:
			return ("UNKNOWN", "UNKNOWN")
		
		state_fips = full_fips[:2]
		county_fips = full_fips[2:] if len(full_fips) > 2 else "UNKNOWN"
		return (state_fips, county_fips)

	@staticmethod
	def extract_coordinates_from_geometry(geometry: Dict[str, Any]) -> List[Coordinate]:
		"""
		Extract coordinates from a geometry object (Polygon or MultiPolygon).
		For MultiPolygon, we take the outermost perimeter (first polygon's first ring).
		
		Args:
			geometry: Geometry object with type and coordinates
		
		Returns:
			List of Coordinate objects extracted from the geometry
		"""
		shape = []
		geom_type = geometry.get("type")
		coordinates_raw = geometry.get("coordinates", [])
		
		if not coordinates_raw:
			return shape
		
		if geom_type == "Polygon":
			# Polygon structure: [[[lon, lat], [lon, lat], ...]]
			# We take the first ring (exterior boundary)
			if len(coordinates_raw) > 0:
				polygon_ring = coordinates_raw[0]
				for coord_pair in polygon_ring:
					if len(coord_pair) >= 2:
						lon, lat = coord_pair[0], coord_pair[1]
						shape.append(Coordinate(latitude=lat, longitude=lon))
		
		elif geom_type == "MultiPolygon":
			# MultiPolygon structure: [[[[lon, lat], ...], ...], ...]
			# We take the first polygon's first ring (exterior boundary of first polygon)
			if len(coordinates_raw) > 0:
				first_polygon = coordinates_raw[0]
				if len(first_polygon) > 0:
					polygon_ring = first_polygon[0]
					for coord_pair in polygon_ring:
						if len(coord_pair) >= 2:
							lon, lat = coord_pair[0], coord_pair[1]
							shape.append(Coordinate(latitude=lat, longitude=lon))
		
		return shape

	@staticmethod
	def extract_all_shapes(geometry: Dict[str, Any]) -> List[List[Coordinate]]:
		"""
		Extracts ALL separate polygons from the geometry.
		Returns a List of Lists of Coordinates.
		"""
		all_shapes = []
		
		geom_type = geometry.get("type")
		coordinates_raw = geometry.get("coordinates", [])
		
		if not coordinates_raw:
			return all_shapes
			
		# --- HELPER ---
		def parse_ring(ring):
			coords = []
			for coord_pair in ring:
				if len(coord_pair) >= 2:
					coords.append(Coordinate(latitude=coord_pair[1], longitude=coord_pair[0]))
			return coords

		if geom_type == "Polygon":
			# Structure: [ [Exterior], [Hole], [Hole] ]
			# We treat the exterior ring as the first shape
			if len(coordinates_raw) > 0:
				exterior_ring = parse_ring(coordinates_raw[0])
				all_shapes.append(exterior_ring)
		
		elif geom_type == "MultiPolygon":
			# Structure: [ [[Exterior], [Hole]], [[Exterior], [Hole]] ]
			for polygon in coordinates_raw:
				if len(polygon) > 0:
					exterior_ring = parse_ring(polygon[0])
					all_shapes.append(exterior_ring)
					
		return all_shapes

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
