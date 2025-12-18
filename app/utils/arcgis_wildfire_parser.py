"""
Parser for ArcGIS wildfire feature data.
"""
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from app.schemas.location import Location, Coordinate
from app.utils.datetime_utils import parse_timestamp_ms
import logging

logger = logging.getLogger(__name__)


class ArcGISWildfireParser:
	"""Parser for extracting and transforming ArcGIS wildfire feature data."""
	
	@staticmethod
	def map_severity(complexity_level: Optional[str]) -> int:
		"""
		Map incident complexity level to severity integer.
		
		Args:
			complexity_level: String like "Type 1 Incident", "Type 2 Incident", "Type 3 Incident"
		
		Returns:
			Integer severity (1, 2, or 3), defaults to 3 if unknown
		"""
		if not complexity_level:
			return 3
		
		complexity_level = complexity_level.strip().lower()
		if "type 1" in complexity_level:
			return 1
		elif "type 2" in complexity_level:
			return 2
		elif "type 3" in complexity_level:
			return 3
		else:
			logger.warning(f"Unknown complexity level: {complexity_level}, defaulting to 3")
			return 3
	
	@staticmethod
	def build_description(incident_name: Optional[str], incident_short_description: Optional[str]) -> Optional[str]:
		"""
		Build description from incident name and short description.
		
		Args:
			incident_name: Name of the incident
			incident_short_description: Short description of the incident
		
		Returns:
			Combined description string
		"""
		parts = []
		if incident_name:
			parts.append(incident_name)
		if incident_short_description:
			parts.append(incident_short_description)
		return " - ".join(parts) if parts else None
	
	@staticmethod
	def build_fuel_source(primary_fuel: Optional[str], secondary_fuel: Optional[str]) -> Optional[str]:
		"""
		Build fuel source from primary and secondary fuel models.
		
		Args:
			primary_fuel: Primary fuel model
			secondary_fuel: Secondary fuel model
		
		Returns:
			Combined fuel source string
		"""
		parts = []
		if primary_fuel:
			parts.append(primary_fuel)
		if secondary_fuel:
			parts.append(secondary_fuel)
		return " / ".join(parts) if parts else None
	
	@staticmethod
	def parse_event_key(properties: Dict[str, Any]) -> str:
		"""
		Extract event key from feature properties.
		
		Args:
			properties: Feature properties dictionary
		
		Returns:
			Event key string
		"""
		return properties.get("attr_UniqueFireIdentifier", "")
	
	@staticmethod
	def parse_arcgis_id(properties: Dict[str, Any]) -> str:
		"""
		Extract ArcGIS ID from feature properties.
		
		Args:
			properties: Feature properties dictionary
		
		Returns:
			ArcGIS ID as string
		"""
		return str(properties.get("OBJECTID", ""))
	
	@staticmethod
	def parse_start_date(properties: Dict[str, Any]) -> datetime:
		"""
		Parse start date from feature properties.
		
		Args:
			properties: Feature properties dictionary
		
		Returns:
			Start date datetime in UTC, or current time if not available
		"""
		discovery_timestamp_ms = properties.get("attr_FireDiscoveryDateTime")
		return parse_timestamp_ms(discovery_timestamp_ms) or datetime.now(timezone.utc)
	
	@staticmethod
	def parse_last_modified(properties: Dict[str, Any]) -> datetime:
		"""
		Parse last modified timestamp from feature properties.
		
		Args:
			properties: Feature properties dictionary
		
		Returns:
			Last modified datetime in UTC, or current time if not available
		"""
		modified_timestamp_ms = properties.get("attr_ModifiedOnDateTime_dt")
		return parse_timestamp_ms(modified_timestamp_ms) or datetime.now(timezone.utc)
	
	@staticmethod
	def parse_location(feature: Dict[str, Any]) -> Location:
		"""
		Parse location data from ArcGIS feature.
		
		Args:
			feature: Complete GeoJSON feature dictionary
		
		Returns:
			Location object with parsed data
		"""
		properties = feature.get("properties", {})
		geometry = feature.get("geometry", {})
		
		# Parse FIPS
		full_fips = properties.get("attr_POOFips")
		state_fips, county_fips = Location.parse_fips(full_fips)
		
		# Extract location data
		initial_lat = properties.get("attr_InitialLatitude")
		initial_lon = properties.get("attr_InitialLongitude")
		starting_point = Coordinate(
			latitude=initial_lat if initial_lat is not None else 0.0,
			longitude=initial_lon if initial_lon is not None else 0.0
		)
		
		# Extract shape coordinates
		full_shape = Location.extract_all_shapes(geometry)
		# Also extract single shape for backward compatibility
		shape = Location.extract_coordinates_from_geometry(geometry)
		
		event_key = ArcGISWildfireParser.parse_event_key(properties)
		
		# Create location
		return Location(
			episode_key=None,
			event_key=event_key,
			state_fips=state_fips,
			county_fips=county_fips,
			ugc_code="",  # Not applicable for wildfires
			shape=shape,
			full_shape=full_shape,
			full_zone_ugc_endpoint="",  # Not applicable for wildfires
			starting_point=starting_point
		)
	
	@staticmethod
	def parse_acres_burned(properties: Dict[str, Any]) -> int:
		"""
		Parse acres burned from feature properties.
		
		Args:
			properties: Feature properties dictionary
		
		Returns:
			Acres burned as integer, defaults to 0
		"""
		return int(properties.get("poly_GISAcres", 0) or 0)
	
	@staticmethod
	def parse_severity(properties: Dict[str, Any]) -> int:
		"""
		Parse severity from feature properties.
		
		Args:
			properties: Feature properties dictionary
		
		Returns:
			Severity integer (1, 2, or 3)
		"""
		complexity_level = properties.get("attr_IncidentComplexityLevel")
		return ArcGISWildfireParser.map_severity(complexity_level)
	
	@staticmethod
	def parse_cost(properties: Dict[str, Any]) -> Optional[int]:
		"""
		Parse cost from feature properties.
		
		Args:
			properties: Feature properties dictionary
		
		Returns:
			Cost as integer, or None if not available
		"""
		cost = properties.get("attr_EstimatedFinalCost")
		return int(cost) if cost is not None else None
	
	@staticmethod
	def parse_description(properties: Dict[str, Any]) -> Optional[str]:
		"""
		Parse description from feature properties.
		
		Args:
			properties: Feature properties dictionary
		
		Returns:
			Combined description string, or None
		"""
		return ArcGISWildfireParser.build_description(
			properties.get("attr_IncidentName"),
			properties.get("attr_IncidentShortDescription")
		)
	
	@staticmethod
	def parse_fuel_source(properties: Dict[str, Any]) -> Optional[str]:
		"""
		Parse fuel source from feature properties.
		
		Args:
			properties: Feature properties dictionary
		
		Returns:
			Combined fuel source string, or None
		"""
		return ArcGISWildfireParser.build_fuel_source(
			properties.get("attr_PrimaryFuelModel"),
			properties.get("attr_SecondaryFuelModel")
		)
	
	@staticmethod
	def parse_percent_contained(properties: Dict[str, Any]) -> Optional[int]:
		"""
		Parse percent contained from feature properties.
		
		Args:
			properties: Feature properties dictionary
		
		Returns:
			Percent contained as integer, or None if not available
		"""
		percent_contained = properties.get("attr_PercentContained")
		return int(percent_contained) if percent_contained is not None else None
