from typing import List, Optional
from datetime import datetime
from app.schemas.event import Event
from app.schemas.episode import Episode
from app.redis_client import quantagent_redis

class State:
	"""
	Shared memory class for the entire API and all agents.
	This acts as a singleton state object.
	
	PROPERTY/SETTER PATTERN EXPLANATION:
	------------------------------------
	The @property and @setter decorators allow us to use methods like attributes,
	but with controlled access. Instead of directly accessing `state._active_events`,
	we use `state.active_events` which:
	
	1. GETTER (@property): When you read `state.active_events`, it calls the getter method
	   - Allows validation, logging, or transformation before returning
	   - Example: `events = state.active_events` calls the getter
	
	2. SETTER (@property_name.setter): When you assign `state.active_events = [...]`, 
	   it calls the setter method
	   - Allows validation, type checking, or side effects before setting
	   - Example: `state.active_events = [event1, event2]` calls the setter
	
	Benefits:
	- Encapsulation: Internal storage (_active_events) is protected
	- Validation: Can check types/values before setting
	- Future-proof: Can add logic later without changing calling code
	- Clean API: Looks like attribute access but with method control
	"""
	
	_instance: Optional['State'] = None
	REDIS_EVENT_KEY_PREFIX = "event:"
	REDIS_EPISODE_KEY_PREFIX = "episode:"
	
	def __new__(cls):
		if cls._instance is None:
			cls._instance = super(State, cls).__new__(cls)
			cls._instance._initialized = False
		return cls._instance
	
	def __init__(self):
		if self._initialized:
			return
		
		# Private attributes (prefixed with _) store the actual data
		self._initialized = True
	
	@property
	def events(self) -> List[Event]:
		"""
		Getter for events.
		Fetches all events from Redis with prefix 'event:'.
		Usage: events = state.events
		"""
		# Get all keys matching the event pattern
		event_keys = quantagent_redis.get_all_keys(f"{State.REDIS_EVENT_KEY_PREFIX}*")
		
		# Fetch all events from Redis and convert to Event objects
		events = []
		for key in event_keys:
			try:
				event_dict = quantagent_redis.read(key)
				if event_dict is None:
					continue
				
				# Convert dictionary to Event object
				event = Event.from_dict(event_dict)
				events.append(event)
			except Exception as e:
				# Log error but continue processing other events
				import logging
				logger = logging.getLogger(__name__)
				logger.warning(f"Failed to load event from Redis key {key}: {str(e)}")
				continue
		
		return events

	@property
	def active_events(self) -> List[Event]:
		"""
		Getter for active events.
		Fetches all events from Redis and filters by is_active=True.
		Usage: active_events = state.active_events
		"""
		all_events = self.events
		return [event for event in all_events if event.is_active is True]

	def add_event(self, event: Event):
		"""
		Add an event to both Redis and in-memory collection.
		
		Args:
			event: Event object
		"""
		redis_key = f"{State.REDIS_EVENT_KEY_PREFIX}{event.event_key}"
		quantagent_redis.create(redis_key, event.to_dict())
	
	def remove_event(self, event_key: str):
		"""Remove an event by key."""
		redis_key = f"{State.REDIS_EVENT_KEY_PREFIX}{event_key}"
		quantagent_redis.delete(redis_key)

	def update_event(self, event: Event):
		"""Update an event in both Redis and in-memory collection."""
		redis_key = f"{State.REDIS_EVENT_KEY_PREFIX}{event.event_key}"
		quantagent_redis.update(redis_key, event.to_dict())
	
	def event_exists(self, event_key: str) -> bool:
		"""
		Check if an event exists with the given event_key.
		
		Args:
			event_key: Event key to check
			
		Returns:
			True if an event exists, False otherwise
		"""
		# Check Redis for the event using standardized key creation
		redis_key = f"{State.REDIS_EVENT_KEY_PREFIX}{event_key}"
		event_dict = quantagent_redis.read(redis_key)
		
		if event_dict is None:
			return False
		
		return True

	def get_event(self, event_key: str) -> Optional[Event]:
		"""Get an event by key."""
		redis_key = f"{State.REDIS_EVENT_KEY_PREFIX}{event_key}"
		event_dict = quantagent_redis.read(redis_key)
		if event_dict is None:
			return None
		return Event.from_dict(event_dict)

# Global state instance
state = State()

