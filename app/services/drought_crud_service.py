from datetime import datetime, timezone
from typing import Dict
from app.schemas.drought import Drought
from app.schemas.location import Location
from app.schemas.counties import County
from app.state import state
import logging

logger = logging.getLogger(__name__)


class DroughtCRUDService:
	"""Service for drought event CRUD operations."""
	@staticmethod
	def create_drought(county: County, event_key: str, drought_data: Dict) -> Drought:
		"""
		Create a new drought event.
		
		Args:
			county: County object
			event_key: Event key for the drought event
			drought_data: Dictionary with 'severity', 'dm', and 'geometry' keys
		
		Returns:
			Created Drought object
		"""
		# Create location object
		location = Location(
			episode_key=None,
			event_key=event_key,
			state_fips=county.state_fips,
			county_fips=county.fips,
			ugc_code="",  # Not applicable for drought events - using empty string
			shape=[], # we let the FE draw it by county. We concede granularity for a simpler solution of tracking droughts.
			full_zone_ugc_endpoint=""  # Not applicable for drought events - using empty string
		)

		severity = drought_data['severity']
		drought = Drought(
			event_key=event_key,
			episode_key=None,
			start_date=datetime.now(timezone.utc),
			updated_at=datetime.now(timezone.utc),
			end_date=None,
			description=f"Drought event detected in {county.name}, {county.state_abbr}. Severity: {severity}",
			is_active=True,
			location=location,
			severity=severity
		)
		
		state.add_drought(drought)
		logger.info(f"Created drought event {event_key} for county {county.fips}")
		return drought

	@staticmethod
	def update_drought(existing_drought: Drought, new_severity: str) -> Drought:
		"""
		Update an existing drought event with new severity.
		
		Args:
			existing_drought: Existing Drought object
			new_severity: New severity level (D0-D4)
		
		Returns:
			Updated Drought object
		"""
		# Create updated drought
		updated_description = existing_drought.description or ""
		if updated_description:
			updated_description += f"\n\nDrought event continues. Updated severity: {new_severity} at {datetime.now(timezone.utc)}"
		else:
			updated_description = f"Drought event continues. Updated severity: {new_severity} at {datetime.now(timezone.utc)}"
		
		updated_drought = Drought(
			event_key=existing_drought.event_key,
			episode_key=existing_drought.episode_key,
			start_date=existing_drought.start_date,
			end_date=None,
			description=updated_description,
			is_active=True,
			location=existing_drought.location,
			severity=new_severity,
			updated_at=datetime.now(timezone.utc)
		)
		
		state.update_drought(updated_drought)
		logger.info(f"Updated drought event {existing_drought.event_key} with severity {new_severity}")
		return updated_drought

	@staticmethod
	def complete_drought(event_key: str) -> Drought:
		"""
		Complete a drought event by marking it as inactive and setting end_date.
		
		Args:
			event_key: Event key of the drought event to complete
		
		Returns:
			Completed Drought object, or None if event not found
		"""
		existing_drought = state.get_drought(event_key)
		if not existing_drought:
			logger.warning(f"Drought event {event_key} not found for completion")
			return None
		
		# Create completed drought
		completed_drought = Drought(
			event_key=existing_drought.event_key,
			episode_key=existing_drought.episode_key,
			start_date=existing_drought.start_date,
			end_date=datetime.now(timezone.utc),  # Set end time
			description=existing_drought.description,
			is_active=False,  # Mark as inactive
			location=existing_drought.location,
			severity=existing_drought.severity,
			updated_at=datetime.now(timezone.utc)
		)
		
		state.update_drought(completed_drought)
		logger.info(f"Completed drought event {event_key}")
		return completed_drought

