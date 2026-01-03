"""
Executor for Event Confirmation Crew with retry logic.
"""
from typing import Any, Dict
from app.crews.base_executor import BaseExecutor
from app.crews.event_confirmation_crew.crew import EventLocationConfirmationCrew
import logging

logger = logging.getLogger(__name__)


class EventConfirmationExecutor(BaseExecutor):
	"""
	Executor for the Event Confirmation Crew.
	Inherits retry logic from BaseExecutor.
	"""
	
	def __init__(self, max_retries: int = None):
		"""
		Initialize the event confirmation executor.
		
		Args:
			max_retries: Maximum number of retry attempts (defaults to config value)
		"""
		super().__init__(max_retries=max_retries)
		self.crew = EventLocationConfirmationCrew()
	
	def _execute(self, event_key: str, *args, **kwargs) -> Any:
		"""
		Execute the event confirmation crew.
		
		Args:
			event_key: The event key to confirm
			*args: Additional positional arguments
			**kwargs: Additional keyword arguments
		
		Returns:
			Result from crew execution
		"""
		inputs = {
			"event_key": event_key,
			**kwargs
		}
		return self.crew.kickoff(inputs=inputs)
