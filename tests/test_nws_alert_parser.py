"""
Unit tests for NWSAlertParser.
"""
import pytest
from unittest.mock import AsyncMock
from datetime import datetime, timezone
from app.utils.nws_alert_parser import NWSAlertParser

class TestExtractPropertiesFromAlert:
	"""Test cases for NWSAlertParser.extract_properties_from_alert."""
	
	def test_extract_properties_from_features_array(self):
		"""Test extracting properties from GeoJSON FeatureCollection format."""
		alert_data = {
			"features": [
				{
					"properties": {
						"id": "test-alert-1",
						"headline": "Test Alert"
					}
				}
			]
		}
		
		result = NWSAlertParser.extract_properties_from_alert(alert_data)
		
		assert result is not None
		assert result["id"] == "test-alert-1"
		assert result["headline"] == "Test Alert"
	
	def test_extract_properties_from_direct_properties(self):
		"""Test extracting properties from direct properties format."""
		alert_data = {
			"properties": {
				"id": "test-alert-2",
				"headline": "Test Alert 2"
			}
		}
		
		result = NWSAlertParser.extract_properties_from_alert(alert_data)
		
		assert result is not None
		assert result["id"] == "test-alert-2"
		assert result["headline"] == "Test Alert 2"
	
	def test_extract_properties_empty_features_array(self):
		"""Test handling empty features array."""
		alert_data = {
			"features": []
		}
		
		result = NWSAlertParser.extract_properties_from_alert(alert_data, "test-id")
		
		assert result is None
	
	def test_extract_properties_missing_properties_in_feature(self):
		"""Test handling feature without properties."""
		alert_data = {
			"features": [
				{
					"geometry": {}
				}
			]
		}
		
		result = NWSAlertParser.extract_properties_from_alert(alert_data, "test-id")
		
		assert result is None
	
	def test_extract_properties_no_features_or_properties(self):
		"""Test handling alert data with neither features nor properties."""
		alert_data = {
			"type": "FeatureCollection"
		}
		
		result = NWSAlertParser.extract_properties_from_alert(alert_data, "test-id")
		
		assert result is None
	
	def test_extract_properties_empty_properties(self):
		"""Test handling empty properties dictionary."""
		alert_data = {
			"properties": {}
		}
		
		result = NWSAlertParser.extract_properties_from_alert(alert_data)
		
		assert result is None




class TestGetMostRecentAlert:
	"""Test cases for NWSAlertParser.get_most_recent_alert."""
	
	@pytest.mark.asyncio
	async def test_get_most_recent_alert_no_replaced_by(self):
		"""Test getting alert when there's no replacedBy property."""
		client = AsyncMock()
		alert_data = {
			"features": [
				{
					"properties": {
						"id": "alert-1",
						"replacedBy": None
					}
				}
			]
		}
		client.get_alert_by_id = AsyncMock(return_value=alert_data)
		
		result = await NWSAlertParser.get_most_recent_alert(client, "alert-1")
		
		assert result == alert_data
		client.get_alert_by_id.assert_called_once_with("alert-1")
	
	@pytest.mark.asyncio
	async def test_get_most_recent_alert_follows_replaced_by(self):
		"""Test following replacedBy link to get most recent alert."""
		client = AsyncMock()
		
		# First alert with replacedBy
		alert_1 = {
			"features": [
				{
					"properties": {
						"id": "alert-1",
						"replacedBy": "https://api.weather.gov/alerts/alert-2"
					}
				}
			]
		}
		
		# Second alert (most recent, no replacedBy)
		alert_2 = {
			"features": [
				{
					"properties": {
						"id": "alert-2",
						"replacedBy": None
					}
				}
			]
		}
		
		client.get_alert_by_id = AsyncMock(side_effect=[alert_1, alert_2])
		
		result = await NWSAlertParser.get_most_recent_alert(client, "alert-1")
		
		assert result == alert_2
		assert client.get_alert_by_id.call_count == 2
		client.get_alert_by_id.assert_any_call("alert-1")
		client.get_alert_by_id.assert_any_call("alert-2")
	
	@pytest.mark.asyncio
	async def test_get_most_recent_alert_multiple_replaced_by(self):
		"""Test following multiple replacedBy links."""
		client = AsyncMock()
		
		alert_1 = {
			"features": [{"properties": {"id": "alert-1", "replacedBy": "https://api.weather.gov/alerts/alert-2"}}]
		}
		alert_2 = {
			"features": [{"properties": {"id": "alert-2", "replacedBy": "https://api.weather.gov/alerts/alert-3"}}]
		}
		alert_3 = {
			"features": [{"properties": {"id": "alert-3", "replacedBy": None}}]
		}
		
		client.get_alert_by_id = AsyncMock(side_effect=[alert_1, alert_2, alert_3])
		
		result = await NWSAlertParser.get_most_recent_alert(client, "alert-1")
		
		assert result == alert_3
		assert client.get_alert_by_id.call_count == 3
	
	@pytest.mark.asyncio
	async def test_get_most_recent_alert_handles_url_with_query_params(self):
		"""Test handling replacedBy URL with query parameters."""
		client = AsyncMock()
		
		alert_1 = {
			"features": [{"properties": {"id": "alert-1", "replacedBy": "https://api.weather.gov/alerts/alert-2?param=value"}}]
		}
		alert_2 = {
			"features": [{"properties": {"id": "alert-2", "replacedBy": None}}]
		}
		
		client.get_alert_by_id = AsyncMock(side_effect=[alert_1, alert_2])
		
		result = await NWSAlertParser.get_most_recent_alert(client, "alert-1")
		
		assert result == alert_2
		client.get_alert_by_id.assert_any_call("alert-2")
	
	@pytest.mark.asyncio
	async def test_get_most_recent_alert_max_iterations(self):
		"""Test that max iterations prevents infinite loops."""
		client = AsyncMock()
		
		# Create a chain that exceeds max iterations
		alert_with_replaced_by = {
			"features": [{"properties": {"id": "alert-1", "replacedBy": "https://api.weather.gov/alerts/alert-2"}}]
		}
		
		client.get_alert_by_id = AsyncMock(return_value=alert_with_replaced_by)
		
		result = await NWSAlertParser.get_most_recent_alert(client, "alert-1")
		
		# Should return the last alert after max iterations
		assert result == alert_with_replaced_by
		assert client.get_alert_by_id.call_count == 10
	
	@pytest.mark.asyncio
	async def test_get_most_recent_alert_handles_exception(self):
		"""Test handling exceptions when fetching alerts."""
		client = AsyncMock()
		client.get_alert_by_id = AsyncMock(side_effect=Exception("API Error"))
		
		result = await NWSAlertParser.get_most_recent_alert(client, "alert-1")
		
		assert result is None
	
	@pytest.mark.asyncio
	async def test_get_most_recent_alert_unexpected_replaced_by_format(self):
		"""Test handling unexpected replacedBy format."""
		client = AsyncMock()
		
		alert_data = {
			"features": [
				{
					"properties": {
						"id": "alert-1",
						"replacedBy": "invalid-format"
					}
				}
			]
		}
		
		client.get_alert_by_id = AsyncMock(return_value=alert_data)
		
		result = await NWSAlertParser.get_most_recent_alert(client, "alert-1")
		
		# Should return the alert data even with invalid replacedBy format
		assert result == alert_data




class TestExtractActualEndTime:
	"""Test cases for NWSAlertParser.extract_actual_end_time."""
	
	def test_extract_actual_end_time_from_event_ending_time(self):
		"""Test extracting end time from eventEndingTime parameter."""
		alert_data = {
			"features": [
				{
					"properties": {
						"parameters": {
							"eventEndingTime": ["2024-01-15T12:00:00-06:00"]
						}
					}
				}
			]
		}
		
		result = NWSAlertParser.extract_actual_end_time(alert_data)
		
		assert result is not None
		assert result.year == 2024
		assert result.month == 1
		assert result.day == 15
	
	def test_extract_actual_end_time_fallback_to_ends(self):
		"""Test fallback to ends property when eventEndingTime is missing."""
		alert_data = {
			"features": [
				{
					"properties": {
						"ends": "2024-01-15T11:00:00-06:00"
					}
				}
			]
		}
		
		result = NWSAlertParser.extract_actual_end_time(alert_data)
		
		assert result is not None
		assert result.year == 2024
	
	def test_extract_actual_end_time_fallback_to_expires(self):
		"""Test fallback to expires property when eventEndingTime and ends are missing."""
		alert_data = {
			"features": [
				{
					"properties": {
						"expires": "2024-01-15T13:00:00-06:00"
					}
				}
			]
		}
		
		result = NWSAlertParser.extract_actual_end_time(alert_data)
		
		assert result is not None
		assert result.year == 2024
	
	def test_extract_actual_end_time_fallback_to_current_time(self):
		"""Test fallback to current time when all other options are missing."""
		alert_data = {
			"features": [
				{
					"properties": {}
				}
			]
		}
		
		before = datetime.now(timezone.utc)
		result = NWSAlertParser.extract_actual_end_time(alert_data)
		after = datetime.now(timezone.utc)
		
		assert result is not None
		assert before <= result <= after
	
	def test_extract_actual_end_time_empty_event_ending_time_list(self):
		"""Test handling empty eventEndingTime list."""
		alert_data = {
			"features": [
				{
					"properties": {
						"parameters": {
							"eventEndingTime": []
						},
						"ends": "2024-01-15T11:00:00-06:00"
					}
				}
			]
		}
		
		result = NWSAlertParser.extract_actual_end_time(alert_data)
		
		# Should fallback to ends
		assert result is not None
		assert result.year == 2024
	
	def test_extract_actual_end_time_invalid_properties(self):
		"""Test handling alert data with invalid properties structure."""
		alert_data = {
			"invalid": "structure"
		}
		
		before = datetime.now(timezone.utc)
		result = NWSAlertParser.extract_actual_end_time(alert_data)
		after = datetime.now(timezone.utc)
		
		# Should fallback to current time
		assert result is not None
		assert before <= result <= after


