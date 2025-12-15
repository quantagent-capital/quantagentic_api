import logging
from typing import List, Optional
from datetime import datetime
from app.schemas.counties import County
from app.schemas.event import Event
from app.schemas.episode import Episode
from app.schemas.drought import Drought
from app.redis_client import quantagent_redis
logger = logging.getLogger(__name__)

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
	REDIS_COUNTY_KEY_PREFIX = "county:"
	REDIS_DROUGHT_KEY_PREFIX = "drought:"
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
		event_keys = quantagent_redis.get_all_keys(f"{State.REDIS_EVENT_KEY_PREFIX}*")
		return quantagent_redis.read_all_as_schema(event_keys, Event, "event")

	@property
	def counties(self) -> List[County]:
		"""
		Getter for counties.
		Fetches all counties from Redis with prefix 'county:'.
		Usage: counties = state.counties
		"""
		county_keys = quantagent_redis.get_all_keys(f"{State.REDIS_COUNTY_KEY_PREFIX}*")
		return quantagent_redis.read_all_as_schema(county_keys, County, "county")

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
		return quantagent_redis.read_as_schema(redis_key, Event, "event")

	@property
	def droughts(self) -> List[Drought]:
		"""
		Getter for droughts.
		Fetches all droughts from Redis with prefix 'drought:'.
		Usage: droughts = state.droughts
		"""
		drought_keys = quantagent_redis.get_all_keys(f"{State.REDIS_DROUGHT_KEY_PREFIX}*")
		return quantagent_redis.read_all_as_schema(drought_keys, Drought, "drought")

	@property
	def active_droughts(self) -> List[Drought]:
		"""
		Getter for active droughts.
		Fetches all droughts from Redis and filters by is_active=True.
		Usage: active_droughts = state.active_droughts
		"""
		all_droughts = self.droughts
		return [drought for drought in all_droughts if drought.is_active is True]

	def add_drought(self, drought: Drought):
		"""
		Add a drought to both Redis and in-memory collection.
		
		Args:
			drought: Drought object
		"""
		redis_key = f"{State.REDIS_DROUGHT_KEY_PREFIX}{drought.event_key}"
		quantagent_redis.create(redis_key, drought.to_dict())
	
	def remove_drought(self, event_key: str):
		"""Remove a drought by event_key."""
		redis_key = f"{State.REDIS_DROUGHT_KEY_PREFIX}{event_key}"
		quantagent_redis.delete(redis_key)

	def update_drought(self, drought: Drought):
		"""Update a drought in both Redis and in-memory collection."""
		redis_key = f"{State.REDIS_DROUGHT_KEY_PREFIX}{drought.event_key}"
		quantagent_redis.update(redis_key, drought.to_dict())
	
	def active_drought_exists(self, event_key: str) -> bool:
		"""
		Check if a active drought exists with the given event_key.
		
		Args:
			event_key: Event key to check
			
		Returns:
			True if a active drought exists, False otherwise
		"""
		redis_key = f"{State.REDIS_DROUGHT_KEY_PREFIX}{event_key}"
		drought_dict = quantagent_redis.read_as_dict(redis_key, "drought")
		if drought_dict is None or drought_dict.get('is_active', False) is False:
			return False
		
		return True

	def get_drought(self, event_key: str) -> Optional[Drought]:
		"""Get a drought by event_key."""
		redis_key = f"{State.REDIS_DROUGHT_KEY_PREFIX}{event_key}"
		return quantagent_redis.read_as_schema(redis_key, Drought, "drought")

# Global state instance
state = State()

