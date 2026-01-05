"""
Tests for ConfirmEventLocationTool.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
from app.crews.event_confirmation_crew.tools.event_confirmation_tool import ConfirmEventLocationTool
from app.crews.event_confirmation_crew.models import EventConfirmationOutput
from app.schemas.event import Event
from app.schemas.location import Location, Coordinate
from shapely.geometry import Point, Polygon


class TestConfirmEventLocationTool:
	"""Test suite for ConfirmEventLocationTool."""
	
	@pytest.fixture
	def tool(self):
		"""Create a tool instance."""
		return ConfirmEventLocationTool()
	
	@pytest.fixture
	def sample_event(self):
		"""Create a sample event with locations."""
		return Event(
			event_key="TEST-KEY-001",
			nws_alert_id="alert-1",
			event_type="TOR",
			start_date=datetime.now(timezone.utc),
			description="Test tornado warning",
			is_active=True,
			confirmed=False,
			raw_vtec="/O.NEW.TEST.TO.W.0015.240115T1000Z/",
			office="KTEST",
			locations=[
				Location(
					event_key="TEST-KEY-001",
					state_fips="48",
					county_fips="113",
					ugc_code="TXC113",
					full_zone_ugc_endpoint="https://api.weather.gov/zones/forecast/TXC113",
					full_shape=[[
						Coordinate(latitude=32.8, longitude=-97.5),
						Coordinate(latitude=32.9, longitude=-97.5),
						Coordinate(latitude=32.9, longitude=-97.4),
						Coordinate(latitude=32.8, longitude=-97.4),
						Coordinate(latitude=32.8, longitude=-97.5)  # Closed polygon
					]]
				),
				Location(
					event_key="TEST-KEY-001",
					state_fips="48",
					county_fips="115",
					ugc_code="TXC115",
					full_zone_ugc_endpoint="https://api.weather.gov/zones/forecast/TXC115",
					full_shape=[[
						Coordinate(latitude=33.0, longitude=-97.0),
						Coordinate(latitude=33.1, longitude=-97.0),
						Coordinate(latitude=33.1, longitude=-96.9),
						Coordinate(latitude=33.0, longitude=-96.9),
						Coordinate(latitude=33.0, longitude=-97.0)  # Closed polygon
					]]
				)
			]
		)
	
	@pytest.fixture
	def mock_state(self):
		"""Mock state object."""
		with patch('app.crews.event_confirmation_crew.tools.event_confirmation_tool.state') as mock_state:
			yield mock_state
	
	def test_event_not_found(self, tool, mock_state):
		"""Test that missing event returns not confirmed."""
		mock_state.get_event.return_value = None
		
		result = tool._run("NONEXISTENT-KEY", 32.8, -97.5)
		
		assert result.confirmed is False
		assert result.observed_coordinate is None
		assert result.location_index is None
	
	def test_invalid_coordinates_none(self, tool, mock_state, sample_event):
		"""Test that None coordinates return not confirmed."""
		mock_state.get_event.return_value = sample_event
		
		result = tool._run("TEST-KEY-001", None, -97.5)
		
		assert result.confirmed is False
		assert result.observed_coordinate is None
		assert result.location_index is None
	
	def test_invalid_coordinates_zero(self, tool, mock_state, sample_event):
		"""Test that (0.0, 0.0) coordinates return not confirmed."""
		mock_state.get_event.return_value = sample_event
		
		result = tool._run("TEST-KEY-001", 0.0, 0.0)
		
		assert result.confirmed is False
		assert result.observed_coordinate is None
		assert result.location_index is None
	
	def test_invalid_coordinate_ranges(self, tool, mock_state, sample_event):
		"""Test that out-of-range coordinates return not confirmed."""
		mock_state.get_event.return_value = sample_event
		
		# Latitude out of range
		result = tool._run("TEST-KEY-001", 91.0, -97.5)
		assert result.confirmed is False
		
		# Longitude out of range
		result = tool._run("TEST-KEY-001", 32.8, -181.0)
		assert result.confirmed is False
	
	def test_coordinate_found_in_first_location(self, tool, mock_state, sample_event):
		"""Test that coordinate found in first location returns confirmed with index 0."""
		mock_state.get_event.return_value = sample_event
		
		# Coordinate inside first polygon (32.85, -97.45)
		result = tool._run("TEST-KEY-001", 32.85, 97.45)  # Positive longitude should be negated
		
		assert result.confirmed is True
		assert result.observed_coordinate is not None
		assert result.observed_coordinate.latitude == 32.85
		assert result.observed_coordinate.longitude == -97.45  # Should be negated
		assert result.location_index == 0
	
	def test_coordinate_found_in_second_location(self, tool, mock_state, sample_event):
		"""Test that coordinate found in second location returns confirmed with index 1."""
		mock_state.get_event.return_value = sample_event
		
		# Coordinate inside second polygon (33.05, -96.95)
		result = tool._run("TEST-KEY-001", 33.05, 96.95)  # Positive longitude should be negated
		
		assert result.confirmed is True
		assert result.observed_coordinate is not None
		assert result.observed_coordinate.latitude == 33.05
		assert result.observed_coordinate.longitude == -96.95  # Should be negated
		assert result.location_index == 1
	
	def test_coordinate_not_found(self, tool, mock_state, sample_event):
		"""Test that coordinate outside all polygons returns not confirmed."""
		mock_state.get_event.return_value = sample_event
		
		# Coordinate outside all polygons
		result = tool._run("TEST-KEY-001", 40.0, -100.0)
		
		assert result.confirmed is False
		assert result.observed_coordinate is None
		assert result.location_index is None
	
	def test_location_without_full_shape(self, tool, mock_state):
		"""Test that locations without full_shape are skipped."""
		event = Event(
			event_key="TEST-KEY-001",
			nws_alert_id="alert-1",
			event_type="TOR",
			start_date=datetime.now(timezone.utc),
			description="Test",
			is_active=True,
			confirmed=False,
			raw_vtec="/O.NEW.TEST.TO.W.0015.240115T1000Z/",
			office="KTEST",
			locations=[
				Location(
					event_key="TEST-KEY-001",
					state_fips="48",
					county_fips="113",
					ugc_code="TXC113",
					full_zone_ugc_endpoint="https://api.weather.gov/zones/forecast/TXC113",
					full_shape=None  # No shape
				)
			]
		)
		mock_state.get_event.return_value = event
		
		result = tool._run("TEST-KEY-001", 32.8, -97.5)
		
		assert result.confirmed is False
		assert result.observed_coordinate is None
		assert result.location_index is None
	
	def test_polygon_with_insufficient_points(self, tool, mock_state):
		"""Test that polygons with less than 3 points are skipped."""
		event = Event(
			event_key="TEST-KEY-001",
			nws_alert_id="alert-1",
			event_type="TOR",
			start_date=datetime.now(timezone.utc),
			description="Test",
			is_active=True,
			confirmed=False,
			raw_vtec="/O.NEW.TEST.TO.W.0015.240115T1000Z/",
			office="KTEST",
			locations=[
				Location(
					event_key="TEST-KEY-001",
					state_fips="48",
					county_fips="113",
					ugc_code="TXC113",
					full_zone_ugc_endpoint="https://api.weather.gov/zones/forecast/TXC113",
					full_shape=[[
						Coordinate(latitude=32.8, longitude=-97.5),
						Coordinate(latitude=32.9, longitude=-97.5)
						# Only 2 points - insufficient
					]]
				)
			]
		)
		mock_state.get_event.return_value = event
		
		result = tool._run("TEST-KEY-001", 32.8, -97.5)
		
		assert result.confirmed is False
		assert result.observed_coordinate is None
		assert result.location_index is None
	
	def test_longitude_negation(self, tool, mock_state, sample_event):
		"""Test that positive longitudes are negated."""
		mock_state.get_event.return_value = sample_event
		
		# Pass positive longitude
		result = tool._run("TEST-KEY-001", 32.85, 97.45)
		
		# Should be negated in the result
		assert result.observed_coordinate.longitude == -97.45
	
	def test_multiple_polygons_in_location(self, tool, mock_state):
		"""Test that tool checks all polygons in a location's full_shape."""
		event = Event(
			event_key="TEST-KEY-001",
			nws_alert_id="alert-1",
			event_type="TOR",
			start_date=datetime.now(timezone.utc),
			description="Test",
			is_active=True,
			confirmed=False,
			raw_vtec="/O.NEW.TEST.TO.W.0015.240115T1000Z/",
			office="KTEST",
			locations=[
				Location(
					event_key="TEST-KEY-001",
					state_fips="48",
					county_fips="113",
					ugc_code="TXC113",
					full_zone_ugc_endpoint="https://api.weather.gov/zones/forecast/TXC113",
					full_shape=[
						[
							Coordinate(latitude=32.0, longitude=-97.0),
							Coordinate(latitude=32.1, longitude=-97.0),
							Coordinate(latitude=32.1, longitude=-96.9),
							Coordinate(latitude=32.0, longitude=-96.9),
							Coordinate(latitude=32.0, longitude=-97.0)
						],
						[
							Coordinate(latitude=32.8, longitude=-97.5),
							Coordinate(latitude=32.9, longitude=-97.5),
							Coordinate(latitude=32.9, longitude=-97.4),
							Coordinate(latitude=32.8, longitude=-97.4),
							Coordinate(latitude=32.8, longitude=-97.5)
						]
					]
				)
			]
		)
		mock_state.get_event.return_value = event
		
		# Coordinate in second polygon
		result = tool._run("TEST-KEY-001", 32.85, 97.45)
		
		assert result.confirmed is True
		assert result.location_index == 0  # Still index 0 (first location)
	
	def test_polygon_closing(self, tool, mock_state):
		"""Test that polygons are automatically closed if not already closed."""
		event = Event(
			event_key="TEST-KEY-001",
			nws_alert_id="alert-1",
			event_type="TOR",
			start_date=datetime.now(timezone.utc),
			description="Test",
			is_active=True,
			confirmed=False,
			raw_vtec="/O.NEW.TEST.TO.W.0015.240115T1000Z/",
			office="KTEST",
			locations=[
				Location(
					event_key="TEST-KEY-001",
					state_fips="48",
					county_fips="113",
					ugc_code="TXC113",
					full_zone_ugc_endpoint="https://api.weather.gov/zones/forecast/TXC113",
					full_shape=[[
						Coordinate(latitude=32.8, longitude=-97.5),
						Coordinate(latitude=32.9, longitude=-97.5),
						Coordinate(latitude=32.9, longitude=-97.4),
						Coordinate(latitude=32.8, longitude=-97.4)
						# Not closed - should be auto-closed
					]]
				)
			]
		)
		mock_state.get_event.return_value = event
		
		# Coordinate inside the polygon
		result = tool._run("TEST-KEY-001", 32.85, 97.45)
		
		assert result.confirmed is True
		assert result.location_index == 0

