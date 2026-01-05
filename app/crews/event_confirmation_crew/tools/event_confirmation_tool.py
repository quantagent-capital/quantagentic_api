"""
Tool for confirming event locations based on coordinates.
"""
from typing import Type
from crewai.tools import BaseTool
from pydantic import BaseModel
from shapely.geometry import Point, Polygon
from app.schemas.location import Coordinate
from app.state import state
from app.schemas.event import Event
from app.crews.event_confirmation_crew.models import EventConfirmationOutput
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

	def _run(self, event_key: str, latitude: float, longitude: float) -> EventConfirmationOutput:
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
			EventConfirmationOutput with confirmed status and observed coordinate
		"""
		# Get the specific event
		event = state.get_event(event_key)
		if event is None:
			logger.warning(f"Event {event_key} not found")
			return EventConfirmationOutput(confirmed=False, observed_coordinate=None, location_index=None)
		
		# Validate coordinates - check for None or exactly (0.0, 0.0)
		if latitude is None or longitude is None or (latitude == 0.0 and longitude == 0.0):
			logger.info("Invalid coordinates provided (None or all zeros)")
			return EventConfirmationOutput(confirmed=False, observed_coordinate=None, location_index=None)
		
		# Validate coordinate ranges
		if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
			logger.warning(f"Coordinates out of valid range: lat={latitude}, lon={longitude}")
			return EventConfirmationOutput(confirmed=False, observed_coordinate=None, location_index=None)
		
		if longitude > 0:
			longitude = -longitude

		# Create point from coordinates
		point = Point(longitude, latitude)  # Shapely uses (lon, lat) order
		observed_coordinate = Coordinate(latitude=latitude, longitude=longitude)
		
		logger.info(f"Checking event {event_key} for coordinate ({latitude}, {longitude})")
		
		# Loop through all locations for this event
		for location_index, location in enumerate(event.locations):
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
					
					# Make polygon valid if it's invalid (handles self-intersections, etc.)
					if not polygon.is_valid:
						logger.info(f"Polygon invalid for event {event_key}, location {location.ugc_code}, attempting to fix")
						try:
							polygon = polygon.buffer(0)  # Common technique to fix invalid polygons
							if not polygon.is_valid:
								logger.warning(f"Polygon still invalid after buffer(0) for event {event_key}, location {location.ugc_code}")
						except Exception as buffer_error:
							logger.warning(f"Failed to fix invalid polygon with buffer(0): {str(buffer_error)}")
					
					# Debug logging for polygon bounds
					bounds = polygon.bounds  # (minx, miny, maxx, maxy)
					logger.info(f"Polygon bounds for {location.ugc_code}: lon=[{bounds[0]:.6f}, {bounds[2]:.6f}], lat=[{bounds[1]:.6f}, {bounds[3]:.6f}]")
					logger.info(f"Point: lon={longitude:.6f}, lat={latitude:.6f}")
					
					# Check if point intersects polygon (inside or on boundary)
					# Using intersects() which is more reliable than contains() for edge cases
					intersects = polygon.intersects(point)
					contains = polygon.contains(point)
					touches = polygon.touches(point)
					
					logger.info(f"Polygon checks - intersects: {intersects}, contains: {contains}, touches: {touches}")
					
					if intersects or contains or touches:
						logger.info(f"Coordinate ({latitude}, {longitude}) found in event {event.event_key}, location {location.ugc_code} at index {location_index}")
						return EventConfirmationOutput(confirmed=True, observed_coordinate=observed_coordinate, location_index=location_index)
				except Exception as e:
					logger.warning(f"Error creating polygon or checking containment for event {event.event_key}, location {location.ugc_code}: {str(e)}")
					logger.info(f"Polygon points: {polygon_points[:5]}... (showing first 5)")
					continue
		
		return EventConfirmationOutput(confirmed=False, observed_coordinate=None, location_index=None)
