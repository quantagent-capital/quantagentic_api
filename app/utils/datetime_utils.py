"""
Datetime utility functions.
"""
from typing import Optional
from datetime import datetime, timezone, timedelta, time
import logging
import zoneinfo

logger = logging.getLogger(__name__)


def parse_timestamp_ms(timestamp_ms: Optional[int]) -> Optional[datetime]:
	"""
	Convert milliseconds timestamp to datetime.
	
	Args:
		timestamp_ms: Timestamp in milliseconds
	
	Returns:
		datetime object in UTC, or None if timestamp is None
	"""
	if timestamp_ms is None:
		return None
	return datetime.fromtimestamp(timestamp_ms / 1000.0, tz=timezone.utc)


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


def get_last_tuesday_date() -> str:
	"""
	Get the date string (YYYYMMDD) for the most recent Tuesday.
	Drought Monitor data is published on Tuesdays.
	
	Special case: If today is Tuesday, Wednesday, or Thursday before 8:30 AM Eastern,
	we should use the data from two Tuesdays ago instead of the most recent Tuesday.

	This is because the drought monitor data is published on Thursdays, _for the previous Tuesday to Tuesday_.
	
	Returns:
		Date string in YYYYMMDD format
	"""
	# Get current time in UTC and convert to Eastern timezone
	now_utc = datetime.now(timezone.utc)
	eastern_tz = zoneinfo.ZoneInfo("America/New_York")
	now_eastern = now_utc.astimezone(eastern_tz)
	
	# Check if we need to use two Tuesdays ago
	# Tuesday = 1, Wednesday = 2, Thursday = 3
	weekday = now_eastern.weekday()
	is_tue_wed_thu = weekday in [1, 2, 3]
	is_before_830_am = now_eastern.time() < time(8, 30)
	
	# Calculate days since most recent Tuesday
	days_since_tuesday = (weekday - 1 + 7) % 7
	last_tuesday = now_eastern - timedelta(days=days_since_tuesday)
	
	# If it's Tuesday/Wednesday/Thursday before 8:30 AM Eastern, use two Tuesdays ago
	if is_tue_wed_thu and is_before_830_am:
		last_tuesday = last_tuesday - timedelta(days=7)
	
	return last_tuesday.strftime("%Y%m%d")