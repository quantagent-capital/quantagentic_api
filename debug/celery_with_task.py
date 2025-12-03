#!/usr/bin/env python3
"""
Debug script that queues the disaster polling task and waits for a Celery worker to process it.
This allows you to debug the task execution through Celery.

Usage:
	python debug/celery_with_task.py
	Or use the "Debug: Celery Worker with Auto Task" configuration in Cursor IDE

Note: You need to start a Celery worker in a separate terminal/process:
	celery -A app.celery_app worker --loglevel=info --pool=solo
"""
# CRITICAL: Set environment variables BEFORE any imports
import sys
import os

# Set environment variables BEFORE any imports
os.environ["LANGCHAIN_TRACING_V2"] = "false"
os.environ["LANGCHAIN_ENDPOINT"] = ""
os.environ["LANGCHAIN_API_KEY"] = ""
os.environ["LANGCHAIN_PROJECT"] = ""

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
	sys.path.insert(0, project_root)

import logging
from app.tasks.disaster_polling_task import disaster_polling_task

# Configure logging
logging.basicConfig(
	level=logging.INFO,
	format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
	handlers=[
		logging.StreamHandler(sys.stdout)
	]
)

logger = logging.getLogger(__name__)

if __name__ == "__main__":
	logger.info("=" * 80)
	logger.info("DEBUG: Queuing disaster polling task for Celery worker")
	logger.info("=" * 80)
	logger.info("")
	logger.info("⚠️  IMPORTANT: Make sure a Celery worker is running!")
	logger.info("   Start it in another terminal with:")
	logger.info("   celery -A app.celery_app worker --loglevel=info --pool=solo")
	logger.info("")
	logger.info("=" * 80)
	
	try:
		# Queue the task
		logger.info("Queuing disaster polling task...")
		result = disaster_polling_task.delay()
		logger.info(f"✓ Task queued successfully with ID: {result.id}")
		logger.info("")
		logger.info("Waiting for worker to process the task...")
		logger.info("(This will block until the task completes or times out)")
		logger.info("=" * 80)
		
		# Wait for result (with timeout)
		try:
			task_result = result.get(timeout=600)  # 10 minute timeout
			logger.info("=" * 80)
			logger.info("✓ Task completed successfully!")
			logger.info(f"Result: {task_result}")
			logger.info("=" * 80)
		except Exception as e:
			logger.error("=" * 80)
			logger.error(f"✗ Task failed or timed out: {str(e)}")
			logger.error(f"Exception type: {type(e).__name__}")
			logger.error("")
			logger.error("Make sure:")
			logger.error("  1. A Celery worker is running")
			logger.error("  2. Redis is running (docker-compose up -d)")
			logger.error("  3. The worker can connect to Redis")
			logger.error("=" * 80)
			import traceback
			logger.error("Full traceback:")
			logger.error(traceback.format_exc())
			sys.exit(1)
		
		sys.exit(0)
	except Exception as e:
		logger.error("=" * 80)
		logger.error(f"✗ Failed to queue task: {str(e)}")
		logger.error(f"Exception type: {type(e).__name__}")
		import traceback
		logger.error("Full traceback:")
		logger.error(traceback.format_exc())
		logger.error("=" * 80)
		sys.exit(1)

