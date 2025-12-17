from datetime import datetime, timezone
from typing import Dict, Optional
from app.schemas.wildfire import Wildfire
from app.schemas.location import Location, Coordinate
from app.utils.datetime_utils import parse_timestamp_ms
from app.utils.wildfire_utils import WildfireUtils
from app.state import state
import logging

logger = logging.getLogger(__name__)


class WildfireCRUDService:
	"""Service for wildfire event CRUD operations."""
	@staticmethod
	def create_wildfire(feature: Dict[str, any]) -> Wildfire:
		"""
		Create a new wildfire event from an ArcGIS feature.
		
		Args:
			feature: GeoJSON feature from ArcGIS API
		
		Returns:
			Created Wildfire object
		"""
		properties = feature.get("properties", {})
		geometry = feature.get("geometry", {})
		
		# Extract and parse fields
		event_key = properties.get("attr_UniqueFireIdentifier", "")
		arcgis_id = str(properties.get("OBJECTID", ""))
		
		# Parse timestamps
		discovery_timestamp_ms = properties.get("attr_FireDiscoveryDateTime")
		start_date = parse_timestamp_ms(discovery_timestamp_ms) or datetime.now(timezone.utc)
		
		modified_timestamp_ms = properties.get("attr_ModifiedOnDateTime_dt")
		last_modified = parse_timestamp_ms(modified_timestamp_ms) or datetime.now(timezone.utc)
		
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
		shape = Location.extract_coordinates_from_geometry_for_wildfire(geometry)
		
		# Create location
		location = Location(
			episode_key=None,
			event_key=event_key,
			state_fips=state_fips,
			county_fips=county_fips,
			ugc_code="",  # Not applicable for wildfires
			shape=shape,
			full_zone_ugc_endpoint="",  # Not applicable for wildfires
			starting_point=starting_point
		)
		
		# Extract other fields
		acres_burned = int(properties.get("poly_GISAcres", 0) or 0)
		severity = WildfireUtils.map_severity(properties.get("attr_IncidentComplexityLevel"))
		cost = properties.get("attr_EstimatedFinalCost")
		cost_int = int(cost) if cost is not None else None
		
		description = WildfireUtils.build_description(
			properties.get("attr_IncidentName"),
			properties.get("attr_IncidentShortDescription")
		)
		
		fuel_source = WildfireUtils.build_fuel_source(
			properties.get("attr_PrimaryFuelModel"),
			properties.get("attr_SecondaryFuelModel")
		)
		
		percent_contained = properties.get("attr_PercentContained")
		percent_contained_int = int(percent_contained) if percent_contained is not None else None
		
		# Determine active status based on the 3-tiered logic
		# The lifecycle of the wildfire is managed in the completion layer based on API response
		# For this stack, we query the API directly for active wildfires
		active = True
		
		wildfire = Wildfire(
			event_key=event_key,
			episode_key=None,
			arcgis_id=arcgis_id,
			location=location,
			acres_burned=acres_burned,
			severity=severity,
			start_date=start_date,
			last_modified=last_modified,
			end_date=None,
			cost=cost_int,
			description=description,
			fuel_source=fuel_source,
			active=active,
			percent_contained=percent_contained_int
		)
		
		state.add_wildfire(wildfire)
		return wildfire

	@staticmethod
	def update_wildfire(existing_wildfire: Wildfire, feature: Dict[str, any]) -> Wildfire:
		"""
		Update an existing wildfire event from an ArcGIS feature.
		
		Uses NEW VALUES for: severity, cost, acres_burned, fuel_source, description, location.shape
		Uses EXISTING VALUES for: event_key, start_date, arcgis_id, location.starting_point, location.fips, location.state_fips
		
		Args:
			existing_wildfire: Existing Wildfire object
			feature: GeoJSON feature from ArcGIS API
		
		Returns:
			Updated Wildfire object
		"""
		properties = feature.get("properties", {})
		geometry = feature.get("geometry", {})
		
		# Parse timestamps
		modified_timestamp_ms = properties.get("attr_ModifiedOnDateTime_dt")
		last_modified = parse_timestamp_ms(modified_timestamp_ms) or datetime.now(timezone.utc)
		
		# Extract NEW values
		acres_burned = int(properties.get("poly_GISAcres", 0) or 0)
		severity = WildfireUtils.map_severity(properties.get("attr_IncidentComplexityLevel"))
		cost = properties.get("attr_EstimatedFinalCost")
		cost_int = int(cost) if cost is not None else None
		
		description = WildfireUtils.build_description(
			properties.get("attr_IncidentName"),
			properties.get("attr_IncidentShortDescription")
		)
		
		fuel_source = WildfireUtils.build_fuel_source(
			properties.get("attr_PrimaryFuelModel"),
			properties.get("attr_SecondaryFuelModel")
		)
		
		percent_contained = properties.get("attr_PercentContained")
		percent_contained_int = int(percent_contained) if percent_contained is not None else None
		
		# Extract NEW shape coordinates
		shape = Location.extract_coordinates_from_geometry(geometry)
		
		# Create updated location (preserving existing fips and state_fips, but updating shape)
		updated_location = Location(
			episode_key=existing_wildfire.location.episode_key,
			event_key=existing_wildfire.event_key,
			state_fips=existing_wildfire.location.state_fips,  # KEEP EXISTING
			county_fips=existing_wildfire.location.county_fips,  # KEEP EXISTING
			ugc_code=existing_wildfire.location.ugc_code,
			shape=shape,  # NEW VALUE
			full_zone_ugc_endpoint=existing_wildfire.location.full_zone_ugc_endpoint,
			starting_point=existing_wildfire.location.starting_point  # KEEP EXISTING
		)
		
		# Create updated wildfire (preserving existing values where specified)
		updated_wildfire = Wildfire(
			event_key=existing_wildfire.event_key,  # KEEP EXISTING
			episode_key=existing_wildfire.episode_key,
			arcgis_id=existing_wildfire.arcgis_id,  # KEEP EXISTING
			location=updated_location,
			acres_burned=acres_burned,  # NEW VALUE
			severity=severity,  # NEW VALUE
			start_date=existing_wildfire.start_date,  # KEEP EXISTING
			last_modified=last_modified,  # NEW VALUE
			end_date=existing_wildfire.end_date,
			cost=cost_int,  # NEW VALUE
			description=description,  # NEW VALUE
			fuel_source=fuel_source,  # NEW VALUE
			active=existing_wildfire.active,  # Will be updated by service layer
			percent_contained=percent_contained_int  # NEW VALUE
		)
		
		state.update_wildfire(updated_wildfire)
		return updated_wildfire
	
	@staticmethod
	def complete_wildfire(event_key: str) -> Optional[Wildfire]:
		"""
		Complete a wildfire event by marking it as inactive and setting end_date.
		
		Args:
			event_key: Event key of the wildfire event to complete
		
		Returns:
			Completed Wildfire object, or None if event not found
		"""
		existing_wildfire = state.get_wildfire(event_key)
		if not existing_wildfire:
			logger.warning(f"Wildfire event {event_key} not found for completion")
			return None
		
		completed_wildfire = Wildfire(
			event_key=existing_wildfire.event_key,
			episode_key=existing_wildfire.episode_key,
			arcgis_id=existing_wildfire.arcgis_id,
			location=existing_wildfire.location,
			acres_burned=existing_wildfire.acres_burned,
			severity=existing_wildfire.severity,
			start_date=existing_wildfire.start_date,
			last_modified=datetime.now(timezone.utc),
			end_date=datetime.now(timezone.utc),  # Set end time
			cost=existing_wildfire.cost,
			description=existing_wildfire.description,
			fuel_source=existing_wildfire.fuel_source,
			active=False,  # Mark as inactive
			percent_contained=existing_wildfire.percent_contained
		)
		
		state.update_wildfire(completed_wildfire)
		return completed_wildfire
