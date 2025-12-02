"""
Base executor class for CrewAI crews with retry logic and exception handling.
"""
import logging
from typing import Any, Optional
from app.config import settings
from app.exceptions import ServiceError

logger = logging.getLogger(__name__)


class ExecutorRetryExhaustedError(ServiceError):
	"""
	Exception raised when an executor exhausts all retry attempts.
	"""
	def __init__(self, executor_name: str, max_retries: int):
		message = f"{executor_name} exhausted all {max_retries} retry attempts"
		super().__init__(message, status_code=500)


class BaseExecutor:
	"""
	Base executor class that provides retry logic and exception handling.
	All crew executors should inherit from this class.
	"""
	
	def __init__(self, max_retries: Optional[int] = None):
		"""
		Initialize the base executor.
		
		Args:
			max_retries: Maximum number of retry attempts (defaults to config value)
		"""
		self.max_retries = max_retries or settings.executor_max_retries
		self.executor_name = self.__class__.__name__
	
	def execute(self, *args, **kwargs) -> Any:
		"""
		Execute the crew with retry logic.
		
		Args:
			*args: Positional arguments to pass to _execute
			**kwargs: Keyword arguments to pass to _execute
		
		Returns:
			Result from _execute method
		
		Raises:
			ExecutorRetryExhaustedError: If all retries are exhausted
		"""
		last_exception = None
		
		for attempt in range(1, self.max_retries + 1):
			try:
				logger.info(f"{self.executor_name} attempt {attempt}/{self.max_retries}")
				result = self._execute(*args, **kwargs)
				logger.info(f"{self.executor_name} completed successfully on attempt {attempt}")
				return result
			except Exception as e:
				last_exception = e
				logger.warning(
					f"{self.executor_name} attempt {attempt}/{self.max_retries} failed: {str(e)}"
				)
				if attempt < self.max_retries:
					logger.info(f"{self.executor_name} retrying...")
				else:
					logger.error(
						f"{self.executor_name} exhausted all retries. Last error: {str(e)}"
					)
		
		# All retries exhausted
		raise ExecutorRetryExhaustedError(self.executor_name, self.max_retries)
	
	def _execute(self, *args, **kwargs) -> Any:
		"""
		Override this method in subclasses to implement the actual execution logic.
		
		Args:
			*args: Positional arguments
			**kwargs: Keyword arguments
		
		Returns:
			Result of the execution
		
		Raises:
			Exception: Any exception that should trigger a retry
		"""
		raise NotImplementedError("Subclasses must implement _execute method")

