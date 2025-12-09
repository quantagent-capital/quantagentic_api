from datetime import datetime, timezone
from typing import Optional, List
from app.crews.utils.nws_event_types import NWS_WARNING_CODES
from app.exceptions import NotFoundError
from app.exceptions.base import ConflictError
from app.schemas.event import Event
from app.schemas.location import Location
from app.shared_models.nws_poller_models import FilteredNWSAlert
from app.state import state
from app.utils.datetime_utils import parse_datetime_to_utc
import logging

logger = logging.getLogger(__name__)


class EventService:
	"""Service layer for Event operations."""

	@staticmethod
	def create_event_from_alert(alert: FilteredNWSAlert) -> Event:
		"""
		Create an event from a FilteredNWSAlert.
		
		Args:
			alert: FilteredNWSAlert object
		
		Returns:
			Created Event object
		"""
		try:
			logger.info(f"Processing alert {alert.alert_id} with key {alert.key}")
			if state.event_exists(alert.key):
				raise ConflictError(f"Event with key: `{alert.key}` already exists, did we misclassify the alert?")
			event = Event(
				event_key=alert.key,
				nws_alert_id=alert.alert_id,
				episode_key=None,
				event_type=alert.event_type,
				hr_event_type=NWS_WARNING_CODES.get(alert.event_type, "UNKNOWN"),
				locations=alert.locations,
				start_date=parse_datetime_to_utc(alert.effective) or datetime.now(timezone.utc),
				expected_end_date=parse_datetime_to_utc(alert.expected_end),
				updated_at=datetime.now(timezone.utc),
				description=f"{alert.headline or ''}\n\n{alert.description or ''}",
				is_active=True,
				raw_vtec=alert.raw_vtec,
				previous_ids=[]
			)
			state.add_event(event)
			return event
		except ConflictError as e:
			# Re - raise as callers will handle logging for this case.
			raise
		except Exception as e:
			logger.error(f"Error processing alert {alert.alert_id}: {str(e)}")
			import traceback
			logger.error(traceback.format_exc())
			raise
	
	@staticmethod
	def update_event(event_key: str, event: Event) -> Optional[Event]:
		"""
		Update an existing event.
		
		Args:
			event_key: Key of event to update
			event: Updated event object
		
		Returns:
			Updated event or None if not found
		"""
		if not state.event_exists(event_key):
			raise ConflictError(f"Cannot update event with key: `{event_key}`, does not exist in state.")

		state.update_event(event)
		return event
	
	@staticmethod
	def get_event(event_key: str) -> Optional[Event]:
		"""
		Get an event by key.
		
		Args:
			event_key: Key of event to retrieve
		
		Returns:
			Event object or None if not found
		"""

		event = state.get_event(event_key)
		if event is None:
			raise NotFoundError("Event", event_key)
		return event
	
	@staticmethod
	def has_episode(event_key: str) -> bool:
		"""
		Check if an event has an associated episode.
		
		Args:
			event_key: Key of event to check
		
		Returns:
			True if event has an episode_key, False otherwise
		"""
		# TODO: Implement has_episode logic
		event = EventService.get_event(event_key)
		if event is None:
			return False
		return event.episode_key is not None
	
	@staticmethod
	def _merge_locations(existing_locations: List[Location], new_locations: List[Location]) -> List[Location]:
		"""
		Merge existing and new locations, avoiding duplicates based on ugc_code.
		
		Args:
			existing_locations: List of existing Location objects
			new_locations: List of new Location objects from updateable alert
		
		Returns:
			Combined list of locations with no duplicates
		"""
		# Get set of existing ugc_codes for quick lookup
		existing_ugc_codes = {loc.ugc_code for loc in existing_locations}
		
		# Start with existing locations
		merged_locations = list(existing_locations)
		
		# Add new locations that don't already exist
		for new_loc in new_locations:
			if new_loc.ugc_code not in existing_ugc_codes:
				merged_locations.append(new_loc)
				existing_ugc_codes.add(new_loc.ugc_code)  # Track to avoid duplicates within new_locations
		
		return merged_locations
	
	@staticmethod
	def update_event_from_alert(updateable_alert: FilteredNWSAlert) -> Event:
		"""
		Update an existing event from an updateable alert.
		
		Update logic:
		- If message_type is "COR" or "UPG": Replace entire event with updateable alert metadata
		- If message_type is "CAN" or "EXP": Mark event as inactive and set actual_end_date
		- Otherwise: Merge locations, update description, update expected_end_date
		
		Args:
			existing_event: Existing Event object to update
			updateable_alert: FilteredNWSAlert with update information
		
		Returns:
			Updated Event object
		"""
		try:
			existing_event = EventService.get_event(updateable_alert.key)
			logger.info(f"Updating event {existing_event.event_key} from alert {updateable_alert.alert_id} (message_type: {updateable_alert.message_type})")
			
			message_type = updateable_alert.message_type.upper()
			previous_ids = existing_event.previous_ids
			if existing_event.nws_alert_id not in previous_ids:
				previous_ids.append(existing_event.nws_alert_id)
			
			# Handle COR and UPG message types - replace entire event
			if message_type in ["COR", "UPG"]:
				logger.info(f"Message type {message_type} detected - replacing entire event")	
				updated_event = Event(
					event_key=updateable_alert.key,
					nws_alert_id=updateable_alert.alert_id,  # Always use new alert_id
					episode_key=existing_event.episode_key,  # Preserve episode_key
					event_type=updateable_alert.event_type,
					hr_event_type=NWS_WARNING_CODES.get(updateable_alert.event_type, "UNKNOWN"),
					locations=updateable_alert.locations,
					start_date=parse_datetime_to_utc(updateable_alert.effective) or existing_event.start_date,
					expected_end_date=parse_datetime_to_utc(updateable_alert.expected_end),
					actual_end_date=existing_event.actual_end_date,  # Preserve actual_end_date unless explicitly set
					updated_at=datetime.now(timezone.utc),
					description=f"{updateable_alert.headline or ''}\n\n{updateable_alert.description or ''}",
					is_active=existing_event.is_active,  # Preserve is_active status
					raw_vtec=updateable_alert.raw_vtec,
					property_damage=existing_event.property_damage,  # Preserve these fields
					crops_damage=existing_event.crops_damage,
					range_miles=existing_event.range_miles,
					previous_ids=previous_ids
				)
			
			# Handle CAN and EXP message types - mark as inactive
			elif message_type in ["CAN", "EXP"]:
				logger.info(f"Message type {message_type} detected - marking event as inactive")
				updated_event = Event(
					event_key=existing_event.event_key,
					nws_alert_id=updateable_alert.alert_id,  # Always use new alert_id
					episode_key=existing_event.episode_key,
					event_type=existing_event.event_type,
					hr_event_type=existing_event.hr_event_type,
					locations=existing_event.locations,  # Keep existing locations
					start_date=existing_event.start_date,
					expected_end_date=existing_event.expected_end_date,
					actual_end_date=parse_datetime_to_utc(updateable_alert.expected_end),
					updated_at=datetime.now(timezone.utc),
					description=existing_event.description,  # Keep existing description
					is_active=False,
					raw_vtec=existing_event.raw_vtec,
					property_damage=existing_event.property_damage,
					crops_damage=existing_event.crops_damage,
					range_miles=existing_event.range_miles,
					previous_ids=previous_ids
				)
			
			# Default update behavior - merge locations, update description and expected_end_date
			else:
				logger.info(f"Standard update for message type {message_type} - merging locations and updating fields")
				merged_locations = EventService._merge_locations(existing_event.locations, updateable_alert.locations)
				
				# Build description from alert
				new_description = f"{updateable_alert.headline or ''}\n\n{updateable_alert.description or ''}"
				updated_event = Event(
					event_key=existing_event.event_key,
					nws_alert_id=updateable_alert.alert_id,  # Always use new alert_id
					episode_key=existing_event.episode_key,
					event_type=existing_event.event_type,
					hr_event_type=existing_event.hr_event_type,
					locations=merged_locations,
					start_date=existing_event.start_date,  # Keep original start_date
					expected_end_date=parse_datetime_to_utc(updateable_alert.expected_end),
					actual_end_date=existing_event.actual_end_date,
					updated_at=datetime.now(timezone.utc),
					description=new_description,
					is_active=existing_event.is_active,
					raw_vtec=updateable_alert.raw_vtec,  # Update raw_vtec
					property_damage=existing_event.property_damage,
					crops_damage=existing_event.crops_damage,
					range_miles=existing_event.range_miles,
					previous_ids=previous_ids
				)
			
			# Update the event in state
			state.update_event(updated_event)
			logger.info(f"Successfully updated event {updated_event.event_key}")
			return updated_event
			
		except NotFoundError:
			# Re-raise NotFoundError as-is (callers will handle logging)
			raise
		except Exception as e:
			# Use alert key instead of existing_event.event_key in case get_event failed
			event_key = updateable_alert.key if 'existing_event' not in locals() else existing_event.event_key
			logger.error(f"Error updating event {event_key} from alert {updateable_alert.alert_id}: {str(e)}")
			import traceback
			logger.error(traceback.format_exc())
			raise

