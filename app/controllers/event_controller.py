from fastapi import APIRouter, status
from app.schemas.event import Event
from app.shared_models.nws_poller_models import FilteredNWSAlert
from app.services.event_service import EventService
from app.exceptions import handle_service_exceptions, NotFoundError

router = APIRouter(prefix="/events", tags=["events"])

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
async def update_event(event_key: str, event: Event):
	"""
	Update an existing event.
	"""
	updated_event = EventService.update_event(event_key, event)
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

