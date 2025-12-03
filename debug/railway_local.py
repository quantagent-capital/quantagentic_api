#!/usr/bin/env python3
"""
Local debug script that mimics Railway's exact startup process.
Starts both Celery worker (with beat) and FastAPI server.
This allows debugging both services simultaneously, matching Railway's behavior.

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

import subprocess
import signal
import time
import logging
from app.logging_config import setup_logging, get_logger

# Setup logging
setup_logging(level="INFO")
logger = get_logger(__name__)

# Global process references
celery_process = None
hypercorn_process = None


def cleanup(signum=None, frame=None):
	"""Cleanup function to stop all processes."""
	global celery_process, hypercorn_process
	
	logger.info("=" * 80)
	logger.info("Shutting down services...")
	
	if hypercorn_process and hypercorn_process.poll() is None:
		logger.info("Stopping FastAPI server...")
		hypercorn_process.terminate()
		try:
			hypercorn_process.wait(timeout=5)
		except subprocess.TimeoutExpired:
			logger.warning("Hypercorn didn't stop gracefully, killing...")
			hypercorn_process.kill()
	
	if celery_process and celery_process.poll() is None:
		logger.info("Stopping Celery worker...")
		celery_process.terminate()
		try:
			celery_process.wait(timeout=5)
		except subprocess.TimeoutExpired:
			logger.warning("Celery didn't stop gracefully, killing...")
			celery_process.kill()
	
	logger.info("All services stopped.")
	logger.info("=" * 80)
	sys.exit(0)


# Register signal handlers
signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)


if __name__ == "__main__":
	logger.info("=" * 80)
	logger.info("Starting QuantAgentic API services (Railway Local Debug Mode)")
	logger.info("=" * 80)
	
	try:
		# Start Celery worker with beat in the background
		logger.info("Starting Celery worker with beat scheduler...")
		celery_cmd = [
			sys.executable, "-m", "celery",
			"-A", "app.celery_app",
			"worker",
			"--beat",
			"--loglevel=info",
			"--logfile=/dev/stdout"  # Use stdout for Railway compatibility
		]
		
		celery_process = subprocess.Popen(
			celery_cmd,
			stdout=subprocess.PIPE,
			stderr=subprocess.STDOUT,
			text=True,
			bufsize=1
		)
		
		# Wait a moment for Celery to start
		logger.info("Waiting for Celery to initialize...")
		time.sleep(3)
		
		# Check if Celery started successfully
		if celery_process.poll() is not None:
			logger.error("ERROR: Celery worker failed to start!")
			logger.error(f"Exit code: {celery_process.returncode}")
			sys.exit(1)
		
		logger.info(f"Celery worker started (PID: {celery_process.pid})")
		logger.info("Starting FastAPI server...")
		logger.info("=" * 80)
		
		# Start FastAPI server in the foreground (this keeps the process alive)
		# This matches Railway's behavior - hypercorn runs in foreground
		port = os.getenv("PORT", "8000")
		hypercorn_cmd = [
			sys.executable, "-m", "hypercorn",
			"main:app",
			"--bind", f"[::]:{port}",
			"--reload"  # Enable reload for local development
		]
		
		logger.info(f"Starting Hypercorn on port {port}...")
		logger.info("=" * 80)
		logger.info("Both services are running. Press Ctrl+C to stop.")
		logger.info("=" * 80)
		
		# Stream Celery output to stdout in a separate thread
		def stream_celery_output():
			"""Stream Celery output to stdout."""
			try:
				for line in iter(celery_process.stdout.readline, ''):
					if line:
						# Use print to ensure it goes to stdout (for Railway compatibility)
						print(f"[CELERY] {line.rstrip()}", flush=True)
			except Exception as e:
				logger.error(f"Error streaming Celery output: {e}")
		
		import threading
		celery_thread = threading.Thread(target=stream_celery_output, daemon=True)
		celery_thread.start()
		
		# Start hypercorn in foreground (this blocks)
		# The debugger attaches to this main process, and breakpoints in your code
		# (app/ directory) will work for both Celery tasks and FastAPI endpoints
		logger.info("Starting Hypercorn (debugger attached to main process)...")
		logger.info("Note: Breakpoints in app/ code will work for both Celery and FastAPI")
		hypercorn_process = subprocess.Popen(
			hypercorn_cmd,
			stdout=sys.stdout,
			stderr=sys.stderr
		)
		
		# Wait for hypercorn to finish (or be interrupted)
		hypercorn_process.wait()
		
	except KeyboardInterrupt:
		logger.info("Received interrupt signal...")
	except Exception as e:
		logger.error(f"Error starting services: {e}")
		import traceback
		logger.error(traceback.format_exc())
	finally:
		cleanup()

