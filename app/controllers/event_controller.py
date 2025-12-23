from fastapi import APIRouter, status, Query
from typing import List, Dict
from app.exceptions.base import ConflictError
from app.schemas.event import Event
from app.shared_models.nws_poller_models import FilteredNWSAlert
from app.services.event_service import EventService
from app.exceptions import handle_service_exceptions, NotFoundError
import logging
router = APIRouter(prefix="/events", tags=["events"])
logger = logging.getLogger(__name__)

@router.get("/", response_model=List[Event])
@handle_service_exceptions
async def get_events(
	active_only: bool = Query(default=True, description="If true, return only active events")
):
	"""
	Get events from state, optionally filtered by active_only.
	
	Args:
		active_only: If true, return only events from state.active_events. Default is True.
	
	Returns:
		List of Event objects matching the filter criteria
	"""
	events = EventService.get_events(active_only=active_only)
	return events

@router.post("/", response_model=Event, status_code=status.HTTP_201_CREATED)
@handle_service_exceptions
async def create_event(alert: FilteredNWSAlert):
	"""
	Create a new event from a FilteredNWSAlert.
	"""
	created_event = EventService.create_event_from_alert(alert)
	return created_event

@router.put("/{event_key}", response_model=Event)
@handle_service_exceptions
async def update_event(event_key: str, alert: FilteredNWSAlert):
	"""
	Update an existing event.
	"""
	if alert.message_type.upper() == "NEW":
		message = f"Cannot update an existing event with a message type of {alert.message_type}"
		logger.warning(message)
		raise ConflictError(message)

	updated_event = EventService.update_event_from_alert(alert)
	if updated_event is None:
		raise NotFoundError("Event", event_key)
	return updated_event

@router.get("/{event_key}", response_model=Event)
@handle_service_exceptions
async def get_event(event_key: str):
	"""
	Get an event by key.
	"""
	event = EventService.get_event(event_key)
	if event is None:
		raise NotFoundError("Event", event_key)
	return event

@router.get("/{event_key}/has_episode", response_model=bool)
@handle_service_exceptions
async def has_episode(event_key: str):
	"""
	Check if an event has an associated episode.
	"""
	return EventService.has_episode(event_key)

@router.get("/stats/counts-by-type", response_model=Dict[str, int])
@handle_service_exceptions
async def get_active_event_counts_by_type():
	"""
	Get count of all active events grouped by event type.
	
	Returns:
		Dictionary mapping event_type to count of active events
		Example: {"Flood Warning": 5, "Tornado Warning": 2}
	"""
	return EventService.get_active_event_counts_by_type()

@router.post("/confirm/{event_key}", status_code=status.HTTP_200_OK)
@handle_service_exceptions
async def confirm_event(event_key: str):
	"""
	Confirm whether an event occurred by running the confirmation crew.
	
	Args:
		event_key: The event key to confirm
	
	Returns:
		Result from the confirmation crew execution
	"""
	result = await EventService.confirm_event(event_key)
	return result

