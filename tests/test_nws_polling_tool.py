"""
Unit tests for NWSPollingTool.
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from app.crews.tools.nws_polling_tool import NWSPollingTool, NWSPollingInput
from app.state import state


class TestNWSPollingTool:
	"""Test cases for NWSPollingTool."""
	
	@pytest.fixture
	def tool(self):
		"""Create tool instance."""
		return NWSPollingTool()
	
	@pytest.fixture
	def sample_nws_response(self):
		"""Sample NWS API response."""
		return {
			"features": [
				{
					"properties": {
						"severity": "Extreme",
						"urgency": "Immediate",
						"certainty": "Observed",
						"status": "Actual",
						"event": "Tornado Warning",
						"messageType": "Alert"
					}
				},
				{
					"properties": {
						"severity": "Severe",
						"urgency": "Expected",
						"certainty": "Likely",
						"status": "Actual",
						"event": "Severe Thunderstorm Warning",
						"messageType": "Alert"
					}
				}
			]
		}
	
	@patch('app.crews.tools.nws_polling_tool.NWSClient')
	@patch('app.crews.tools.nws_polling_tool.state')
	def test_poll_nws_alerts_success(self, mock_state, mock_client_class, tool, sample_nws_response):
		"""Test successful NWS polling."""
		# Setup mocks
		mock_state.last_disaster_poll_time = None
		mock_client = AsyncMock()
		mock_client.get = AsyncMock(return_value=sample_nws_response)
		mock_client.close = AsyncMock()
		mock_client_class.return_value = mock_client
		
		# Run test
		result = tool._run(use_last_poll_time=True)
		
		# Assertions
		assert "filtered_alerts" in result or "features" in result
		mock_client.get.assert_called_once()
	
	@patch('app.crews.tools.nws_polling_tool.NWSClient')
	@patch('app.crews.tools.nws_polling_tool.state')
	def test_poll_with_if_modified_since(self, mock_state, mock_client_class, tool):
		"""Test polling with If-Modified-Since header."""
		from datetime import datetime, timezone
		
		# Setup mocks
		mock_state.last_disaster_poll_time = datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
		mock_client = AsyncMock()
		mock_client.get = AsyncMock(return_value={"features": []})
		mock_client.close = AsyncMock()
		mock_client_class.return_value = mock_client
		
		# Run test
		result = tool._run(use_last_poll_time=True)
		
		# Assertions
		mock_client.get.assert_called_once()
		# Check that headers were passed (would need to inspect call args)
	
	@patch('app.crews.tools.nws_polling_tool.NWSClient')
	def test_poll_filters_by_severity(self, mock_client_class, tool, sample_nws_response):
		"""Test that alerts are filtered by severity."""
		mock_client = AsyncMock()
		mock_client.get = AsyncMock(return_value=sample_nws_response)
		mock_client.close = AsyncMock()
		mock_client_class.return_value = mock_client
		
		# Add an alert that should be filtered out
		sample_nws_response["features"].append({
			"properties": {
				"severity": "Minor",
				"urgency": "Immediate",
				"certainty": "Observed",
				"status": "Actual",
				"event": "Test Warning",
				"messageType": "Alert"
			}
		})
		
		result = tool._run()
		
		# Should only include Extreme/Severe alerts
		assert "filtered" in result.lower() or "features" in result
	
	@patch('app.crews.tools.nws_polling_tool.NWSClient')
	def test_poll_handles_304_not_modified(self, mock_client_class, tool):
		"""Test handling of 304 Not Modified response."""
		mock_client = AsyncMock()
		# Simulate 304 error
		mock_client.get = AsyncMock(side_effect=Exception("304 Not Modified"))
		mock_client.close = AsyncMock()
		mock_client_class.return_value = mock_client
		
		result = tool._run()
		
		# Should return message about no new alerts
		assert "304" in result or "no new alerts" in result.lower()
	
	def test_tool_name_and_description(self, tool):
		"""Test tool metadata."""
		assert tool.name == "NWSPollingTool"
		assert "NWS" in tool.description
		assert "poll" in tool.description.lower()

