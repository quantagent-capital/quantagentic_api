#!/usr/bin/env python3
"""
Debug script to run the disaster polling task locally without Celery.
This is useful for debugging and testing the task logic directly.

Usage:
	python debug/task_direct.py
	Or use the "Debug: Disaster Polling Task (Direct)" configuration in Cursor IDE
"""
# CRITICAL: Import env setup FIRST, before any other imports
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

# Now import other modules
import logging

from app.crews.disaster_polling_agent.executor import DisasterPollingExecutor

# Configure logging to see all output
logging.basicConfig(
	level=logging.DEBUG,
	format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
	handlers=[
		logging.StreamHandler(sys.stdout)
	]
)

logger = logging.getLogger(__name__)

if __name__ == "__main__":
	logger.info("=" * 80)
	logger.info("DEBUG: Running disaster polling task directly (no Celery)")
	logger.info("=" * 80)
	
	try:
		executor = DisasterPollingExecutor()
		result = executor.execute()
		
		logger.info("=" * 80)
		logger.info("DEBUG: Task completed successfully")
		logger.info(f"Result: {result}")
		logger.info("=" * 80)
		
		sys.exit(0)
	except Exception as e:
		logger.error("=" * 80)
		logger.error(f"DEBUG: Task failed with error: {str(e)}")
		logger.error(f"Exception type: {type(e).__name__}")
		import traceback
		logger.error("Full traceback:")
		logger.error(traceback.format_exc())
		logger.error("=" * 80)
		sys.exit(1)

