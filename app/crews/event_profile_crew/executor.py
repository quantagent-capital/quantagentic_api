"""
Executor for the event profile crew.
"""
from typing import Any, Dict
from app.crews.base_executor import BaseExecutor
from app.shared_models.nws_poller_models import FilteredNWSAlert
from app.crews.event_profile_crew.crew import EventProfileCrew
import logging
import agentops
agentops.init(default_tags=['event_profile_crew'])
logger = logging.getLogger(__name__)


class EventProfileExecutor(BaseExecutor):
	"""
	Executor for the event profile crew.
	Handles running the crew to create Event models from FilteredNWSAlerts.
	"""
	
	def __init__(self, alert: FilteredNWSAlert, max_retries: int = None):
		"""
		Initialize executor with alert data.
		
		Args:
			alert: FilteredNWSAlert data to process
			max_retries: Maximum retry attempts (uses default from settings if None)
		"""
		super().__init__(max_retries=max_retries)
		self.alert = alert
	
	def _execute(self) -> Dict[str, Any]:
		"""
		Execute the event profile crew.
		
		Returns:
			Dictionary with execution results containing the Event model
		"""
		try:
			logger.info("Starting event profile crew execution")
			
			llm_input = {
				"location_endpoints": self.alert.affected_zones_ugc_endpoints,
				"event_key": self.alert.key,
				"raw_ugc_codes": self.alert.affected_zones_raw_ugc_codes,
				"nws_alert_id": self.alert.alert_id,
				"description": self.alert.description,
				"start_date": self.alert.effective,
				"abbreviated_event_type": self.alert.event_type,
			}

			# Run the crew
			crew_instance = EventProfileCrew()
			crew = crew_instance.crew()
			result = crew.kickoff(inputs=llm_input)
			
			logger.info("Event profile crew execution completed successfully")
			
			return result.pydantic.event
			
		except Exception as e:
			logger.error(f"Error executing event profile crew: {str(e)}")
			import traceback
			logger.error(f"Traceback: {traceback.format_exc()}")
			raise

