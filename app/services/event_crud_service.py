from typing import List, Dict
from datetime import datetime, timezone
from app.schemas.event import Event
from app.state import state
import logging

logger = logging.getLogger(__name__)


class EventCRUDService:
	"""Service for Event CRUD operations."""

	@staticmethod
	def get_event(event_key: str) -> Event:
		"""
		Get an event by key.
		
		Args:
			event_key: Key of event to retrieve
		
		Returns:
			Event object
		
		Raises:
			NotFoundError: If event is not found
		"""
		event = state.get_event(event_key)
		if event is None:
			from app.exceptions import NotFoundError
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
		try:
			event = EventCRUDService.get_event(event_key)
			return event.episode_key is not None
		except Exception:
			return False
	
	@staticmethod
	def get_events(active_only: bool = True) -> List[Event]:
		"""
		Get events from state, optionally filtered by active_only.
		
		Filtering logic:
		- If active_only is True, return only events from state.active_events
		- Otherwise, return all events from state.events
		
		Args:
			active_only: If true, return only events from state.active_events. Default is True.
		
		Returns:
			List of Event objects matching the filter criteria
		"""
		# If active_only is True, use active_events; otherwise use all events
		return state.active_events if active_only else state.events
	
	@staticmethod
	def get_active_event_counts_by_type() -> Dict[str, int]:
		"""
		Get count of active events grouped by event type.
		
		Returns:
			Dictionary mapping event_type to count of active events
		"""
		active_events = state.active_events
		counts: Dict[str, int] = {}
		
		for event in active_events:
			event_type = event.event_type
			counts[event_type] = counts.get(event_type, 0) + 1
		
		return counts

	@staticmethod
	def deactivate_event(event_key: str) -> Event:
		"""
		Deactivate an event by setting is_active=False and actual_end_date to current time.
		
		Args:
			event_key: Key of event to deactivate
		
		Returns:
			Deactivated Event object
		
		Raises:
			NotFoundError: If event is not found
		"""
		existing_event = EventCRUDService.get_event(event_key)
		
		# Create updated event with is_active=False and actual_end_date set to now
		deactivated_event = Event(
			event_key=existing_event.event_key,
			nws_alert_id=existing_event.nws_alert_id,
			episode_key=existing_event.episode_key,
			event_type=existing_event.event_type,
			hr_event_type=existing_event.hr_event_type,
			locations=existing_event.locations,
			start_date=existing_event.start_date,
			expected_end_date=existing_event.expected_end_date,
			actual_end_date=datetime.now(timezone.utc),
			updated_at=datetime.now(timezone.utc),
			description=existing_event.description,
			is_active=False,
			confirmed=existing_event.confirmed,
			raw_vtec=existing_event.raw_vtec,
			office=existing_event.office,
			property_damage=existing_event.property_damage,
			crops_damage=existing_event.crops_damage,
			range_miles=existing_event.range_miles,
			previous_ids=existing_event.previous_ids
		)
		
		# Update the event in state
		state.update_event(deactivated_event)
		logger.info(f"Deactivated event {event_key} with actual_end_date={deactivated_event.actual_end_date}")
		return deactivated_event

