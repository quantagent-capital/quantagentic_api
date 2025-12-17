"""
Celery task for wildfire data synchronization.
"""
from app.celery_app import celery_app
from app.processors.wildfire_processor import WildfireProcessor
import logging

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.wildfire_sync_task", bind=True, max_retries=3)
def wildfire_sync_task(self):
	"""
	Celery task that syncs wildfire data by polling ArcGIS API.
	Creates, updates, or completes wildfire events based on API responses.
	
	Returns:
		Dictionary with counts of created, updated, and completed events
	"""
	logger.info("=" * 80)
	logger.info("WILDFIRE SYNC TASK STARTED")
	logger.info("=" * 80)
	
	try:
		result = WildfireProcessor.sync_wildfire_data()
		logger.info("=" * 80)
		logger.info(f"WILDFIRE SYNC TASK COMPLETED: {result}")
		logger.info("=" * 80)
		return result
	except Exception as e:
		logger.error("=" * 80)
		logger.error(f"Wildfire sync task FAILED: {str(e)}")
		logger.error(f"Exception type: {type(e).__name__}")
		logger.error("Full traceback:")
		import traceback
		logger.error(traceback.format_exc())
		logger.error("=" * 80)
		# Retry with exponential backoff
		raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
