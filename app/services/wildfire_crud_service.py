from datetime import datetime, timezone
from typing import Dict, Optional
from app.schemas.wildfire import Wildfire
from app.utils.arcgis_wildfire_parser import ArcGISWildfireParser
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
		
		# Parse all fields using parser
		event_key = ArcGISWildfireParser.parse_event_key(properties)
		arcgis_id = ArcGISWildfireParser.parse_arcgis_id(properties)
		start_date = ArcGISWildfireParser.parse_start_date(properties)
		last_modified = ArcGISWildfireParser.parse_last_modified(properties)
		location = ArcGISWildfireParser.parse_location(feature)
		acres_burned = ArcGISWildfireParser.parse_acres_burned(properties)
		severity = ArcGISWildfireParser.parse_severity(properties)
		cost = ArcGISWildfireParser.parse_cost(properties)
		description = ArcGISWildfireParser.parse_description(properties)
		fuel_source = ArcGISWildfireParser.parse_fuel_source(properties)
		percent_contained = ArcGISWildfireParser.parse_percent_contained(properties)
		
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
			cost=cost,
			description=description,
			fuel_source=fuel_source,
			active=active,
			percent_contained=percent_contained
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
		
		# Parse NEW values using parser
		last_modified = ArcGISWildfireParser.parse_last_modified(properties)
		acres_burned = ArcGISWildfireParser.parse_acres_burned(properties)
		severity = ArcGISWildfireParser.parse_severity(properties)
		cost = ArcGISWildfireParser.parse_cost(properties)
		description = ArcGISWildfireParser.parse_description(properties)
		fuel_source = ArcGISWildfireParser.parse_fuel_source(properties)
		percent_contained = ArcGISWildfireParser.parse_percent_contained(properties)
		
		# Parse location (will extract new shapes)
		parsed_location = ArcGISWildfireParser.parse_location(feature)
		
		# Create updated location (preserving existing fips and state_fips, but updating shape)
		from app.schemas.location import Location
		updated_location = Location(
			episode_key=existing_wildfire.location.episode_key,
			event_key=existing_wildfire.event_key,
			state_fips=existing_wildfire.location.state_fips,
			county_fips=existing_wildfire.location.county_fips,
			ugc_code=existing_wildfire.location.ugc_code,
			shape=parsed_location.shape,
			full_shape=parsed_location.full_shape,
			full_zone_ugc_endpoint=existing_wildfire.location.full_zone_ugc_endpoint,
			starting_point=existing_wildfire.location.starting_point
		)
		
		# Create updated wildfire (preserving existing values where specified)
		updated_wildfire = Wildfire(
			event_key=existing_wildfire.event_key,
			episode_key=existing_wildfire.episode_key,
			arcgis_id=existing_wildfire.arcgis_id,
			location=updated_location,
			acres_burned=acres_burned,
			severity=severity,
			start_date=existing_wildfire.start_date,
			last_modified=last_modified,
			end_date=existing_wildfire.end_date,
			cost=cost,
			description=description,
			fuel_source=fuel_source,
			active=existing_wildfire.active, # This gets updated downstream
			percent_contained=percent_contained
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
