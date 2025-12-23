"""
Tool for confirming event locations based on coordinates.
"""
from typing import List, Type, Dict, Any
from crewai.tools import BaseTool
from pydantic import BaseModel
from shapely.geometry import Point, Polygon
from app.schemas.location import Coordinate
from app.state import state
from app.schemas.event import Event
import logging

logger = logging.getLogger(__name__)

class ConfirmEventLocationInput(BaseModel):
	event_key: str
	latitude: float
	longitude: float

class ConfirmEventLocationTool(BaseTool):
	name: str = "ConfirmEventLocationTool"
	description: str = "Check if coordinates are contained within the event's polygons and collect observed coordinates."
	args_schema: Type[BaseModel] = ConfirmEventLocationInput

	def _run(self, event_key: str, latitude: float, longitude: float) -> Dict[str, Any]:
		"""
		Check if coordinates are contained within the event's polygons.
		
		This tool:
		1. Validates that coordinates are not all zeros or invalid
		2. Gets the specific event by event_key
		3. Loops through the event's location full_shapes
		4. Checks if the input coordinates are contained within any polygon
		5. If contained, adds the coordinate to observed_coordinates for that location
		6. If any coordinate is found, marks event as confirmed
		
		Args:
			event_key: The event key to check
			latitude: Latitude coordinate to check
			longitude: Longitude coordinate to check
			
		Returns:
			Dictionary with 'confirmed' (bool) and 'observed_locations' (List[Coordinate])
		"""
		# Get the specific event
		event = state.get_event(event_key)
		if event is None:
			logger.warning(f"Event {event_key} not found")
			return {"confirmed": False, "observed_locations": []}
		
		# Validate coordinates
		if not latitude or not longitude or (latitude == 0.0 and longitude == 0.0):
			logger.info("Invalid coordinates provided (all zeros or empty)")
			return {"confirmed": False, "observed_locations": []}
		
		# Create point from coordinates
		point = Point(longitude, latitude)  # Shapely uses (lon, lat) order
		observed_coordinate = Coordinate(latitude=latitude, longitude=longitude)
		
		logger.info(f"Checking event {event_key} for coordinate ({latitude}, {longitude})")
		
		# Loop through all locations for this event
		for location in event.locations:
			if not location.full_shape:
				continue
			
			# Loop through each polygon in full_shape
			for polygon_coords in location.full_shape:
				if not polygon_coords or len(polygon_coords) < 3:
					continue
				
				# Convert Coordinate list to shapely Polygon
				# Shapely expects (lon, lat) tuples
				polygon_points = [(coord.longitude, coord.latitude) for coord in polygon_coords]
				
				# Ensure polygon is closed (first point == last point)
				if polygon_points[0] != polygon_points[-1]:
					polygon_points.append(polygon_points[0])
				
				try:
					polygon = Polygon(polygon_points)
					
					# Check if point is contained in polygon
					if polygon.contains(point):
						logger.info(f"Coordinate ({latitude}, {longitude}) found in event {event.event_key}, location {location.ugc_code}")
						return {"confirmed": event.confirmed, "observed_coordinate": observed_coordinate}
				except Exception as e:
					logger.warning(f"Error creating polygon or checking containment for event {event.event_key}: {str(e)}")
					continue
		
		return {"confirmed": False, "observed_coordinate": None}
