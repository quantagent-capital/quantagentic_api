from typing import Optional
from app.redis_client import quantagent_redis
from app.schemas.event import Event

class EventService:
	"""Service layer for Event operations."""
	
	@staticmethod
	def _get_redis_key(event_key: str) -> str:
		return f"event:{event_key}"
	
	@staticmethod
	def create_event(event: Event) -> Event:
		"""
		Create a new event.
		
		Args:
			event: Event object to create
		
		Returns:
			Created event
		"""
		# TODO: Implement create logic
		key = EventService._get_redis_key(event.event_key)
		event_dict = event.to_dict()
		quantagent_redis.create(key, event_dict)
		return event
	
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
		# TODO: Implement update logic
		key = EventService._get_redis_key(event_key)
		if not quantagent_redis.exists(key):
			return None
		event_dict = event.to_dict()
		quantagent_redis.update(key, event_dict)
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
		# TODO: Implement get logic
		key = EventService._get_redis_key(event_key)
		event_dict = quantagent_redis.read(key)
		if event_dict is None:
			return None
		return Event.from_dict(event_dict)
	
	@staticmethod
	def has_episode(event_key: str) -> bool:
		"""
		Check if an event has an associated episode.
		
		Args:
			event_key: Key of event to check
		
		Returns:
			True if event has an episode_id, False otherwise
		"""
		# TODO: Implement has_episode logic
		event = EventService.get_event(event_key)
		if event is None:
			return False
		return event.episode_id is not None

