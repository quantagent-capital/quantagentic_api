"""
Unit tests for datetime_utils.
"""
import pytest
from unittest.mock import patch
from datetime import datetime, timezone, timedelta
import zoneinfo
from app.utils.datetime_utils import get_last_tuesday_date


class TestGetLastTuesdayDate:
	"""Test cases for get_last_tuesday_date."""
	
	def _get_eastern_datetime(self, year, month, day, hour, minute, second=0):
		"""Helper to create a datetime in Eastern timezone."""
		eastern_tz = zoneinfo.ZoneInfo("America/New_York")
		dt = datetime(year, month, day, hour, minute, second, tzinfo=eastern_tz)
		return dt.astimezone(timezone.utc)
	
	@patch('app.utils.datetime_utils.datetime')
	def test_monday_uses_most_recent_tuesday(self, mock_datetime):
		"""Test that Monday uses the most recent Tuesday."""
		# Monday, January 15, 2024, 10:00 AM Eastern
		mock_now_utc = self._get_eastern_datetime(2024, 1, 15, 10, 0)
		mock_datetime.now.return_value = mock_now_utc
		
		result = get_last_tuesday_date()
		
		# Most recent Tuesday would be January 9, 2024
		assert result == "20240109"
	
	@patch('app.utils.datetime_utils.datetime')
	def test_tuesday_uses_two_tuesdays_ago(self, mock_datetime):
		"""Test that Tuesday always uses two Tuesdays ago."""
		# Tuesday, January 9, 2024, 10:00 AM Eastern
		mock_now_utc = self._get_eastern_datetime(2024, 1, 9, 10, 0)
		mock_datetime.now.return_value = mock_now_utc
		
		result = get_last_tuesday_date()
		
		# Should use two Tuesdays ago: January 2, 2024
		assert result == "20240102"
	
	@patch('app.utils.datetime_utils.datetime')
	def test_tuesday_early_morning_uses_two_tuesdays_ago(self, mock_datetime):
		"""Test that Tuesday early morning still uses two Tuesdays ago."""
		# Tuesday, January 9, 2024, 5:00 AM Eastern
		mock_now_utc = self._get_eastern_datetime(2024, 1, 9, 5, 0)
		mock_datetime.now.return_value = mock_now_utc
		
		result = get_last_tuesday_date()
		
		# Should use two Tuesdays ago: January 2, 2024
		assert result == "20240102"
	
	@patch('app.utils.datetime_utils.datetime')
	def test_wednesday_uses_two_tuesdays_ago(self, mock_datetime):
		"""Test that Wednesday always uses two Tuesdays ago."""
		# Wednesday, January 10, 2024, 10:00 AM Eastern
		mock_now_utc = self._get_eastern_datetime(2024, 1, 10, 10, 0)
		mock_datetime.now.return_value = mock_now_utc
		
		result = get_last_tuesday_date()
		
		# Should use two Tuesdays ago: January 2, 2024
		assert result == "20240102"
	
	@patch('app.utils.datetime_utils.datetime')
	def test_wednesday_early_morning_uses_two_tuesdays_ago(self, mock_datetime):
		"""Test that Wednesday early morning still uses two Tuesdays ago."""
		# Wednesday, January 10, 2024, 5:00 AM Eastern
		mock_now_utc = self._get_eastern_datetime(2024, 1, 10, 5, 0)
		mock_datetime.now.return_value = mock_now_utc
		
		result = get_last_tuesday_date()
		
		# Should use two Tuesdays ago: January 2, 2024
		assert result == "20240102"
	
	@patch('app.utils.datetime_utils.datetime')
	def test_thursday_before_830_am_uses_two_tuesdays_ago(self, mock_datetime):
		"""Test that Thursday before 8:30 AM uses two Tuesdays ago."""
		# Thursday, January 11, 2024, 8:00 AM Eastern
		mock_now_utc = self._get_eastern_datetime(2024, 1, 11, 8, 0)
		mock_datetime.now.return_value = mock_now_utc
		
		result = get_last_tuesday_date()
		
		# Should use two Tuesdays ago: January 2, 2024
		assert result == "20240102"
	
	@patch('app.utils.datetime_utils.datetime')
	def test_thursday_at_829_am_uses_two_tuesdays_ago(self, mock_datetime):
		"""Test that Thursday at 8:29 AM uses two Tuesdays ago."""
		# Thursday, January 11, 2024, 8:29 AM Eastern
		mock_now_utc = self._get_eastern_datetime(2024, 1, 11, 8, 29)
		mock_datetime.now.return_value = mock_now_utc
		
		result = get_last_tuesday_date()
		
		# Should use two Tuesdays ago: January 2, 2024
		assert result == "20240102"
	
	@patch('app.utils.datetime_utils.datetime')
	def test_thursday_at_830_am_uses_most_recent_tuesday(self, mock_datetime):
		"""Test that Thursday at exactly 8:30 AM uses most recent Tuesday."""
		# Thursday, January 11, 2024, 8:30 AM Eastern
		mock_now_utc = self._get_eastern_datetime(2024, 1, 11, 8, 30)
		mock_datetime.now.return_value = mock_now_utc
		
		result = get_last_tuesday_date()
		
		# Should use most recent Tuesday: January 9, 2024
		assert result == "20240109"
	
	@patch('app.utils.datetime_utils.datetime')
	def test_thursday_after_830_am_uses_most_recent_tuesday(self, mock_datetime):
		"""Test that Thursday after 8:30 AM uses most recent Tuesday."""
		# Thursday, January 11, 2024, 9:00 AM Eastern
		mock_now_utc = self._get_eastern_datetime(2024, 1, 11, 9, 0)
		mock_datetime.now.return_value = mock_now_utc
		
		result = get_last_tuesday_date()
		
		# Should use most recent Tuesday: January 9, 2024
		assert result == "20240109"
	
	@patch('app.utils.datetime_utils.datetime')
	def test_friday_uses_most_recent_tuesday(self, mock_datetime):
		"""Test that Friday uses the most recent Tuesday."""
		# Friday, January 12, 2024, 10:00 AM Eastern
		mock_now_utc = self._get_eastern_datetime(2024, 1, 12, 10, 0)
		mock_datetime.now.return_value = mock_now_utc
		
		result = get_last_tuesday_date()
		
		# Most recent Tuesday would be January 9, 2024
		assert result == "20240109"
	
	@patch('app.utils.datetime_utils.datetime')
	def test_saturday_uses_most_recent_tuesday(self, mock_datetime):
		"""Test that Saturday uses the most recent Tuesday."""
		# Saturday, January 13, 2024, 10:00 AM Eastern
		mock_now_utc = self._get_eastern_datetime(2024, 1, 13, 10, 0)
		mock_datetime.now.return_value = mock_now_utc
		
		result = get_last_tuesday_date()
		
		# Most recent Tuesday would be January 9, 2024
		assert result == "20240109"
	
	@patch('app.utils.datetime_utils.datetime')
	def test_sunday_uses_most_recent_tuesday(self, mock_datetime):
		"""Test that Sunday uses the most recent Tuesday."""
		# Sunday, January 14, 2024, 10:00 AM Eastern
		mock_now_utc = self._get_eastern_datetime(2024, 1, 14, 10, 0)
		mock_datetime.now.return_value = mock_now_utc
		
		result = get_last_tuesday_date()
		
		# Most recent Tuesday would be January 9, 2024
		assert result == "20240109"
	
	@patch('app.utils.datetime_utils.datetime')
	def test_cross_month_boundary(self, mock_datetime):
		"""Test behavior when crossing month boundary."""
		# Tuesday, January 2, 2024, 10:00 AM Eastern
		mock_now_utc = self._get_eastern_datetime(2024, 1, 2, 10, 0)
		mock_datetime.now.return_value = mock_now_utc
		
		result = get_last_tuesday_date()
		
		# Should use two Tuesdays ago: December 26, 2023
		assert result == "20231226"
	
	@patch('app.utils.datetime_utils.datetime')
	def test_cross_year_boundary(self, mock_datetime):
		"""Test behavior when crossing year boundary."""
		# Tuesday, January 2, 2024, 10:00 AM Eastern
		mock_now_utc = self._get_eastern_datetime(2024, 1, 2, 10, 0)
		mock_datetime.now.return_value = mock_now_utc
		
		result = get_last_tuesday_date()
		
		# Should use two Tuesdays ago: December 26, 2023
		assert result == "20231226"
	
	@patch('app.utils.datetime_utils.datetime')
	def test_thursday_midnight_uses_two_tuesdays_ago(self, mock_datetime):
		"""Test that Thursday at midnight uses two Tuesdays ago."""
		# Thursday, January 11, 2024, 12:00 AM Eastern
		mock_now_utc = self._get_eastern_datetime(2024, 1, 11, 0, 0)
		mock_datetime.now.return_value = mock_now_utc
		
		result = get_last_tuesday_date()
		
		# Should use two Tuesdays ago: January 2, 2024
		assert result == "20240102"
	
	@patch('app.utils.datetime_utils.datetime')
	def test_thursday_late_night_uses_most_recent_tuesday(self, mock_datetime):
		"""Test that Thursday late at night uses most recent Tuesday."""
		# Thursday, January 11, 2024, 11:59 PM Eastern
		mock_now_utc = self._get_eastern_datetime(2024, 1, 11, 23, 59)
		mock_datetime.now.return_value = mock_now_utc
		
		result = get_last_tuesday_date()
		
		# Should use most recent Tuesday: January 9, 2024
		assert result == "20240109"
