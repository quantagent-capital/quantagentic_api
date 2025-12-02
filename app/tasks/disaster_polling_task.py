"""
Celery task for disaster polling agent.
"""
from app.celery_app import celery_app
from app.crews.disaster_polling_agent.executor import DisasterPollingExecutor
import logging

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.disaster_polling_task", bind=True, max_retries=3)
def disaster_polling_task(self):
	"""
	Celery task that runs the disaster polling agent every 5 minutes.
	
	Returns:
		Execution result
	"""
	try:
		executor = DisasterPollingExecutor()
		result = executor.execute()
		logger.info(f"Disaster polling task completed: {result}")
		return result
	except Exception as e:
		logger.error(f"Disaster polling task failed: {str(e)}")
		# Retry with exponential backoff
		raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))

