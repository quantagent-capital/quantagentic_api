from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict
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
		# TODO: Implement has_episode logic
		try:
			event = EventCRUDService.get_event(event_key)
			return event.episode_key is not None
		except Exception:
			return False
	
	@staticmethod
	def get_events(hour_offset: Optional[int] = 72) -> List[Event]:
		"""
		Get events from state, optionally filtered by hour_offset.
		
		Filtering logic:
		- Calculate the time point: now - hour_offset hours
		- Include events where the time point falls between start_date and actual_end_date
		- If either actual_end_date or start_date is null, automatically include the event
		
		Args:
			hour_offset: Hours to look back from now. Default is 72 hours.
		
		Returns:
			List of Event objects matching the filter criteria
		"""
		all_events = state.events
		
		# If hour_offset is None or 0, return all events
		if hour_offset is None or hour_offset <= 0:
			return all_events
		
		# Calculate the time point exactly hour_offset hours ago
		current_time = datetime.now(timezone.utc)
		time_point = current_time - timedelta(hours=hour_offset)
		
		filtered_events = []
		for event in all_events:
			# If actual_end_date is null, automatically include the event
			# (start_date is required in schema, but check for safety)
			if event.actual_end_date is None or event.start_date is None:
				filtered_events.append(event)
				continue
			
			# Check if time_point falls between start_date and actual_end_date (inclusive)
			if event.start_date <= time_point <= event.actual_end_date:
				filtered_events.append(event)
		
		return filtered_events
	
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

