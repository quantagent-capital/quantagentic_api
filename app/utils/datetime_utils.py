"""
Datetime utility functions.
"""
from typing import Optional
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


def parse_datetime_to_utc(dt_string: Optional[str]) -> Optional[datetime]:
	"""
	Parse a datetime string to a datetime object in UTC.
	
	Handles formats like:
	- 2025-12-09T04:45:00-08:00 (with timezone offset)
	- 2025-12-09T04:45:00Z (Zulu/UTC)
	- 2025-12-09T04:45:00+00:00 (explicit UTC)
	
	Args:
		dt_string: ISO format datetime string or None
		
	Returns:
		datetime object in UTC timezone or None
	"""
	if dt_string is None:
		return None
	try:
		# Handle 'Z' timezone indicator (Zulu/UTC)
		if dt_string.endswith('Z'):
			dt_string = dt_string.replace('Z', '+00:00')
		
		# Parse the datetime string
		dt = datetime.fromisoformat(dt_string)
		
		# Convert to UTC if timezone-aware, otherwise assume UTC
		if dt.tzinfo is not None:
			dt = dt.astimezone(timezone.utc)
		else:
			# If no timezone info, assume it's already in UTC
			dt = dt.replace(tzinfo=timezone.utc)
		
		return dt
	except (ValueError, AttributeError) as e:
		logger.warning(f"Failed to parse datetime string '{dt_string}': {str(e)}")
		return None
