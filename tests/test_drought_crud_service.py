"""
Unit tests for DroughtCRUDService.
"""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timezone
from app.services.drought_crud_service import DroughtCRUDService
from app.schemas.drought import Drought
from app.schemas.location import Location
from app.schemas.counties import County, Coordinate


class TestCreateDrought:
	"""Test cases for DroughtCRUDService.create_drought."""
	
	@pytest.fixture
	def sample_county(self):
		"""Create a sample County for testing."""
		return County(
			fips="001",
			state_abbr="TX",
			state_fips="48",
			name="Test County",
			centroid=Coordinate(latitude=32.8, longitude=-97.5)
		)
	
	@pytest.fixture
	def sample_drought_data(self):
		"""Create sample drought data dictionary."""
		return {
			'severity': 'D2',
			'dm': 2,
			'geometry': Mock()  # Mock geometry object
		}
	
	@patch('app.services.drought_crud_service.state')
	def test_create_drought_success(self, mock_state, sample_county, sample_drought_data):
		"""Test successful drought creation."""
		mock_state.add_drought = Mock()
		event_key = "DRT-001-48"
		
		result = DroughtCRUDService.create_drought(sample_county, event_key, sample_drought_data)
		
		# Assertions
		assert isinstance(result, Drought)
		assert result.event_key == event_key
		assert result.episode_key is None
		assert result.severity == "D2"
		assert result.is_active is True
		assert result.end_date is None
		assert result.description is not None
		assert "Test County" in result.description
		assert "TX" in result.description
		assert "D2" in result.description
		assert result.location.county_fips == "001"
		assert result.location.state_fips == "48"
		assert result.location.event_key == event_key
		assert result.start_date is not None
		assert result.updated_at is not None
		mock_state.add_drought.assert_called_once()
	
	@patch('app.services.drought_crud_service.state')
	def test_create_drought_sets_correct_location(self, mock_state, sample_county, sample_drought_data):
		"""Test that drought creation sets location correctly."""
		mock_state.add_drought = Mock()
		event_key = "DRT-001-48"
		
		result = DroughtCRUDService.create_drought(sample_county, event_key, sample_drought_data)
		
		assert isinstance(result.location, Location)
		assert result.location.county_fips == sample_county.fips
		assert result.location.state_fips == sample_county.state_fips
		assert result.location.event_key == event_key
		assert result.location.episode_key is None
		assert result.location.ugc_code == ""
		assert result.location.shape == []
		assert result.location.full_zone_ugc_endpoint == ""


class TestUpdateDrought:
	"""Test cases for DroughtCRUDService.update_drought."""
	
	@pytest.fixture
	def existing_drought(self):
		"""Create an existing drought for testing."""
		location = Location(
			episode_key=None,
			event_key="DRT-001-48",
			state_fips="48",
			county_fips="001",
			ugc_code="",
			shape=[],
			full_zone_ugc_endpoint=""
		)
		return Drought(
			event_key="DRT-001-48",
			episode_key=None,
			start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
			end_date=None,
			description="Original description",
			is_active=True,
			location=location,
			severity="D1",
			updated_at=datetime(2024, 1, 1, tzinfo=timezone.utc)
		)
	
	@patch('app.services.drought_crud_service.state')
	def test_update_drought_success(self, mock_state, existing_drought):
		"""Test successful drought update with higher severity."""
		mock_state.update_drought = Mock()
		new_severity = "D3"
		
		result = DroughtCRUDService.update_drought(existing_drought, new_severity)
		
		# Assertions
		assert isinstance(result, Drought)
		assert result.event_key == existing_drought.event_key
		assert result.severity == new_severity
		assert result.is_active is True
		assert result.end_date is None  # Should remain None on update
		assert result.start_date == existing_drought.start_date
		assert result.location == existing_drought.location
		assert "Updated severity: D3" in result.description
		assert result.updated_at is not None
		assert result.updated_at > existing_drought.updated_at
		mock_state.update_drought.assert_called_once()
	
	@patch('app.services.drought_crud_service.state')
	def test_update_drought_with_empty_description(self, mock_state):
		"""Test drought update when original description is empty."""
		mock_state.update_drought = Mock()
		location = Location(
			episode_key=None,
			event_key="DRT-001-48",
			state_fips="48",
			county_fips="001",
			ugc_code="",
			shape=[],
			full_zone_ugc_endpoint=""
		)
		existing_drought = Drought(
			event_key="DRT-001-48",
			episode_key=None,
			start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
			end_date=None,
			description=None,
			is_active=True,
			location=location,
			severity="D1",
			updated_at=datetime(2024, 1, 1, tzinfo=timezone.utc)
		)
		
		result = DroughtCRUDService.update_drought(existing_drought, "D2")
		
		assert "Updated severity: D2" in result.description
		mock_state.update_drought.assert_called_once()
	
	@patch('app.services.drought_crud_service.state')
	def test_update_drought_preserves_fields(self, mock_state, existing_drought):
		"""Test that update preserves all fields except severity and updated_at."""
		mock_state.update_drought = Mock()
		
		result = DroughtCRUDService.update_drought(existing_drought, "D4")
		
		assert result.event_key == existing_drought.event_key
		assert result.episode_key == existing_drought.episode_key
		assert result.start_date == existing_drought.start_date
		assert result.location == existing_drought.location
		assert result.is_active is True  # Should always be True on update


class TestCompleteDrought:
	"""Test cases for DroughtCRUDService.complete_drought."""
	
	@pytest.fixture
	def active_drought(self):
		"""Create an active drought for testing."""
		location = Location(
			episode_key=None,
			event_key="DRT-001-48",
			state_fips="48",
			county_fips="001",
			ugc_code="",
			shape=[],
			full_zone_ugc_endpoint=""
		)
		return Drought(
			event_key="DRT-001-48",
			episode_key=None,
			start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
			end_date=None,
			description="Active drought",
			is_active=True,
			location=location,
			severity="D2",
			updated_at=datetime(2024, 1, 1, tzinfo=timezone.utc)
		)
	
	@patch('app.services.drought_crud_service.state')
	def test_complete_drought_success(self, mock_state, active_drought):
		"""Test successful drought completion."""
		mock_state.get_drought.return_value = active_drought
		mock_state.update_drought = Mock()
		event_key = "DRT-001-48"
		
		result = DroughtCRUDService.complete_drought(event_key)
		
		# Assertions
		assert isinstance(result, Drought)
		assert result.event_key == event_key
		assert result.is_active is False
		assert result.end_date is not None
		assert result.severity == active_drought.severity
		assert result.start_date == active_drought.start_date
		assert result.location == active_drought.location
		assert result.description == active_drought.description
		assert result.updated_at is not None
		mock_state.get_drought.assert_called_once_with(event_key)
		mock_state.update_drought.assert_called_once()
	
	@patch('app.services.drought_crud_service.state')
	def test_complete_drought_not_found(self, mock_state):
		"""Test completing a drought that doesn't exist."""
		mock_state.get_drought.return_value = None
		event_key = "DRT-NONEXISTENT-48"
		
		result = DroughtCRUDService.complete_drought(event_key)
		
		assert result is None
		mock_state.get_drought.assert_called_once_with(event_key)
		mock_state.update_drought.assert_not_called()
	
	@patch('app.services.drought_crud_service.state')
	def test_complete_drought_sets_end_date(self, mock_state, active_drought):
		"""Test that completion sets end_date to current time."""
		mock_state.get_drought.return_value = active_drought
		mock_state.update_drought = Mock()
		
		before_completion = datetime.now(timezone.utc)
		result = DroughtCRUDService.complete_drought("DRT-001-48")
		after_completion = datetime.now(timezone.utc)
		
		assert result.end_date is not None
		assert before_completion <= result.end_date <= after_completion

