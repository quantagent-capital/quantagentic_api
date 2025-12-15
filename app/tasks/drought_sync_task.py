"""
Celery task for drought data synchronization.
"""
from app.celery_app import celery_app
from app.services.drought_service import DroughtService
import logging

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.drought_sync_task", bind=True, max_retries=3)
def drought_sync_task(self):
	"""
	Celery task that syncs drought data by comparing current and previous week drought maps.
	Creates, updates, or completes drought events based on county intersections.
	
	Returns:
		Dictionary with counts of created, updated, and completed events
	"""
	logger.info("=" * 80)
	logger.info("DROUGHT SYNC TASK STARTED")
	logger.info("=" * 80)
	
	try:
		result = DroughtService.sync_drought_data()
		logger.info("=" * 80)
		logger.info(f"DROUGHT SYNC TASK COMPLETED: {result}")
		logger.info("=" * 80)
		return result
	except Exception as e:
		logger.error("=" * 80)
		logger.error(f"Drought sync task FAILED: {str(e)}")
		logger.error(f"Exception type: {type(e).__name__}")
		logger.error("Full traceback:")
		import traceback
		logger.error(traceback.format_exc())
		logger.error("=" * 80)
		# Retry with exponential backoff
		raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))

