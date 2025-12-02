from typing import List, Optional
from datetime import datetime
from app.schemas.event import Event
from app.schemas.episode import Episode

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
	
	def __new__(cls):
		if cls._instance is None:
			cls._instance = super(State, cls).__new__(cls)
			cls._instance._initialized = False
		return cls._instance
	
	def __init__(self):
		if self._initialized:
			return
		
		# Private attributes (prefixed with _) store the actual data
		self._active_events: List[Event] = []
		self._active_episodes: List[Episode] = []
		self._last_disaster_poll_time: Optional[datetime] = None
		self._initialized = True
	
	@property
	def active_events(self) -> List[Event]:
		"""
		Getter for active_events.
		Usage: events = state.active_events
		"""
		return self._active_events
	
	@active_events.setter
	def active_events(self, value: List[Event]):
		"""
		Setter for active_events.
		Usage: state.active_events = [event1, event2]
		"""
		self._active_events = value
	
	def add_active_event(self, event: Event):
		"""Add an active event."""
		if event not in self._active_events:
			self._active_events.append(event)
	
	def remove_active_event(self, event_key: str):
		"""Remove an active event by key."""
		self._active_events = [e for e in self._active_events if e.event_key != event_key]
	
	@property
	def active_episodes(self) -> List[Episode]:
		"""
		Getter for active_episodes.
		Usage: episodes = state.active_episodes
		"""
		return self._active_episodes
	
	@active_episodes.setter
	def active_episodes(self, value: List[Episode]):
		"""
		Setter for active_episodes.
		Usage: state.active_episodes = [episode1, episode2]
		"""
		self._active_episodes = value
	
	def add_active_episode(self, episode: Episode):
		"""Add an active episode."""
		if episode not in self._active_episodes:
			self._active_episodes.append(episode)
	
	def remove_active_episode(self, episode_id: int):
		"""Remove an active episode by ID."""
		self._active_episodes = [e for e in self._active_episodes if e.episode_id != episode_id]
	
	@property
	def last_disaster_poll_time(self) -> Optional[datetime]:
		"""
		Getter for last_disaster_poll_time.
		Usage: poll_time = state.last_disaster_poll_time
		"""
		return self._last_disaster_poll_time
	
	@last_disaster_poll_time.setter
	def last_disaster_poll_time(self, value: Optional[datetime]):
		"""
		Setter for last_disaster_poll_time.
		Usage: state.last_disaster_poll_time = datetime.now()
		"""
		self._last_disaster_poll_time = value

# Global state instance
state = State()

