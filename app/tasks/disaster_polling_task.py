"""
Celery task for disaster polling agent.
"""
from app.celery_app import celery_app
from app.crews.disaster_polling_agent.executor import DisasterPollingExecutor
import logging
import traceback

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.disaster_polling_task", bind=True, max_retries=3)
def disaster_polling_task(self):
	"""
	Celery task that runs the disaster polling agent every 5 minutes.
	
	Returns:
		Execution result
	"""
	logger.info("=" * 80)
	logger.info("DISASTER POLLING TASK STARTED")
	logger.info("=" * 80)
	
	try:
		logger.info("Creating DisasterPollingExecutor...")
		executor = DisasterPollingExecutor()
		logger.info("Executing disaster polling crew...")
		result = executor.execute()
		logger.info("=" * 80)
		logger.info(f"Disaster polling task completed successfully")
		logger.info(f"Result: {result}")
		logger.info("=" * 80)
		return result
	except Exception as e:
		logger.error("=" * 80)
		logger.error(f"Disaster polling task FAILED: {str(e)}")
		logger.error(f"Exception type: {type(e).__name__}")
		logger.error("Full traceback:")
		logger.error(traceback.format_exc())
		logger.error("=" * 80)
		# Retry with exponential backoff
		raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))

