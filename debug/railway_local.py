#!/usr/bin/env python3
"""
Local debug script that mimics Railway's exact startup process.
Starts both Celery worker (with beat) and FastAPI server in the same process.
This allows debugging both services simultaneously without subprocess switching.

Usage:
	python debug/railway_local.py
	Or use the "Debug: Railway Local (Full Stack)" configuration in Cursor IDE
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

import signal
import threading
import logging
import asyncio

# Setup simple logging for debug mode (not JSON, easier to read in IDE)
# Check if we're in debug mode (when running from IDE)
is_debug_mode = os.getenv("PYTHONDEBUG", "").lower() in ("1", "true") or "--debug" in sys.argv

if is_debug_mode:
	# Use simple format for IDE debug console
	# Configure root logger to output to stdout with simple format
	root_logger = logging.getLogger()
	root_logger.setLevel(logging.INFO)
	
	# Remove any existing handlers
	root_logger.handlers.clear()
	
	# Create stdout handler with simple format
	stdout_handler = logging.StreamHandler(sys.stdout)
	stdout_handler.setLevel(logging.INFO)
	formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
	stdout_handler.setFormatter(formatter)
	root_logger.addHandler(stdout_handler)
	
	# Configure app loggers - they'll propagate to root logger
	# Set level for all app.* loggers to ensure they log
	app_logger = logging.getLogger("app")
	app_logger.setLevel(logging.INFO)
	app_logger.propagate = True  # Ensure propagation to root logger
	
	logger = logging.getLogger(__name__)
else:
	# Use JSON format for Railway/production
	from app.logging_config import setup_logging, get_logger
	setup_logging(level="INFO")
	logger = get_logger(__name__)


def cleanup(signum=None, frame=None):
	"""Cleanup function to stop all services."""
	logger.info("=" * 80)
	logger.info("Shutting down services...")
	logger.info("All services stopped.")
	logger.info("=" * 80)
	sys.exit(0)


# Register signal handlers
signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)


def run_celery_worker():
	"""Run Celery worker with beat in the current process."""
	# Reconfigure logging for debug mode after celery_app import
	# (celery_app.py calls setup_logging() which we need to override)
	if is_debug_mode:
		root_logger = logging.getLogger()
		root_logger.handlers.clear()
		stdout_handler = logging.StreamHandler(sys.stdout)
		stdout_handler.setLevel(logging.INFO)
		formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
		stdout_handler.setFormatter(formatter)
		root_logger.addHandler(stdout_handler)
		root_logger.setLevel(logging.INFO)
		
		# Configure all Celery loggers to propagate to root (which has stdout handler)
		for logger_name in ["celery", "celery.beat", "celery.worker", "celery.task"]:
			celery_logger = logging.getLogger(logger_name)
			celery_logger.handlers.clear()  # Remove any existing handlers
			celery_logger.setLevel(logging.INFO)
			celery_logger.propagate = True  # Let logs propagate to root logger
		
		# Ensure app loggers are also configured to propagate
		app_logger = logging.getLogger("app")
		app_logger.setLevel(logging.INFO)
		app_logger.propagate = True
	
	from app.celery_app import celery_app
	
	# Use solo pool to avoid subprocess spawning - all code runs in main process
	# Pass argv directly to worker_main (starts with 'worker' subcommand)
	logger.info("Starting Celery worker with beat scheduler (pool=solo)...")
	try:
		# Start worker - this blocks until shutdown
		# argv should start with 'worker' subcommand, not 'celery'
		celery_app.worker_main(argv=[
			"worker",
			"--beat",
			"--pool=solo",
			"--loglevel=info"
		])
	except SystemExit:
		# Celery worker_main calls sys.exit() on shutdown, which is expected
		pass
	except KeyboardInterrupt:
		# Handle interrupt gracefully
		logger.info("Celery worker interrupted")


def run_hypercorn():
	"""Run Hypercorn server in the current process."""
	import hypercorn.asyncio
	from hypercorn.config import Config
	from main import app
	
	port = os.getenv("PORT", "8000")
	logger.info(f"Starting Hypercorn on port {port}...")
	
	# Create Hypercorn config
	config = Config()
	config.bind = [f"[::]:{port}"]
	config.use_reload = True  # Enable reload for local development
	
	# Run Hypercorn - this blocks until shutdown
	# Signal handlers will handle cleanup when Ctrl+C is pressed
	asyncio.run(hypercorn.asyncio.serve(app, config))


if __name__ == "__main__":
	logger.info("=" * 80)
	logger.info("Starting QuantAgentic API services (Railway Local Debug Mode)")
	logger.info("All services run in the main process - breakpoints work everywhere!")
	logger.info("=" * 80)
	
	try:
		# Start Celery worker with beat in a background thread
		# Using solo pool ensures all tasks run in the main process
		celery_thread = threading.Thread(target=run_celery_worker, daemon=True)
		celery_thread.start()
		
		# Wait a moment for Celery to initialize
		logger.info("Waiting for Celery to initialize...")
		import time
		time.sleep(3)
		
		logger.info("Celery worker started")
		logger.info("=" * 80)
		logger.info("Both services are running. Press Ctrl+C to stop.")
		logger.info("=" * 80)
		
		# Start Hypercorn in the main thread (this blocks)
		# The debugger attaches to this main process, and breakpoints work
		# for both Celery tasks (via solo pool) and FastAPI endpoints
		run_hypercorn()
		
	except KeyboardInterrupt:
		logger.info("Received interrupt signal...")
	except Exception as e:
		logger.error(f"Error starting services: {e}")
		import traceback
		logger.error(traceback.format_exc())
	finally:
		cleanup()

