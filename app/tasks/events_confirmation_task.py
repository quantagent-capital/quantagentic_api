"""
Celery task for event confirmation.
"""
from app.celery_app import celery_app
from app.services.event_service import EventService
import logging

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.events_confirmation_task", bind=True, max_retries=3)
def events_confirmation_task(self):
	"""
	Celery task that confirms all active and unconfirmed events.
	Runs every hour via CeleryBeat schedule.
	
	Returns:
		Dictionary with summary of confirmation results
	"""
	logger.info("=" * 80)
	logger.info("EVENTS CONFIRMATION TASK STARTED")
	logger.info("=" * 80)
	
	try:
		# Import asyncio to run the async function
		import asyncio
		result = asyncio.run(EventService.confirm_events())
		logger.info("=" * 80)
		logger.info(f"EVENTS CONFIRMATION TASK COMPLETED: {result}")
		logger.info("=" * 80)
		return result
	except Exception as e:
		logger.error("=" * 80)
		logger.error(f"Events confirmation task FAILED: {str(e)}")
		logger.error(f"Exception type: {type(e).__name__}")
		logger.error("Full traceback:")
		import traceback
		logger.error(traceback.format_exc())
		logger.error("=" * 80)
		# Retry with exponential backoff
		raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))

