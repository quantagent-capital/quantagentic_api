"""
Utilities for polygon overlap detection using Shapely.
"""
from typing import List, Tuple, Optional
from shapely.geometry import Polygon, Point
from shapely import intersection


def parse_polygon_from_coordinates(coordinates: List) -> Optional[Polygon]:
	"""
	Parse polygon from NWS coordinate format.
	
	Args:
		coordinates: NWS coordinate array (nested lists)
		
	Returns:
		Shapely Polygon object or None if invalid
	"""
	try:
		# NWS coordinates format: [[[lon, lat], [lon, lat], ...]]
		# Flatten if needed
		if len(coordinates) > 0 and isinstance(coordinates[0][0], list):
			# Nested format
			coords = coordinates[0]
		else:
			coords = coordinates
		
		# Extract (lon, lat) pairs
		points = []
		for coord in coords:
			if len(coord) >= 2:
				lon, lat = float(coord[0]), float(coord[1])
				points.append((lon, lat))
		
		if len(points) < 3:
			return None
		
		# Create polygon (close if not already closed)
		if points[0] != points[-1]:
			points.append(points[0])
		
		return Polygon(points)
		
	except Exception as e:
		return None


def parse_polygon_from_string(polygon_str: str) -> Optional[Polygon]:
	"""
	Parse polygon from string format (stored in Location.shape).
	
	Args:
		polygon_str: Polygon string in format "POLYGON((lon lat, lon lat, ...))"
		
	Returns:
		Shapely Polygon object or None if invalid
	"""
	try:
		# Parse WKT format: POLYGON((lon lat, lon lat, ...))
		if polygon_str.startswith("POLYGON"):
			# Extract coordinates
			coords_str = polygon_str.replace("POLYGON((", "").replace("))", "")
			points = []
			for coord_pair in coords_str.split(","):
				parts = coord_pair.strip().split()
				if len(parts) >= 2:
					lon, lat = float(parts[0]), float(parts[1])
					points.append((lon, lat))
			
			if len(points) >= 3:
				return Polygon(points)
		
		return None
		
	except Exception as e:
		return None


def polygons_overlap(polygon1: Polygon, polygon2: Polygon) -> bool:
	"""
	Check if two polygons overlap.
	
	Args:
		polygon1: First polygon
		polygon2: Second polygon
		
	Returns:
		True if polygons overlap, False otherwise
	"""
	try:
		if polygon1 is None or polygon2 is None:
			return False
		
		# Check if polygons intersect
		return polygon1.intersects(polygon2)
		
	except Exception:
		return False


def check_event_episode_overlap(
	event_polygon_coords: List,
	episode_locations: List[dict]
) -> bool:
	"""
	Check if an event polygon overlaps with any episode location.
	
	Args:
		event_polygon_coords: Event polygon coordinates from NWS
		episode_locations: List of episode location dicts with 'shape' field
		
	Returns:
		True if overlap found, False otherwise
	"""
	try:
		event_polygon = parse_polygon_from_coordinates(event_polygon_coords)
		if event_polygon is None:
			return False
		
		# Check against each episode location
		for location in episode_locations:
			shape_str = location.get("shape", "")
			if shape_str:
				episode_polygon = parse_polygon_from_string(shape_str)
				if episode_polygon and polygons_overlap(event_polygon, episode_polygon):
					return True
		
		return False
		
	except Exception:
		return False

