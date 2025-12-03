"""
Executor for the disaster polling agent crew.
"""
from typing import Any, Dict
from datetime import datetime, timezone
from app.crews.base_executor import BaseExecutor
from app.crews.disaster_polling_agent.crew import DisasterPollingCrew
from app.state import state
from dotenv import load_dotenv
import logging
import agentops
agentops.init(default_tags=['crewai'])

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
			logger.info("Creating DisasterPollingCrew instance...")
			
			# Run the crew
			crew_instance = DisasterPollingCrew()
			logger.info("Crew instance created, getting crew object...")
			crew = crew_instance.crew()
			logger.info(f"Crew configured with {len(crew.agents)} agent(s) and {len(crew.tasks)} task(s)")
			logger.info("Kicking off crew execution...")
			
			result = crew.kickoff()
			logger.info(f"Crew execution completed. Result type: {type(result)}")
			
			# Update last poll time
			state.last_disaster_poll_time = datetime.now(timezone.utc)
			logger.info(f"Updated last poll time: {state.last_disaster_poll_time.isoformat()}")
			
			# Process results and call API endpoints
			# TODO: Parse crew result and call appropriate controller endpoints
			# This will be implemented based on the crew's output format
			
			logger.info("Disaster polling crew execution completed successfully")
			
			return {
				"status": "success",
				"result": str(result),
				"poll_time": state.last_disaster_poll_time.isoformat()
			}
			
		except Exception as e:
			logger.error(f"Error executing disaster polling crew: {str(e)}")
			import traceback
			logger.error(f"Traceback: {traceback.format_exc()}")
			raise

