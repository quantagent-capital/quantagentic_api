from datetime import datetime, timezone
from typing import Optional
from app.crews.utils.nws_event_types import NWS_WARNING_CODES
from app.exceptions import NotFoundError
from app.exceptions.base import ConflictError
from app.schemas.event import Event
from app.shared_models.nws_poller_models import FilteredNWSAlert
from app.state import state
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
				start_date=alert.effective,
				expected_end_date=alert.expected_end,
				updated_at=datetime.now(timezone.utc),
				description=f"{alert.headline}\n\n{alert.description}",
				is_active=True,
				raw_vtec=alert.raw_vtec
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

