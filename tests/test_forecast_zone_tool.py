"""
Unit tests for GetForecastZoneTool.
"""
import pytest
from unittest.mock import AsyncMock, patch
from app.crews.tools.forecast_zone_tool import GetForecastZoneTool


class TestGetForecastZoneTool:
	"""Test cases for GetForecastZoneTool."""
	
	@pytest.fixture
	def tool(self):
		"""Create tool instance."""
		return GetForecastZoneTool()
	
	@pytest.fixture
	def sample_zone_response(self):
		"""Sample forecast zone API response."""
		return {
			"id": "https://api.weather.gov/zones/forecast/PKZ413",
			"type": "Feature",
			"geometry": {
				"type": "Polygon",
				"coordinates": [[
					[-177.9968616, 53.095572],
					[-179.9999434, 53.2009532],
					[-180, 56.0445412],
					[-170.9990433, 56.0445412],
					[-177.9968616, 53.095572]
				]]
			},
			"properties": {
				"id": "PKZ413",
				"name": "Bering Sea Offshore 171W to 180 and South of 56N"
			}
		}
	
	@patch('app.crews.tools.forecast_zone_tool.NWSClient')
	def test_get_forecast_zone_success(self, mock_client_class, tool, sample_zone_response):
		"""Test successful forecast zone retrieval."""
		mock_client = AsyncMock()
		mock_client.get = AsyncMock(return_value=sample_zone_response)
		mock_client.close = AsyncMock()
		mock_client_class.return_value = mock_client
		
		zone_url = "https://api.weather.gov/zones/forecast/PKZ413"
		result = tool._run(zone_url)
		
		assert "coordinates" in result
		assert "PKZ413" in result
	
	@patch('app.crews.tools.forecast_zone_tool.NWSClient')
	def test_get_forecast_zone_with_path_only(self, mock_client_class, tool, sample_zone_response):
		"""Test getting zone with path only (no full URL)."""
		mock_client = AsyncMock()
		mock_client.get = AsyncMock(return_value=sample_zone_response)
		mock_client.close = AsyncMock()
		mock_client_class.return_value = mock_client
		
		zone_path = "/zones/forecast/PKZ413"
		result = tool._run(zone_path)
		
		assert "coordinates" in result
	
	@patch('app.crews.tools.forecast_zone_tool.NWSClient')
	def test_get_forecast_zone_error_handling(self, mock_client_class, tool):
		"""Test error handling."""
		mock_client = AsyncMock()
		mock_client.get = AsyncMock(side_effect=Exception("API Error"))
		mock_client.close = AsyncMock()
		mock_client_class.return_value = mock_client
		
		result = tool._run("https://api.weather.gov/zones/forecast/INVALID")
		
		assert "Error" in result
	
	def test_tool_name_and_description(self, tool):
		"""Test tool metadata."""
		assert tool.name == "GetForecastZoneTool"
		assert "forecast zone" in tool.description.lower()

