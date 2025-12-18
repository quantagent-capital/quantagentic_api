"""
Unit tests for WildfireCRUDService.
"""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timezone
from app.services.wildfire_crud_service import WildfireCRUDService
from app.schemas.wildfire import Wildfire
from app.schemas.location import Location, Coordinate


class TestCreateWildfire:
	"""Test cases for WildfireCRUDService.create_wildfire."""
	
	@pytest.fixture
	def sample_feature(self):
		"""Create a sample ArcGIS feature for testing."""
		return {
			"properties": {
				"OBJECTID": 40095,
				"attr_UniqueFireIdentifier": "2025-NMN4S-000043",
				"attr_FireDiscoveryDateTime": 1741976700000,  # milliseconds timestamp
				"attr_ModifiedOnDateTime_dt": 1762199008867,
				"attr_POOFips": "35033",
				"attr_InitialLatitude": 35.814081,
				"attr_InitialLongitude": -104.962435,
				"poly_GISAcres": 21433,
				"attr_IncidentComplexityLevel": "Type 3 Incident",
				"attr_EstimatedFinalCost": 390000,
				"attr_IncidentName": "Wagon Mound",
				"attr_IncidentShortDescription": "Approximately 40 miles northeast of Las Vegas, NM",
				"attr_PrimaryFuelModel": "Short Grass (1 foot)",
				"attr_SecondaryFuelModel": "Brush (2 feet)",
				"attr_PercentContained": 97
			},
			"geometry": {
				"type": "Polygon",
				"coordinates": [[
					[-104.962435, 35.814081],
					[-104.900000, 35.814081],
					[-104.900000, 35.850000],
					[-104.962435, 35.850000],
					[-104.962435, 35.814081]
				]]
			}
		}
	
	@patch('app.services.wildfire_crud_service.state')
	def test_create_wildfire_success(self, mock_state, sample_feature):
		"""Test successful wildfire creation."""
		mock_state.add_wildfire = Mock()
		
		result = WildfireCRUDService.create_wildfire(sample_feature)
		
		# Assertions
		assert isinstance(result, Wildfire)
		assert result.event_key == "2025-NMN4S-000043"
		assert result.arcgis_id == "40095"
		assert result.acres_burned == 21433
		assert result.severity == 3  # Type 3 Incident
		assert result.cost == 390000
		assert result.description == "Wagon Mound - Approximately 40 miles northeast of Las Vegas, NM"
		assert result.fuel_source == "Short Grass (1 foot) / Brush (2 feet)"
		assert result.percent_contained == 97
		assert result.active is True
		assert result.end_date is None
		assert result.start_date is not None
		assert result.last_modified is not None
		assert isinstance(result.location, Location)
		assert result.location.state_fips == "35"
		assert result.location.county_fips == "033"
		assert result.location.starting_point is not None
		assert result.location.starting_point.latitude == 35.814081
		assert result.location.starting_point.longitude == -104.962435
		assert len(result.location.shape) == 5
		mock_state.add_wildfire.assert_called_once()
	
	@patch('app.services.wildfire_crud_service.state')
	def test_create_wildfire_with_none_values(self, mock_state):
		"""Test creating wildfire with None values."""
		mock_state.add_wildfire = Mock()
		feature = {
			"properties": {
				"OBJECTID": 12345,
				"attr_UniqueFireIdentifier": "TEST-001",
				"attr_FireDiscoveryDateTime": None,
				"attr_ModifiedOnDateTime_dt": None,
				"attr_POOFips": None,
				"attr_InitialLatitude": None,
				"attr_InitialLongitude": None,
				"poly_GISAcres": None,
				"attr_IncidentComplexityLevel": None,
				"attr_EstimatedFinalCost": None,
				"attr_IncidentName": None,
				"attr_IncidentShortDescription": None,
				"attr_PrimaryFuelModel": None,
				"attr_SecondaryFuelModel": None,
				"attr_PercentContained": None
			},
			"geometry": {
				"type": "Polygon",
				"coordinates": []
			}
		}
		
		result = WildfireCRUDService.create_wildfire(feature)
		
		assert result.event_key == "TEST-001"
		assert result.arcgis_id == "12345"
		assert result.acres_burned == 0
		assert result.severity == 3  # Default for None
		assert result.cost is None
		assert result.description is None
		assert result.fuel_source is None
		assert result.percent_contained is None
		assert result.location.starting_point.latitude == 0.0
		assert result.location.starting_point.longitude == 0.0
		assert result.location.state_fips == "UNKNOWN"
		assert result.location.county_fips == "UNKNOWN"
	
	@patch('app.services.wildfire_crud_service.state')
	def test_create_wildfire_with_multipolygon(self, mock_state):
		"""Test creating wildfire with MultiPolygon geometry."""
		mock_state.add_wildfire = Mock()
		feature = {
			"properties": {
				"OBJECTID": 50000,
				"attr_UniqueFireIdentifier": "TEST-MULTI-001",
				"attr_FireDiscoveryDateTime": 1741976700000,
				"attr_ModifiedOnDateTime_dt": 1762199008867,
				"attr_POOFips": "06001",
				"attr_InitialLatitude": 37.5,
				"attr_InitialLongitude": -122.0,
				"poly_GISAcres": 1000,
				"attr_IncidentComplexityLevel": "Type 1 Incident",
				"attr_EstimatedFinalCost": 100000,
				"attr_IncidentName": "Test Fire",
				"attr_IncidentShortDescription": "Test description",
				"attr_PrimaryFuelModel": "Grass",
				"attr_SecondaryFuelModel": None,
				"attr_PercentContained": 50
			},
			"geometry": {
				"type": "MultiPolygon",
				"coordinates": [[[
					[-122.0, 37.5],
					[-121.9, 37.5],
					[-121.9, 37.6],
					[-122.0, 37.6],
					[-122.0, 37.5]
				]]]
			}
		}
		
		result = WildfireCRUDService.create_wildfire(feature)
		
		assert result.severity == 1  # Type 1 Incident
		assert len(result.location.shape) == 5
		assert result.location.shape[0].latitude == 37.5
		assert result.location.shape[0].longitude == -122.0


class TestUpdateWildfire:
	"""Test cases for WildfireCRUDService.update_wildfire."""
	
	@pytest.fixture
	def existing_wildfire(self):
		"""Create an existing wildfire for testing."""
		location = Location(
			episode_key=None,
			event_key="2025-NMN4S-000043",
			state_fips="35",
			county_fips="033",
			ugc_code="",
			shape=[Coordinate(latitude=35.814081, longitude=-104.962435)],
			full_zone_ugc_endpoint="",
			starting_point=Coordinate(latitude=35.814081, longitude=-104.962435)
		)
		return Wildfire(
			event_key="2025-NMN4S-000043",
			episode_key=None,
			arcgis_id="40095",
			location=location,
			acres_burned=20000,
			severity=3,
			start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
			last_modified=datetime(2024, 1, 1, tzinfo=timezone.utc),
			end_date=None,
			cost=300000,
			description="Original description",
			fuel_source="Original fuel",
			active=True,
			percent_contained=90
		)
	
	@pytest.fixture
	def update_feature(self):
		"""Create an update feature for testing."""
		return {
			"properties": {
				"OBJECTID": 40095,
				"attr_UniqueFireIdentifier": "2025-NMN4S-000043",
				"attr_ModifiedOnDateTime_dt": 1762200000000,
				"poly_GISAcres": 25000,  # Updated
				"attr_IncidentComplexityLevel": "Type 2 Incident",  # Updated severity
				"attr_EstimatedFinalCost": 450000,  # Updated cost
				"attr_IncidentName": "Updated Name",
				"attr_IncidentShortDescription": "Updated description",
				"attr_PrimaryFuelModel": "Updated Fuel",
				"attr_SecondaryFuelModel": "Secondary Fuel",
				"attr_PercentContained": 95  # Updated
			},
			"geometry": {
				"type": "Polygon",
				"coordinates": [[
					[-104.962435, 35.814081],
					[-104.850000, 35.814081],
					[-104.850000, 35.900000],
					[-104.962435, 35.900000],
					[-104.962435, 35.814081]
				]]
			}
		}
	
	@patch('app.services.wildfire_crud_service.state')
	def test_update_wildfire_success(self, mock_state, existing_wildfire, update_feature):
		"""Test successful wildfire update."""
		mock_state.update_wildfire = Mock()
		
		result = WildfireCRUDService.update_wildfire(existing_wildfire, update_feature)
		
		# Assertions - NEW values should be updated
		assert result.acres_burned == 25000
		assert result.severity == 2  # Type 2 Incident
		assert result.cost == 450000
		assert result.description == "Updated Name - Updated description"
		assert result.fuel_source == "Updated Fuel / Secondary Fuel"
		assert result.percent_contained == 95
		assert len(result.location.shape) == 5  # New shape
		
		# Assertions - EXISTING values should be preserved
		assert result.event_key == existing_wildfire.event_key
		assert result.arcgis_id == existing_wildfire.arcgis_id
		assert result.start_date == existing_wildfire.start_date
		assert result.location.state_fips == existing_wildfire.location.state_fips
		assert result.location.county_fips == existing_wildfire.location.county_fips
		assert result.location.starting_point == existing_wildfire.location.starting_point
		assert result.active == existing_wildfire.active
		
		mock_state.update_wildfire.assert_called_once()
	
	@patch('app.services.wildfire_crud_service.state')
	def test_update_wildfire_preserves_starting_point(self, mock_state, existing_wildfire, update_feature):
		"""Test that update preserves starting_point."""
		mock_state.update_wildfire = Mock()
		
		result = WildfireCRUDService.update_wildfire(existing_wildfire, update_feature)
		
		assert result.location.starting_point == existing_wildfire.location.starting_point
		assert result.location.starting_point.latitude == 35.814081
		assert result.location.starting_point.longitude == -104.962435


class TestCompleteWildfire:
	"""Test cases for WildfireCRUDService.complete_wildfire."""
	
	@pytest.fixture
	def active_wildfire(self):
		"""Create an active wildfire for testing."""
		location = Location(
			episode_key=None,
			event_key="2025-NMN4S-000043",
			state_fips="35",
			county_fips="033",
			ugc_code="",
			shape=[],
			full_zone_ugc_endpoint="",
			starting_point=Coordinate(latitude=35.814081, longitude=-104.962435)
		)
		return Wildfire(
			event_key="2025-NMN4S-000043",
			episode_key=None,
			arcgis_id="40095",
			location=location,
			acres_burned=20000,
			severity=3,
			start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
			last_modified=datetime(2024, 1, 1, tzinfo=timezone.utc),
			end_date=None,
			cost=300000,
			description="Active fire",
			fuel_source="Grass",
			active=True,
			percent_contained=90
		)
	
	@patch('app.services.wildfire_crud_service.state')
	def test_complete_wildfire_success(self, mock_state, active_wildfire):
		"""Test successful wildfire completion."""
		mock_state.get_wildfire.return_value = active_wildfire
		mock_state.update_wildfire = Mock()
		
		result = WildfireCRUDService.complete_wildfire("2025-NMN4S-000043")
		
		# Assertions
		assert isinstance(result, Wildfire)
		assert result.event_key == active_wildfire.event_key
		assert result.active is False
		assert result.end_date is not None
		assert result.end_date >= active_wildfire.start_date
		assert result.location == active_wildfire.location
		assert result.acres_burned == active_wildfire.acres_burned
		assert result.severity == active_wildfire.severity
		assert result.start_date == active_wildfire.start_date
		assert result.last_modified is not None
		mock_state.get_wildfire.assert_called_once_with("2025-NMN4S-000043")
		mock_state.update_wildfire.assert_called_once()
	
	@patch('app.services.wildfire_crud_service.state')
	def test_complete_wildfire_not_found(self, mock_state):
		"""Test completing a wildfire that doesn't exist."""
		mock_state.get_wildfire.return_value = None
		mock_state.update_wildfire = Mock()
		
		result = WildfireCRUDService.complete_wildfire("NONEXISTENT")
		
		assert result is None
		mock_state.get_wildfire.assert_called_once_with("NONEXISTENT")
		mock_state.update_wildfire.assert_not_called()
	
	@patch('app.services.wildfire_crud_service.state')
	def test_complete_wildfire_sets_end_date(self, mock_state, active_wildfire):
		"""Test that completion sets end_date to current time."""
		mock_state.get_wildfire.return_value = active_wildfire
		mock_state.update_wildfire = Mock()
		
		before_completion = datetime.now(timezone.utc)
		result = WildfireCRUDService.complete_wildfire("2025-NMN4S-000043")
		after_completion = datetime.now(timezone.utc)
		
		assert result.end_date is not None
		assert before_completion <= result.end_date <= after_completion
