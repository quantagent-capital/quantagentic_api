"""
Comprehensive unit tests for EventService methods.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
from app.services.event_service import EventService
from app.shared_models.nws_poller_models import FilteredNWSAlert
from app.schemas.event import Event
from app.schemas.location import Location, Coordinate
from app.exceptions import NotFoundError
from app.exceptions.base import ConflictError
from app.crews.utils.nws_event_types import NWS_WARNING_CODES


class TestCreateEventFromAlert:
	"""Test cases for EventService.create_event_from_alert."""
	
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
	
	@patch('app.services.event_service.state')
	def test_create_event_from_alert_success(self, mock_state, sample_alert):
		"""Test successful event creation from alert."""
		# Setup
		mock_state.event_exists.return_value = False
		mock_state.add_event = Mock()
		
		# Execute
		result = EventService.create_event_from_alert(sample_alert)
		
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
	
	@patch('app.services.event_service.state')
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
		result = EventService.create_event_from_alert(alert)
		
		# Assertions
		assert result.start_date is not None  # Should be parsed from effective
		assert result.expected_end_date is None  # Should be None when expected_end is None
		assert result.description == "\n\n"  # Empty headline and description
	
	@patch('app.services.event_service.state')
	def test_create_event_from_alert_conflict_error(self, mock_state, sample_alert):
		"""Test that ConflictError is raised when event already exists."""
		# Setup
		mock_state.event_exists.return_value = True
		
		# Execute & Assert
		with pytest.raises(ConflictError) as exc_info:
			EventService.create_event_from_alert(sample_alert)
		
		assert "already exists" in str(exc_info.value)
		assert sample_alert.key in str(exc_info.value)
	
	@patch('app.services.event_service.state')
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
		result = EventService.create_event_from_alert(alert)
		
		# Assertions
		assert result.hr_event_type == "UNKNOWN"
	
	@patch('app.services.event_service.state')
	def test_create_event_from_alert_preserves_all_fields(self, mock_state, sample_alert):
		"""Test that all alert fields are properly mapped to event."""
		# Setup
		mock_state.event_exists.return_value = False
		mock_state.add_event = Mock()
		
		# Execute
		result = EventService.create_event_from_alert(sample_alert)
		
		# Assertions - verify all fields are set correctly
		assert result.event_key == "KFWD.TO.W.0015.2024"
		assert result.nws_alert_id == "https://api.weather.gov/alerts/urn:oid:2.49.0.1.840.0.1234567890"
		assert len(result.locations) == 1
		assert result.locations[0].ugc_code == "TXC113"
		assert result.is_active is True


class TestUpdateEventFromAlert:
	"""Test cases for EventService.update_event_from_alert."""
	
	@pytest.fixture
	def existing_event(self):
		"""Create an existing event for testing."""
		return Event(
			event_key="KFWD.TO.W.0015.2024",
			nws_alert_id="https://api.weather.gov/alerts/urn:oid:2.49.0.1.840.0.1234567890",
			episode_key="EP001",
			event_type="TOR",
			hr_event_type="Tornado Warning",
			locations=[
				Location(
					episode_key="EP001",
					event_key="KFWD.TO.W.0015.2024",
					state_fips="48",
					county_fips="113",
					ugc_code="TXC113",
					shape=[Coordinate(latitude=32.8, longitude=-97.5)],
					full_zone_ugc_endpoint="https://api.weather.gov/zones/forecast/TXC113"
				)
			],
			start_date=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
			expected_end_date=datetime(2024, 1, 15, 11, 0, 0, tzinfo=timezone.utc),
			actual_end_date=None,
			updated_at=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
			description="Original description",
			is_active=True,
			raw_vtec="/O.NEW.KFWD.TO.W.0015.240115T1000Z-240115T1100Z/",
			previous_ids=[],
			property_damage=1000,
			crops_damage=500,
			range_miles=5.0
		)
	
	@pytest.fixture
	def update_alert(self):
		"""Create an update alert for testing."""
		return FilteredNWSAlert(
			alert_id="https://api.weather.gov/alerts/urn:oid:2.49.0.1.840.0.1234567891",
			key="KFWD.TO.W.0015.2024",
			event_type="TOR",
			message_type="CON",
			is_watch=False,
			is_warning=True,
			severity="Extreme",
			urgency="Immediate",
			certainty="Observed",
			effective="2024-01-15T10:30:00-06:00",
			expires="2024-01-15T12:00:00-06:00",
			expected_end="2024-01-15T12:00:00-06:00",
			headline="Updated Tornado Warning",
			description="Updated description",
			raw_vtec="/O.CON.KFWD.TO.W.0015.240115T1030Z-240115T1200Z/",
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
	
	@patch('app.services.event_service.state')
	def test_update_event_standard_update(self, mock_state, existing_event, update_alert):
		"""Test standard update (CON message type) - merges locations and updates fields."""
		# Setup
		mock_state.get_event.return_value = existing_event
		mock_state.update_event = Mock()
		
		# Execute
		result = EventService.update_event_from_alert(update_alert)
		
		# Assertions
		assert isinstance(result, Event)
		assert result.event_key == existing_event.event_key
		assert result.nws_alert_id == update_alert.alert_id  # New alert ID
		assert result.episode_key == existing_event.episode_key  # Preserved
		assert result.event_type == existing_event.event_type  # Preserved
		assert result.start_date == existing_event.start_date  # Preserved
		assert result.expected_end_date is not None  # Updated
		assert result.actual_end_date == existing_event.actual_end_date  # Preserved
		assert "Updated Tornado Warning" in result.description
		assert "Updated description" in result.description
		assert result.raw_vtec == update_alert.raw_vtec  # Updated
		assert result.is_active == existing_event.is_active  # Preserved
		assert result.property_damage == existing_event.property_damage  # Preserved
		assert result.crops_damage == existing_event.crops_damage  # Preserved
		assert result.range_miles == existing_event.range_miles  # Preserved
		assert existing_event.nws_alert_id in result.previous_ids  # Old ID added
		mock_state.update_event.assert_called_once_with(result)
	
	@patch('app.services.event_service.state')
	def test_update_event_cor_message_type(self, mock_state, existing_event):
		"""Test COR (Correction) message type - replaces entire event."""
		# Setup
		mock_state.get_event.return_value = existing_event
		mock_state.update_event = Mock()
		
		cor_alert = FilteredNWSAlert(
			alert_id="https://api.weather.gov/alerts/urn:oid:2.49.0.1.840.0.1234567892",
			key="KFWD.TO.W.0015.2024",
			event_type="TOR",
			message_type="COR",
			is_watch=False,
			is_warning=True,
			severity="Extreme",
			urgency="Immediate",
			certainty="Observed",
			effective="2024-01-15T10:30:00-06:00",
			expires="2024-01-15T12:00:00-06:00",
			expected_end="2024-01-15T12:00:00-06:00",
			headline="Corrected Tornado Warning",
			description="Corrected description",
			raw_vtec="/O.COR.KFWD.TO.W.0015.240115T1030Z-240115T1200Z/",
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
					shape=[Coordinate(latitude=32.9, longitude=-97.4)],
					full_zone_ugc_endpoint="https://api.weather.gov/zones/forecast/TXC113"
				)
			]
		)
		
		# Execute
		result = EventService.update_event_from_alert(cor_alert)
		
		# Assertions
		assert result.nws_alert_id == cor_alert.alert_id  # New alert ID
		assert result.episode_key == existing_event.episode_key  # Preserved
		assert result.event_type == cor_alert.event_type  # From alert
		assert result.locations == cor_alert.locations  # Replaced
		assert result.raw_vtec == cor_alert.raw_vtec  # Replaced
		assert "Corrected Tornado Warning" in result.description
		assert result.is_active == existing_event.is_active  # Preserved
		assert result.property_damage == existing_event.property_damage  # Preserved
		assert result.actual_end_date == existing_event.actual_end_date  # Preserved
		assert existing_event.nws_alert_id in result.previous_ids
	
	@patch('app.services.event_service.state')
	def test_update_event_upg_message_type(self, mock_state, existing_event):
		"""Test UPG (Update) message type - replaces entire event."""
		# Setup
		mock_state.get_event.return_value = existing_event
		mock_state.update_event = Mock()
		
		upg_alert = FilteredNWSAlert(
			alert_id="https://api.weather.gov/alerts/urn:oid:2.49.0.1.840.0.1234567893",
			key="KFWD.TO.W.0015.2024",
			event_type="TOR",
			message_type="UPG",
			is_watch=False,
			is_warning=True,
			severity="Extreme",
			urgency="Immediate",
			certainty="Observed",
			effective="2024-01-15T10:30:00-06:00",
			expires="2024-01-15T12:00:00-06:00",
			expected_end="2024-01-15T12:00:00-06:00",
			headline="Upgraded Tornado Warning",
			description="Upgraded description",
			raw_vtec="/O.UPG.KFWD.TO.W.0015.240115T1030Z-240115T1200Z/",
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
					shape=[Coordinate(latitude=32.9, longitude=-97.4)],
					full_zone_ugc_endpoint="https://api.weather.gov/zones/forecast/TXC113"
				)
			]
		)
		
		# Execute
		result = EventService.update_event_from_alert(upg_alert)
		
		# Assertions
		assert result.nws_alert_id == upg_alert.alert_id
		assert result.locations == upg_alert.locations  # Replaced
		assert result.raw_vtec == upg_alert.raw_vtec  # Replaced
		assert "Upgraded Tornado Warning" in result.description
		assert existing_event.nws_alert_id in result.previous_ids
	
	@patch('app.services.event_service.state')
	def test_update_event_can_message_type(self, mock_state, existing_event):
		"""Test CAN (Cancel) message type - marks event as inactive."""
		# Setup
		mock_state.get_event.return_value = existing_event
		mock_state.update_event = Mock()
		
		can_alert = FilteredNWSAlert(
			alert_id="https://api.weather.gov/alerts/urn:oid:2.49.0.1.840.0.1234567894",
			key="KFWD.TO.W.0015.2024",
			event_type="TOR",
			message_type="CAN",
			is_watch=False,
			is_warning=True,
			severity="Extreme",
			urgency="Immediate",
			certainty="Observed",
			effective="2024-01-15T10:30:00-06:00",
			expires="2024-01-15T11:00:00-06:00",
			expected_end="2024-01-15T11:00:00-06:00",
			headline="Cancelled",
			description="Warning cancelled",
			raw_vtec="/O.CAN.KFWD.TO.W.0015.240115T1030Z-240115T1100Z/",
			affected_zones_ugc_endpoints=["https://api.weather.gov/zones/forecast/TXC113"],
			affected_zones_raw_ugc_codes=["TXC113"],
			referenced_alerts=[],
			locations=[]
		)
		
		# Execute
		result = EventService.update_event_from_alert(can_alert)
		
		# Assertions
		assert result.is_active is False  # Marked inactive
		assert result.actual_end_date is not None  # Set from expected_end
		assert result.nws_alert_id == can_alert.alert_id
		assert result.episode_key == existing_event.episode_key  # Preserved
		assert result.event_type == existing_event.event_type  # Preserved
		assert result.locations == existing_event.locations  # Preserved
		assert result.description == existing_event.description  # Preserved
		assert result.property_damage == existing_event.property_damage  # Preserved
		assert existing_event.nws_alert_id in result.previous_ids
	
	@patch('app.services.event_service.state')
	def test_update_event_exp_message_type(self, mock_state, existing_event):
		"""Test EXP (Expired) message type - marks event as inactive."""
		# Setup
		mock_state.get_event.return_value = existing_event
		mock_state.update_event = Mock()
		
		exp_alert = FilteredNWSAlert(
			alert_id="https://api.weather.gov/alerts/urn:oid:2.49.0.1.840.0.1234567895",
			key="KFWD.TO.W.0015.2024",
			event_type="TOR",
			message_type="EXP",
			is_watch=False,
			is_warning=True,
			severity="Extreme",
			urgency="Immediate",
			certainty="Observed",
			effective="2024-01-15T10:30:00-06:00",
			expires="2024-01-15T11:00:00-06:00",
			expected_end="2024-01-15T11:00:00-06:00",
			headline="Expired",
			description="Warning expired",
			raw_vtec="/O.EXP.KFWD.TO.W.0015.240115T1030Z-240115T1100Z/",
			affected_zones_ugc_endpoints=["https://api.weather.gov/zones/forecast/TXC113"],
			affected_zones_raw_ugc_codes=["TXC113"],
			referenced_alerts=[],
			locations=[]
		)
		
		# Execute
		result = EventService.update_event_from_alert(exp_alert)
		
		# Assertions
		assert result.is_active is False
		assert result.actual_end_date is not None
		assert existing_event.nws_alert_id in result.previous_ids
	
	@patch('app.services.event_service.state')
	def test_update_event_merges_locations(self, mock_state, existing_event):
		"""Test that standard update merges locations without duplicates."""
		# Setup
		mock_state.get_event.return_value = existing_event
		mock_state.update_event = Mock()
		
		# Create alert with new location
		new_location = Location(
			episode_key=None,
			event_key="KFWD.TO.W.0015.2024",
			state_fips="48",
			county_fips="215",
			ugc_code="TXC215",
			shape=[Coordinate(latitude=33.0, longitude=-97.0)],
			full_zone_ugc_endpoint="https://api.weather.gov/zones/forecast/TXC215"
		)
		
		update_alert = FilteredNWSAlert(
			alert_id="https://api.weather.gov/alerts/urn:oid:2.49.0.1.840.0.1234567896",
			key="KFWD.TO.W.0015.2024",
			event_type="TOR",
			message_type="CON",
			is_watch=False,
			is_warning=True,
			severity="Extreme",
			urgency="Immediate",
			certainty="Observed",
			effective="2024-01-15T10:30:00-06:00",
			expires="2024-01-15T12:00:00-06:00",
			expected_end="2024-01-15T12:00:00-06:00",
			headline="Updated",
			description="Updated",
			raw_vtec="/O.CON.KFWD.TO.W.0015.240115T1030Z-240115T1200Z/",
			affected_zones_ugc_endpoints=["https://api.weather.gov/zones/forecast/TXC215"],
			affected_zones_raw_ugc_codes=["TXC215"],
			referenced_alerts=[],
			locations=[new_location]
		)
		
		# Execute
		result = EventService.update_event_from_alert(update_alert)
		
		# Assertions
		assert len(result.locations) == 2  # Original + new
		ugc_codes = {loc.ugc_code for loc in result.locations}
		assert "TXC113" in ugc_codes
		assert "TXC215" in ugc_codes
	
	@patch('app.services.event_service.state')
	def test_update_event_no_duplicate_locations(self, mock_state, existing_event):
		"""Test that duplicate locations (same ugc_code) are not added."""
		# Setup
		mock_state.get_event.return_value = existing_event
		mock_state.update_event = Mock()
		
		# Create alert with same location as existing
		duplicate_location = Location(
			episode_key=None,
			event_key="KFWD.TO.W.0015.2024",
			state_fips="48",
			county_fips="113",
			ugc_code="TXC113",  # Same as existing
			shape=[Coordinate(latitude=32.8, longitude=-97.5)],
			full_zone_ugc_endpoint="https://api.weather.gov/zones/forecast/TXC113"
		)
		
		update_alert = FilteredNWSAlert(
			alert_id="https://api.weather.gov/alerts/urn:oid:2.49.0.1.840.0.1234567897",
			key="KFWD.TO.W.0015.2024",
			event_type="TOR",
			message_type="CON",
			is_watch=False,
			is_warning=True,
			severity="Extreme",
			urgency="Immediate",
			certainty="Observed",
			effective="2024-01-15T10:30:00-06:00",
			expires="2024-01-15T12:00:00-06:00",
			expected_end="2024-01-15T12:00:00-06:00",
			headline="Updated",
			description="Updated",
			raw_vtec="/O.CON.KFWD.TO.W.0015.240115T1030Z-240115T1200Z/",
			affected_zones_ugc_endpoints=["https://api.weather.gov/zones/forecast/TXC113"],
			affected_zones_raw_ugc_codes=["TXC113"],
			referenced_alerts=[],
			locations=[duplicate_location]
		)
		
		# Execute
		result = EventService.update_event_from_alert(update_alert)
		
		# Assertions
		assert len(result.locations) == 1  # No duplicate added
		assert result.locations[0].ugc_code == "TXC113"
	
	@patch('app.services.event_service.state')
	def test_update_event_not_found_error(self, mock_state, update_alert):
		"""Test that NotFoundError is raised when event doesn't exist."""
		# Setup
		mock_state.get_event.return_value = None
		
		# Execute & Assert
		with pytest.raises(NotFoundError):
			EventService.update_event_from_alert(update_alert)
	
	@patch('app.services.event_service.state')
	def test_update_event_tracks_previous_ids(self, mock_state, existing_event, update_alert):
		"""Test that previous alert IDs are tracked correctly."""
		# Setup
		existing_event.previous_ids = ["old-alert-1", "old-alert-2"]
		mock_state.get_event.return_value = existing_event
		mock_state.update_event = Mock()
		
		# Execute
		result = EventService.update_event_from_alert(update_alert)
		
		# Assertions
		assert len(result.previous_ids) == 3  # 2 old + 1 current
		assert "old-alert-1" in result.previous_ids
		assert "old-alert-2" in result.previous_ids
		assert existing_event.nws_alert_id in result.previous_ids
	
	@patch('app.services.event_service.state')
	def test_update_event_no_duplicate_previous_id(self, mock_state, existing_event):
		"""Test that current alert ID is not added to previous_ids if already there."""
		# Setup
		existing_event.previous_ids = [existing_event.nws_alert_id]  # Already in list
		mock_state.get_event.return_value = existing_event
		mock_state.update_event = Mock()
		
		update_alert = FilteredNWSAlert(
			alert_id="https://api.weather.gov/alerts/urn:oid:2.49.0.1.840.0.1234567898",
			key="KFWD.TO.W.0015.2024",
			event_type="TOR",
			message_type="CON",
			is_watch=False,
			is_warning=True,
			severity="Extreme",
			urgency="Immediate",
			certainty="Observed",
			effective="2024-01-15T10:30:00-06:00",
			expires="2024-01-15T12:00:00-06:00",
			expected_end="2024-01-15T12:00:00-06:00",
			headline="Updated",
			description="Updated",
			raw_vtec="/O.CON.KFWD.TO.W.0015.240115T1030Z-240115T1200Z/",
			affected_zones_ugc_endpoints=[],
			affected_zones_raw_ugc_codes=[],
			referenced_alerts=[],
			locations=[]
		)
		
		# Execute
		result = EventService.update_event_from_alert(update_alert)
		
		# Assertions - should only have one instance of the old alert ID
		assert result.previous_ids.count(existing_event.nws_alert_id) == 1
	
	@patch('app.services.event_service.state')
	def test_update_event_case_insensitive_message_type(self, mock_state, existing_event):
		"""Test that message type comparison is case-insensitive."""
		# Setup
		mock_state.get_event.return_value = existing_event
		mock_state.update_event = Mock()
		
		# Use lowercase message type
		can_alert = FilteredNWSAlert(
			alert_id="https://api.weather.gov/alerts/urn:oid:2.49.0.1.840.0.1234567899",
			key="KFWD.TO.W.0015.2024",
			event_type="TOR",
			message_type="can",  # lowercase
			is_watch=False,
			is_warning=True,
			severity="Extreme",
			urgency="Immediate",
			certainty="Observed",
			effective="2024-01-15T10:30:00-06:00",
			expires="2024-01-15T11:00:00-06:00",
			expected_end="2024-01-15T11:00:00-06:00",
			headline="Cancelled",
			description="Warning cancelled",
			raw_vtec="/O.CAN.KFWD.TO.W.0015.240115T1030Z-240115T1100Z/",
			affected_zones_ugc_endpoints=[],
			affected_zones_raw_ugc_codes=[],
			referenced_alerts=[],
			locations=[]
		)
		
		# Execute
		result = EventService.update_event_from_alert(can_alert)
		
		# Assertions - should be treated as CAN
		assert result.is_active is False
	
	@patch('app.services.event_service.state')
	def test_update_event_with_missing_expected_end(self, mock_state, existing_event):
		"""Test update when expected_end is None."""
		# Setup
		mock_state.get_event.return_value = existing_event
		mock_state.update_event = Mock()
		
		update_alert = FilteredNWSAlert(
			alert_id="https://api.weather.gov/alerts/urn:oid:2.49.0.1.840.0.1234567900",
			key="KFWD.TO.W.0015.2024",
			event_type="TOR",
			message_type="CON",
			is_watch=False,
			is_warning=True,
			severity="Extreme",
			urgency="Immediate",
			certainty="Observed",
			effective="2024-01-15T10:30:00-06:00",
			expires="2024-01-15T12:00:00-06:00",
			expected_end=None,  # Missing
			headline="Updated",
			description="Updated",
			raw_vtec="/O.CON.KFWD.TO.W.0015.240115T1030Z-240115T1200Z/",
			affected_zones_ugc_endpoints=[],
			affected_zones_raw_ugc_codes=[],
			referenced_alerts=[],
			locations=[]
		)
		
		# Execute
		result = EventService.update_event_from_alert(update_alert)
		
		# Assertions
		assert result.expected_end_date is None  # Should handle None gracefully
		# For CAN/EXP, actual_end_date should also be None if expected_end is None
		if update_alert.message_type in ["CAN", "EXP"]:
			# This would be tested in a separate test, but here we're testing CON
			pass
