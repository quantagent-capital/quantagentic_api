"""
Unit tests for EventCreateService.
"""
import pytest
from unittest.mock import Mock, patch
from app.services.event_create_service import EventCreateService
from app.shared_models.nws_poller_models import FilteredNWSAlert
from app.schemas.event import Event
from app.schemas.location import Location, Coordinate
from app.exceptions.base import ConflictError
from app.utils.nws_event_types import NWS_WARNING_CODES

class TestCreateEventFromAlert:
	"""Test cases for EventCreateService.create_event_from_alert."""
	
	@pytest.fixture
	def sample_alert(self):
		"""Create a sample FilteredNWSAlert for testing."""
		return FilteredNWSAlert(
			alert_id="https://api.weather.gov/alerts/urn:oid:2.49.0.1.840.0.1234567890",
			key="KFWD.TO.W.0015.2024",
			event_type="TOR",
			message_type="NEW",
			is_watch=False,
			is_warning=True,
			severity="Extreme",
			urgency="Immediate",
			certainty="Observed",
			effective="2024-01-15T10:00:00-06:00",
			expires="2024-01-15T11:00:00-06:00",
			expected_end="2024-01-15T11:00:00-06:00",
			headline="Tornado Warning",
			description="Test tornado warning description",
			raw_vtec="/O.NEW.KFWD.TO.W.0015.240115T1000Z-240115T1100Z/",
			affected_zones_ugc_endpoints=["https://api.weather.gov/zones/forecast/TXC113"],
			affected_zones_raw_ugc_codes=["TXC113"],
			referenced_alerts=[],
			locations=[
				Location(
					episode_key=None,
					event_key="KFWD.TO.W.0015.2024",
					state_fips="48",
					county_fips="113",
					ugc_code="TXC113",
					shape=[Coordinate(latitude=32.8, longitude=-97.5)],
					full_zone_ugc_endpoint="https://api.weather.gov/zones/forecast/TXC113"
				)
			]
		)
	
	
	@patch('app.services.event_create_service.state')
	def test_create_event_from_alert_success(self, mock_state, sample_alert):
		"""Test successful event creation from alert."""
		# Setup
		mock_state.event_exists.return_value = False
		mock_state.add_event = Mock()
		
		# Execute
		result = EventCreateService.create_event_from_alert(sample_alert)
		
		# Assertions
		assert isinstance(result, Event)
		assert result.event_key == sample_alert.key
		assert result.nws_alert_id == sample_alert.alert_id
		assert result.event_type == sample_alert.event_type
		assert result.hr_event_type == NWS_WARNING_CODES.get("TOR", "UNKNOWN")
		assert result.episode_key is None
		assert result.is_active is True
		assert result.locations == sample_alert.locations
		assert result.raw_vtec == sample_alert.raw_vtec
		assert result.previous_ids == []
		assert "Tornado Warning" in result.description
		assert "Test tornado warning description" in result.description
		assert result.updated_at is not None
		mock_state.add_event.assert_called_once_with(result)
	
	@patch('app.services.event_create_service.state')
	def test_create_event_from_alert_with_missing_dates(self, mock_state):
		"""Test event creation when optional dates are missing."""
		# Setup
		mock_state.event_exists.return_value = False
		mock_state.add_event = Mock()
		
		# Note: effective is required, but expected_end is optional
		alert = FilteredNWSAlert(
			alert_id="test-alert-1",
			key="KFWD.TO.W.0015.2024",
			event_type="TOR",
			message_type="NEW",
			is_watch=False,
			is_warning=True,
			severity="Extreme",
			urgency="Immediate",
			certainty="Observed",
			effective="2024-01-15T10:00:00-06:00",  # Required field
			expires=None,
			expected_end=None,  # Optional field
			headline=None,
			description=None,
			raw_vtec="/O.NEW.KFWD.TO.W.0015.240115T1000Z-240115T1100Z/",
			affected_zones_ugc_endpoints=[],
			affected_zones_raw_ugc_codes=[],
			referenced_alerts=[],
			locations=[]
		)
		
		# Execute
		result = EventCreateService.create_event_from_alert(alert)
		
		# Assertions
		assert result.start_date is not None  # Should be parsed from effective
		assert result.expected_end_date is None  # Should be None when expected_end is None
		assert result.description == "\n\n"  # Empty headline and description
	
	
	@patch('app.services.event_create_service.state')
	def test_create_event_from_alert_conflict_error(self, mock_state, sample_alert):
		"""Test that ConflictError is raised when event already exists."""
		# Setup
		mock_state.event_exists.return_value = True
		
		# Execute & Assert
		with pytest.raises(ConflictError) as exc_info:
			EventCreateService.create_event_from_alert(sample_alert)
		
		assert "already exists" in str(exc_info.value)
		assert sample_alert.key in str(exc_info.value)
	
	@patch('app.services.event_create_service.state')
	def test_create_event_from_alert_unknown_event_type(self, mock_state):
		"""Test event creation with unknown event type."""
		# Setup
		mock_state.event_exists.return_value = False
		mock_state.add_event = Mock()
		
		alert = FilteredNWSAlert(
			alert_id="test-alert-1",
			key="KFWD.XXX.W.0015.2024",
			event_type="XXX",
			message_type="NEW",
			is_watch=False,
			is_warning=True,
			severity="Extreme",
			urgency="Immediate",
			certainty="Observed",
			effective="2024-01-15T10:00:00-06:00",
			expires="2024-01-15T11:00:00-06:00",
			expected_end="2024-01-15T11:00:00-06:00",
			headline="Test",
			description="Test",
			raw_vtec="/O.NEW.KFWD.XXX.W.0015.240115T1000Z-240115T1100Z/",
			affected_zones_ugc_endpoints=[],
			affected_zones_raw_ugc_codes=[],
			referenced_alerts=[],
			locations=[]
		)
		
		# Execute
		result = EventCreateService.create_event_from_alert(alert)
		
		# Assertions
		assert result.hr_event_type == "UNKNOWN"
	
	
	@patch('app.services.event_create_service.state')
	def test_create_event_from_alert_preserves_all_fields(self, mock_state, sample_alert):
		"""Test that all alert fields are properly mapped to event."""
		# Setup
		mock_state.event_exists.return_value = False
		mock_state.add_event = Mock()
		
		# Execute
		result = EventCreateService.create_event_from_alert(sample_alert)
		
		# Assertions - verify all fields are set correctly
		assert result.event_key == "KFWD.TO.W.0015.2024"
		assert result.nws_alert_id == "https://api.weather.gov/alerts/urn:oid:2.49.0.1.840.0.1234567890"
		assert len(result.locations) == 1
		assert result.locations[0].ugc_code == "TXC113"
		assert result.is_active is True







class TestConfirmedFunctionalityCreate:
	"""Test cases for confirmed field functionality in event creation."""
	
	@patch('app.services.event_create_service.state')
	def test_create_event_with_observed_certainty_sets_confirmed_true(self, mock_state):
		"""Test that creating an event with certainty='Observed' sets confirmed=True."""
		mock_state.event_exists.return_value = False
		mock_state.add_event = Mock()
		
		alert = FilteredNWSAlert(
			alert_id="test-alert-1",
			key="KFWD.TO.W.0015.2024",
			event_type="TOR",
			message_type="NEW",
			is_watch=False,
			is_warning=True,
			severity="Extreme",
			urgency="Immediate",
			certainty="Observed",
			effective="2024-01-15T10:00:00-06:00",
			expires="2024-01-15T11:00:00-06:00",
			expected_end="2024-01-15T11:00:00-06:00",
			headline="Test",
			description="Test",
			raw_vtec="/O.NEW.KFWD.TO.W.0015.240115T1000Z-240115T1100Z/",
			affected_zones_ugc_endpoints=[],
			affected_zones_raw_ugc_codes=[],
			referenced_alerts=[],
			locations=[]
		)
		
		result = EventCreateService.create_event_from_alert(alert)
		
		assert result.confirmed is True
	
	@patch('app.services.event_create_service.state')
	def test_create_event_with_non_observed_certainty_sets_confirmed_false(self, mock_state):
		"""Test that creating an event with certainty != 'Observed' sets confirmed=False."""
		mock_state.event_exists.return_value = False
		mock_state.add_event = Mock()
		
		alert = FilteredNWSAlert(
			alert_id="test-alert-1",
			key="KFWD.TO.W.0015.2024",
			event_type="TOR",
			message_type="NEW",
			is_watch=False,
			is_warning=True,
			severity="Extreme",
			urgency="Immediate",
			certainty="Likely",
			effective="2024-01-15T10:00:00-06:00",
			expires="2024-01-15T11:00:00-06:00",
			expected_end="2024-01-15T11:00:00-06:00",
			headline="Test",
			description="Test",
			raw_vtec="/O.NEW.KFWD.TO.W.0015.240115T1000Z-240115T1100Z/",
			affected_zones_ugc_endpoints=[],
			affected_zones_raw_ugc_codes=[],
			referenced_alerts=[],
			locations=[]
		)
		
		result = EventCreateService.create_event_from_alert(alert)
		
		assert result.confirmed is False
	
	@patch('app.services.event_create_service.state')
	def test_create_event_with_case_insensitive_observed_certainty(self, mock_state):
		"""Test that certainty check is case-insensitive."""
		mock_state.event_exists.return_value = False
		mock_state.add_event = Mock()
		
		# Test lowercase
		alert_lower = FilteredNWSAlert(
			alert_id="test-alert-1",
			key="KFWD.TO.W.0015.2024",
			event_type="TOR",
			message_type="NEW",
			is_watch=False,
			is_warning=True,
			severity="Extreme",
			urgency="Immediate",
			certainty="observed",
			effective="2024-01-15T10:00:00-06:00",
			expires="2024-01-15T11:00:00-06:00",
			expected_end="2024-01-15T11:00:00-06:00",
			headline="Test",
			description="Test",
			raw_vtec="/O.NEW.KFWD.TO.W.0015.240115T1000Z-240115T1100Z/",
			affected_zones_ugc_endpoints=[],
			affected_zones_raw_ugc_codes=[],
			referenced_alerts=[],
			locations=[]
		)
		
		result = EventCreateService.create_event_from_alert(alert_lower)
		assert result.confirmed is True
		
		# Test mixed case
		mock_state.event_exists.return_value = False
		alert_mixed = FilteredNWSAlert(
			alert_id="test-alert-2",
			key="KFWD.TO.W.0016.2024",
			event_type="TOR",
			message_type="NEW",
			is_watch=False,
			is_warning=True,
			severity="Extreme",
			urgency="Immediate",
			certainty="OBSERVED",
			effective="2024-01-15T10:00:00-06:00",
			expires="2024-01-15T11:00:00-06:00",
			expected_end="2024-01-15T11:00:00-06:00",
			headline="Test",
			description="Test",
			raw_vtec="/O.NEW.KFWD.TO.W.0016.240115T1000Z-240115T1100Z/",
			affected_zones_ugc_endpoints=[],
			affected_zones_raw_ugc_codes=[],
			referenced_alerts=[],
			locations=[]
		)
		
		result = EventCreateService.create_event_from_alert(alert_mixed)
		assert result.confirmed is True
	
	@patch('app.services.event_create_service.state')
	def test_create_event_with_empty_certainty_sets_confirmed_false(self, mock_state):
		"""Test that creating an event with empty certainty string sets confirmed=False."""
		mock_state.event_exists.return_value = False
		mock_state.add_event = Mock()
		
		alert = FilteredNWSAlert(
			alert_id="test-alert-1",
			key="KFWD.TO.W.0015.2024",
			event_type="TOR",
			message_type="NEW",
			is_watch=False,
			is_warning=True,
			severity="Extreme",
			urgency="Immediate",
			certainty="",  # Empty string
			effective="2024-01-15T10:00:00-06:00",
			expires="2024-01-15T11:00:00-06:00",
			expected_end="2024-01-15T11:00:00-06:00",
			headline="Test",
			description="Test",
			raw_vtec="/O.NEW.KFWD.TO.W.0015.240115T1000Z-240115T1100Z/",
			affected_zones_ugc_endpoints=[],
			affected_zones_raw_ugc_codes=[],
			referenced_alerts=[],
			locations=[]
		)
		
		result = EventCreateService.create_event_from_alert(alert)
		
		assert result.confirmed is False




