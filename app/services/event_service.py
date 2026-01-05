from typing import Optional, List, Dict
from app.schemas.event import Event
from app.shared_models.nws_poller_models import FilteredNWSAlert
from app.services.event_crud_service import EventCRUDService
from app.services.event_create_service import EventCreateService
from app.services.event_update_service import EventUpdateService
from app.services.event_completion_service import EventCompletionService
from app.services.event_confirmation_service import EventConfirmationService


class EventService:
	"""
	Service layer for Event operations.
	
	This class acts as a facade, delegating to specialized services:
	- EventCRUDService: CRUD operations
	- EventCreateService: Event creation
	- EventUpdateService: Event updates
	- EventCompletionService: Completion checking
	"""

	# CRUD Operations - delegate to EventCRUDService
	@staticmethod
	def get_event(event_key: str) -> Event:
		"""Get an event by key."""
		return EventCRUDService.get_event(event_key)

	@staticmethod
	def has_episode(event_key: str) -> bool:
		"""Check if an event has an associated episode."""
		return EventCRUDService.has_episode(event_key)

	@staticmethod
	def get_events(active_only: bool = True) -> List[Event]:
		"""Get events from state, optionally filtered by active_only."""
		return EventCRUDService.get_events(active_only)

	@staticmethod
	def get_active_event_counts_by_type() -> Dict[str, int]:
		"""Get count of active events grouped by event type."""
		return EventCRUDService.get_active_event_counts_by_type()

	@staticmethod
	def deactivate_event(event_key: str) -> Event:
		"""Deactivate an event by setting is_active=False and actual_end_date to current time."""
		return EventCRUDService.deactivate_event(event_key)

	# Create Operations - delegate to EventCreateService
	@staticmethod
	def create_event_from_alert(alert: FilteredNWSAlert) -> Event:
		"""Create an event from a FilteredNWSAlert."""
		return EventCreateService.create_event_from_alert(alert)

	# Update Operations - delegate to EventUpdateService
	@staticmethod
	def update_event_from_alert(updateable_alert: FilteredNWSAlert) -> Optional[Event]:
		"""Update an existing event from an updateable alert."""
		return EventUpdateService.update_event_from_alert(updateable_alert)

	# Completion Operations - delegate to EventCompletionService
	@staticmethod
	def check_completed_events():
		"""Check for completed events that should be marked as inactive."""
		return EventCompletionService.check_completed_events()
	
	# Confirmation Operations - delegate to EventConfirmationService
	@staticmethod
	async def confirm_event(event: Event):
		"""Confirm whether an event occurred by running the confirmation crew."""
		return await EventConfirmationService.confirm_event(event)
	
	@staticmethod
	async def confirm_events():
		"""Confirm all active and unconfirmed events."""
		return await EventConfirmationService.confirm_events()
