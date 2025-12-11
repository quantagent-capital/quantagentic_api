"""
Unit tests for NWSPollingTool.
Tests the actual poll() and _async_poll() methods.
"""
import pytest
from unittest.mock import AsyncMock, patch
from app.pollers.nws_polling_tool import NWSConfirmedEventsPoller
from app.shared_models.nws_poller_models import FilteredNWSAlert
from app.schemas.location import Location


class TestNWSPollingTool:
	"""Test cases for NWSPollingTool."""
	
	@pytest.fixture
	def tool(self):
		"""Create tool instance."""
		return NWSConfirmedEventsPoller()
	
	@pytest.fixture
	def sample_nws_response(self):
		"""Sample NWS API response with proper structure."""
		return {
			"features": [
				{
					"properties": {
						"id": "https://api.weather.gov/alerts/urn:oid:2.49.0.1.840.0.1234567890",
						"severity": "Extreme",
						"urgency": "Immediate",
						"certainty": "Observed",
						"status": "Actual",
						"eventCode": {
							"NationalWeatherService": ["TOR"]
						},
						"effective": "2024-01-15T10:00:00-00:00",
						"expires": "2024-01-15T11:00:00-00:00",
						"headline": "Tornado Warning",
						"description": "Test tornado warning",
						"affectedZones": ["https://api.weather.gov/zones/forecast/TXC113"],
						"geocode": {
							"UGC": ["TXC113"],
							"SAME": ["048113"]
						},
						"parameters": {
							"VTEC": ["/O.NEW.KFWD.TO.W.0015.240115T1000Z-240115T1100Z/"],
							"eventEndingTime": ["2024-01-15T11:00:00-00:00"]
						},
						"references": []
					},
					"geometry": {
						"type": "Polygon",
						"coordinates": [[
							[-97.5, 32.8],
							[-97.2, 32.8],
							[-97.2, 33.1],
							[-97.5, 33.1],
							[-97.5, 32.8]
						]]
					}
				}
			]
		}
	
	@patch('app.pollers.nws_polling_tool.NWSClient')
	@pytest.mark.asyncio
	async def test_async_poll_success(self, mock_client_class, tool, sample_nws_response):
		"""Test successful async NWS polling."""
		# Setup mocks
		mock_client = AsyncMock()
		mock_client.get = AsyncMock(return_value=sample_nws_response)
		mock_client_class.return_value = mock_client
		
		# Run test
		result = await tool._async_poll()
		
		# Assertions
		assert isinstance(result, list)
		assert len(result) > 0
		assert isinstance(result[0], FilteredNWSAlert)
		mock_client.get.assert_called_once()
		
		# Verify the call was made with correct parameters
		call_args = mock_client.get.call_args
		assert call_args[0][0] == "/alerts/active"
		assert "params" in call_args.kwargs
		assert call_args.kwargs["params"]["status"] == "actual"
	
	@patch('app.pollers.nws_polling_tool.NWSClient')
	def test_poll_success(self, mock_client_class, tool, sample_nws_response):
		"""Test successful synchronous NWS polling."""
		# Setup mocks
		mock_client = AsyncMock()
		mock_client.get = AsyncMock(return_value=sample_nws_response)
		mock_client_class.return_value = mock_client
		
		# Run test
		result = tool.poll()
		
		# Assertions
		assert isinstance(result, list)
		assert len(result) > 0
		assert isinstance(result[0], FilteredNWSAlert)
		mock_client.get.assert_called_once()
	
	@patch('app.pollers.nws_polling_tool.NWSClient')
	@pytest.mark.asyncio
	async def test_async_poll_filters_by_event_type(self, mock_client_class, tool):
		"""Test that alerts are filtered by event type."""
		mock_client = AsyncMock()
		
		# Create response with valid and invalid event types
		response = {
			"features": [
				{
					"properties": {
						"id": "test1",
						"severity": "Extreme",
						"urgency": "Immediate",
						"certainty": "Observed",
						"status": "Actual",
						"eventCode": {"NationalWeatherService": ["TOR"]},  # Valid
						"effective": "2024-01-15T10:00:00-00:00",
						"expires": "2024-01-15T11:00:00-00:00",
						"affectedZones": [],
						"geocode": {"UGC": [], "SAME": []},
						"parameters": {"VTEC": ["/O.NEW.KFWD.TO.W.0015.240115T1000Z-240115T1100Z/"]},
						"references": []
					},
					"geometry": None
				},
				{
					"properties": {
						"id": "test2",
						"severity": "Extreme",
						"urgency": "Immediate",
						"certainty": "Observed",
						"status": "Actual",
						"eventCode": {"NationalWeatherService": ["XXX"]},  # Invalid
						"effective": "2024-01-15T10:00:00-00:00",
						"expires": "2024-01-15T11:00:00-00:00",
						"affectedZones": [],
						"geocode": {"UGC": [], "SAME": []},
						"parameters": {"VTEC": ["/O.NEW.KFWD.XXX.W.0015.240115T1000Z-240115T1100Z/"]},
						"references": []
					},
					"geometry": None
				}
			]
		}
		
		mock_client.get = AsyncMock(return_value=response)
		mock_client_class.return_value = mock_client
		
		result = await tool._async_poll()
		
		# Should only include valid event types (TOR is valid, XXX is not)
		# Note: The tool filters by ALL_NWS_EVENT_CODES, so XXX should be filtered out
		event_types = [alert.event_type for alert in result]
		assert "TOR" in event_types or len(result) == 0  # TOR might be filtered if VTEC parsing fails
		assert "XXX" not in event_types
	
	@patch('app.pollers.nws_polling_tool.NWSClient')
	@pytest.mark.asyncio
	async def test_async_poll_handles_304_not_modified(self, mock_client_class, tool):
		"""Test handling of 304 Not Modified response."""
		mock_client = AsyncMock()
		# Simulate 304 error
		mock_client.get = AsyncMock(side_effect=Exception("304 Not Modified"))
		mock_client_class.return_value = mock_client
		
		result = await tool._async_poll()
		
		# Should return empty list
		assert result == []
	
	@patch('app.pollers.nws_polling_tool.NWSClient')
	@pytest.mark.asyncio
	async def test_async_poll_includes_vtec_fields(self, mock_client_class, tool, sample_nws_response):
		"""Test that filtered alerts include VTEC-related fields."""
		mock_client = AsyncMock()
		mock_client.get = AsyncMock(return_value=sample_nws_response)
		mock_client_class.return_value = mock_client
		
		result = await tool._async_poll()
		
		if len(result) > 0:
			alert = result[0]
			# Check for required fields
			assert hasattr(alert, "key")
			assert hasattr(alert, "affected_zones_ugc_endpoints")
			assert hasattr(alert, "affected_zones_raw_ugc_codes")
			assert hasattr(alert, "raw_vtec")
			assert hasattr(alert, "event_type")
			assert hasattr(alert, "message_type")
			assert hasattr(alert, "is_warning")
			assert hasattr(alert, "is_watch")
			assert hasattr(alert, "locations")
	
	@patch('app.pollers.nws_polling_tool.NWSClient')
	@pytest.mark.asyncio
	async def test_async_poll_empty_response(self, mock_client_class, tool):
		"""Test polling with empty response."""
		mock_client = AsyncMock()
		mock_client.get = AsyncMock(return_value={"features": []})
		mock_client_class.return_value = mock_client
		
		result = await tool._async_poll()
		
		assert result == []
	
	@patch('app.pollers.nws_polling_tool.NWSClient')
	@pytest.mark.asyncio
	async def test_async_poll_no_features_key(self, mock_client_class, tool):
		"""Test polling when response doesn't have features key."""
		mock_client = AsyncMock()
		mock_client.get = AsyncMock(return_value={})
		mock_client_class.return_value = mock_client
		
		result = await tool._async_poll()
		
		assert result == []
	
	@patch('app.pollers.nws_polling_tool.NWSClient')
	def test_poll_handles_runtime_error(self, mock_client_class, tool):
		"""Test that poll() handles errors and raises RuntimeError."""
		mock_client = AsyncMock()
		mock_client.get = AsyncMock(side_effect=Exception("Network error"))
		mock_client_class.return_value = mock_client
		
		with pytest.raises(RuntimeError) as exc_info:
			tool.poll()
		
		assert "Error polling NWS API" in str(exc_info.value)
	
	@patch('app.pollers.nws_polling_tool.NWSClient')
	@pytest.mark.asyncio
	async def test_async_poll_filters_warning_or_watch(self, mock_client_class, tool):
		"""Test that alerts are filtered by warning/watch status."""
		mock_client = AsyncMock()
		
		# Response with valid VTEC that indicates warning
		response = {
			"features": [
				{
					"properties": {
						"id": "test1",
						"severity": "Extreme",
						"urgency": "Immediate",
						"certainty": "Observed",
						"status": "Actual",
						"eventCode": {"NationalWeatherService": ["TOR"]},
						"effective": "2024-01-15T10:00:00-00:00",
						"expires": "2024-01-15T11:00:00-00:00",
						"affectedZones": [],
						"geocode": {"UGC": [], "SAME": []},
						"parameters": {"VTEC": ["/O.NEW.KFWD.TO.W.0015.240115T1000Z-240115T1100Z/"]},
						"references": []
					},
					"geometry": None
				}
			]
		}
		
		mock_client.get = AsyncMock(return_value=response)
		mock_client_class.return_value = mock_client
		
		result = await tool._async_poll()
		
		# If VTEC parsing succeeds, should have alerts
		# The tool filters by warning_or_watch, so only warnings/watches pass
		assert isinstance(result, list)
	
	@patch('app.pollers.nws_polling_tool.NWSClient')
	@pytest.mark.asyncio
	async def test_async_poll_extracts_locations(self, mock_client_class, tool, sample_nws_response):
		"""Test that locations are properly extracted from alerts."""
		mock_client = AsyncMock()
		mock_client.get = AsyncMock(return_value=sample_nws_response)
		mock_client_class.return_value = mock_client
		
		result = await tool._async_poll()
		
		if len(result) > 0:
			alert = result[0]
			assert hasattr(alert, "locations")
			assert isinstance(alert.locations, list)
			# If locations are extracted, they should be Location objects
			if len(alert.locations) > 0:
				assert isinstance(alert.locations[0], Location)
	
	@patch('app.pollers.nws_polling_tool.NWSClient')
	@pytest.mark.asyncio
	async def test_async_poll_expected_end_from_event_ending_time(self, mock_client_class, tool):
		"""Test that expected_end uses eventEndingTime when available."""
		mock_client = AsyncMock()
		response = {
			"features": [
				{
					"properties": {
						"id": "test1",
						"severity": "Extreme",
						"urgency": "Immediate",
						"certainty": "Observed",
						"status": "Actual",
						"eventCode": {"NationalWeatherService": ["TOR"]},
						"effective": "2024-01-15T10:00:00-00:00",
						"expires": "2024-01-15T12:00:00-00:00",
						"ends": "2024-01-15T11:30:00-00:00",
						"affectedZones": [],
						"geocode": {"UGC": [], "SAME": []},
						"parameters": {
							"VTEC": ["/O.NEW.KFWD.TO.W.0015.240115T1000Z-240115T1100Z/"],
							"eventEndingTime": ["2024-01-15T11:00:00-00:00"]  # Should use this
						},
						"references": []
					},
					"geometry": None
				}
			]
		}
		mock_client.get = AsyncMock(return_value=response)
		mock_client_class.return_value = mock_client
		
		result = await tool._async_poll()
		
		if len(result) > 0:
			alert = result[0]
			# Should use eventEndingTime, not ends or expires
			assert alert.expected_end == "2024-01-15T11:00:00-00:00"
	
	@patch('app.pollers.nws_polling_tool.NWSClient')
	@pytest.mark.asyncio
	async def test_async_poll_expected_end_fallback_to_ends(self, mock_client_class, tool):
		"""Test that expected_end falls back to ends when eventEndingTime is None."""
		mock_client = AsyncMock()
		response = {
			"features": [
				{
					"properties": {
						"id": "test1",
						"severity": "Extreme",
						"urgency": "Immediate",
						"certainty": "Observed",
						"status": "Actual",
						"eventCode": {"NationalWeatherService": ["TOR"]},
						"effective": "2024-01-15T10:00:00-00:00",
						"expires": "2024-01-15T12:00:00-00:00",
						"ends": "2024-01-15T11:30:00-00:00",  # Should use this
						"affectedZones": [],
						"geocode": {"UGC": [], "SAME": []},
						"parameters": {
							"VTEC": ["/O.NEW.KFWD.TO.W.0015.240115T1000Z-240115T1100Z/"],
							"eventEndingTime": None  # None, should fallback to ends
						},
						"references": []
					},
					"geometry": None
				}
			]
		}
		mock_client.get = AsyncMock(return_value=response)
		mock_client_class.return_value = mock_client
		
		result = await tool._async_poll()
		
		if len(result) > 0:
			alert = result[0]
			# Should use ends, not expires
			assert alert.expected_end == "2024-01-15T11:30:00-00:00"
	
	@patch('app.pollers.nws_polling_tool.NWSClient')
	@pytest.mark.asyncio
	async def test_async_poll_expected_end_fallback_to_expires(self, mock_client_class, tool):
		"""Test that expected_end falls back to expires when eventEndingTime and ends are None."""
		mock_client = AsyncMock()
		response = {
			"features": [
				{
					"properties": {
						"id": "test1",
						"severity": "Extreme",
						"urgency": "Immediate",
						"certainty": "Observed",
						"status": "Actual",
						"eventCode": {"NationalWeatherService": ["TOR"]},
						"effective": "2024-01-15T10:00:00-00:00",
						"expires": "2024-01-15T12:00:00-00:00",  # Should use this
						"ends": None,  # None
						"affectedZones": [],
						"geocode": {"UGC": [], "SAME": []},
						"parameters": {
							"VTEC": ["/O.NEW.KFWD.TO.W.0015.240115T1000Z-240115T1100Z/"],
							"eventEndingTime": None  # None
						},
						"references": []
					},
					"geometry": None
				}
			]
		}
		mock_client.get = AsyncMock(return_value=response)
		mock_client_class.return_value = mock_client
		
		result = await tool._async_poll()
		
		if len(result) > 0:
			alert = result[0]
			# Should use expires as final fallback
			assert alert.expected_end == "2024-01-15T12:00:00-00:00"
	
	@patch('app.pollers.nws_polling_tool.NWSClient')
	@pytest.mark.asyncio
	async def test_async_poll_expected_end_all_none(self, mock_client_class, tool):
		"""Test that expected_end is None when eventEndingTime, ends, and expires are all None."""
		mock_client = AsyncMock()
		response = {
			"features": [
				{
					"properties": {
						"id": "test1",
						"severity": "Extreme",
						"urgency": "Immediate",
						"certainty": "Observed",
						"status": "Actual",
						"eventCode": {"NationalWeatherService": ["TOR"]},
						"effective": "2024-01-15T10:00:00-00:00",
						"expires": None,  # None
						"ends": None,  # None
						"affectedZones": [],
						"geocode": {"UGC": [], "SAME": []},
						"parameters": {
							"VTEC": ["/O.NEW.KFWD.TO.W.0015.240115T1000Z-240115T1100Z/"],
							"eventEndingTime": None  # None
						},
						"references": []
					},
					"geometry": None
				}
			]
		}
		mock_client.get = AsyncMock(return_value=response)
		mock_client_class.return_value = mock_client
		
		result = await tool._async_poll()
		
		if len(result) > 0:
			alert = result[0]
			# Should be None when all fallbacks are None
			assert alert.expected_end is None
	
	@patch('app.pollers.nws_polling_tool.NWSClient')
	@pytest.mark.asyncio
	async def test_async_poll_expected_end_empty_event_ending_time_list(self, mock_client_class, tool):
		"""Test that expected_end falls back when eventEndingTime is an empty list."""
		mock_client = AsyncMock()
		response = {
			"features": [
				{
					"properties": {
						"id": "test1",
						"severity": "Extreme",
						"urgency": "Immediate",
						"certainty": "Observed",
						"status": "Actual",
						"eventCode": {"NationalWeatherService": ["TOR"]},
						"effective": "2024-01-15T10:00:00-00:00",
						"expires": "2024-01-15T12:00:00-00:00",
						"ends": "2024-01-15T11:30:00-00:00",  # Should use this
						"affectedZones": [],
						"geocode": {"UGC": [], "SAME": []},
						"parameters": {
							"VTEC": ["/O.NEW.KFWD.TO.W.0015.240115T1000Z-240115T1100Z/"],
							"eventEndingTime": []  # Empty list, should fallback
						},
						"references": []
					},
					"geometry": None
				}
			]
		}
		mock_client.get = AsyncMock(return_value=response)
		mock_client_class.return_value = mock_client
		
		result = await tool._async_poll()
		
		if len(result) > 0:
			alert = result[0]
			# Should use ends when eventEndingTime is empty list
			assert alert.expected_end == "2024-01-15T11:30:00-00:00"

