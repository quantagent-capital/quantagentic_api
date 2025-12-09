"""
Structured JSON logging configuration for Railway deployment.
Outputs to stdout so Railway can properly categorize log levels.
"""
import json
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict


class JSONFormatter(logging.Formatter):
	"""
	Custom formatter that outputs logs as JSON.
	Railway supports structured JSON logging and will properly color code log levels.
	"""
	
	def format(self, record: logging.LogRecord) -> str:
		"""Format log record as JSON."""
		log_data: Dict[str, Any] = {
			"timestamp": datetime.utcnow().isoformat() + "Z",
			"level": record.levelname,
			"logger": record.name,
			"message": record.getMessage(),
		}
		
		# Add exception info if present
		if record.exc_info:
			log_data["exception"] = self.formatException(record.exc_info)
		
		# Add extra fields if present
		if hasattr(record, "extra_fields"):
			log_data.update(record.extra_fields)
		
		# Add module and function info for debugging
		if record.module:
			log_data["module"] = record.module
		if record.funcName:
			log_data["function"] = record.funcName
		if record.lineno:
			log_data["line"] = record.lineno
		
		return json.dumps(log_data)


def setup_logging(level: str = "INFO") -> None:
	"""
	Configure application-wide logging to use structured JSON output to stdout.
	
	Args:
		level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
	
	Note:
		If PYTHONDEBUG is set, this function will skip setup to allow
		debug mode logging configuration to take precedence (e.g., in railway_local.py).
	"""
	# Check if we're in debug mode - if so, skip setup to preserve debug logging config
	is_debug_mode = os.getenv("PYTHONDEBUG", "").lower() in ("1", "true")
	if is_debug_mode:
		# In debug mode, assume logging is already configured (e.g., by railway_local.py)
		# Just ensure app loggers are set to appropriate levels
		logging.getLogger("app").setLevel(getattr(logging, level.upper(), logging.INFO))
		return
	
	# Get the root logger
	root_logger = logging.getLogger()
	root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))
	
	# Remove any existing handlers
	root_logger.handlers.clear()
	
	# Create a handler that outputs to stdout (not stderr)
	# This is crucial - Railway treats stderr as errors, stdout as normal logs
	stdout_handler = logging.StreamHandler(sys.stdout)
	stdout_handler.setLevel(getattr(logging, level.upper(), logging.INFO))
	
	# Use JSON formatter
	json_formatter = JSONFormatter()
	stdout_handler.setFormatter(json_formatter)
	
	# Add handler to root logger
	root_logger.addHandler(stdout_handler)
	
	# Configure third-party loggers to use our setup
	# Set level for noisy libraries
	logging.getLogger("httpx").setLevel(logging.WARNING)
	logging.getLogger("httpcore").setLevel(logging.WARNING)
	logging.getLogger("urllib3").setLevel(logging.WARNING)
	
	# Celery logging
	logging.getLogger("celery").setLevel(logging.INFO)
	logging.getLogger("celery.beat").setLevel(logging.INFO)
	
	# CrewAI/Langchain logging
	logging.getLogger("langchain").setLevel(logging.WARNING)
	logging.getLogger("langsmith").setLevel(logging.WARNING)
	logging.getLogger("crewai").setLevel(logging.INFO)


def get_logger(name: str) -> logging.Logger:
	"""
	Get a logger instance with the given name.
	
	Args:
		name: Logger name (typically __name__)
		
	Returns:
		Logger instance
	"""
	return logging.getLogger(name)

