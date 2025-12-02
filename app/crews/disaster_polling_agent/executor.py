"""
Executor for the disaster polling agent crew.
"""
from typing import Any, Dict
from datetime import datetime
from app.crews.base_executor import BaseExecutor
from app.crews.disaster_polling_agent.crew import DisasterPollingCrew
from app.state import state
import logging

logger = logging.getLogger(__name__)


class DisasterPollingExecutor(BaseExecutor):
	"""
	Executor for the disaster polling agent crew.
	Handles running the crew and processing results.
	"""
	
	def _execute(self) -> Dict[str, Any]:
		"""
		Execute the disaster polling crew.
		
		Returns:
			Dictionary with execution results
		"""
		try:
			logger.info("Starting disaster polling crew execution")
			
			# Run the crew
			crew_instance = DisasterPollingCrew()
			result = crew_instance.crew().kickoff()
			
			# Update last poll time
			state.last_disaster_poll_time = datetime.now(datetime.timezone.utc)
			
			# Process results and call API endpoints
			# TODO: Parse crew result and call appropriate controller endpoints
			# This will be implemented based on the crew's output format
			
			logger.info("Disaster polling crew execution completed")
			
			return {
				"status": "success",
				"result": str(result),
				"poll_time": state.last_disaster_poll_time.isoformat()
			}
			
		except Exception as e:
			logger.error(f"Error executing disaster polling crew: {str(e)}")
			raise

