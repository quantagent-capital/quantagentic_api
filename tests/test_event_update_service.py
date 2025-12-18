"""
Unit tests for EventUpdateService.
"""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timezone, timedelta
from app.services.event_update_service import EventUpdateService
from app.services.event_crud_service import EventCRUDService
from app.shared_models.nws_poller_models import FilteredNWSAlert
from app.schemas.event import Event
from app.schemas.location import Location, Coordinate
from app.exceptions import NotFoundError
from app.exceptions.base import ConflictError
from app.utils.event_types import NWS_WARNING_CODES

class TestUpdateEventFromAlert:
	"""Test cases for EventUpdateService.update_event_from_alert."""
	
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
	
	@patch('app.services.event_crud_service.EventCRUDService.get_event')
	@patch('app.services.event_update_service.state')
	def test_update_event_standard_update(self, mock_state, mock_get_event, existing_event, update_alert):
		"""Test standard update (CON message type) - merges locations and updates fields."""
		# Setup
		mock_get_event.return_value = existing_event
		mock_state.update_event = Mock()
		
		# Execute
		result = EventUpdateService.update_event_from_alert(update_alert)
		
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
	
	@patch('app.services.event_crud_service.EventCRUDService.get_event')
	@patch('app.services.event_update_service.state')
	def test_update_event_cor_message_type(self, mock_state, mock_get_event, existing_event):
		"""Test COR (Correction) message type - replaces entire event."""
		# Setup
		mock_get_event.return_value = existing_event
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
		result = EventUpdateService.update_event_from_alert(cor_alert)
		
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
	
	@patch('app.services.event_crud_service.EventCRUDService.get_event')
	@patch('app.services.event_update_service.state')
	def test_update_event_upg_message_type(self, mock_state, mock_get_event, existing_event):
		"""Test UPG (Update) message type - replaces entire event."""
		# Setup
		mock_get_event.return_value = existing_event
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
		result = EventUpdateService.update_event_from_alert(upg_alert)
		
		# Assertions
		assert result.nws_alert_id == upg_alert.alert_id
		assert result.locations == upg_alert.locations  # Replaced
		assert result.raw_vtec == upg_alert.raw_vtec  # Replaced
		assert "Upgraded Tornado Warning" in result.description
		assert existing_event.nws_alert_id in result.previous_ids
	
	@patch('app.services.event_crud_service.EventCRUDService.get_event')
	@patch('app.services.event_update_service.state')
	def test_update_event_can_message_type(self, mock_state, mock_get_event, existing_event):
		"""Test CAN (Cancel) message type - returns None as it's handled by check_completed_events."""
		# Setup
		mock_get_event.return_value = existing_event
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
		result = EventUpdateService.update_event_from_alert(can_alert)
		
		# Assertions - CAN/EXP are now handled by check_completed_events, so this returns None
		assert result is None
		# Should not update event (handled by check_completed_events instead)
		mock_state.update_event.assert_not_called()
	
	@patch('app.services.event_crud_service.EventCRUDService.get_event')
	@patch('app.services.event_update_service.state')
	def test_update_event_exp_message_type(self, mock_state, mock_get_event, existing_event):
		"""Test EXP (Expired) message type - returns None as it's handled by check_completed_events."""
		# Setup
		mock_get_event.return_value = existing_event
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
		result = EventUpdateService.update_event_from_alert(exp_alert)
		
		# Assertions - CAN/EXP are now handled by check_completed_events, so this returns None
		assert result is None
		# Should not update event (handled by check_completed_events instead)
		mock_state.update_event.assert_not_called()
	
	@patch('app.services.event_crud_service.EventCRUDService.get_event')
	@patch('app.services.event_update_service.state')
	def test_update_event_merges_locations(self, mock_state, mock_get_event, existing_event):
		"""Test that standard update merges locations without duplicates."""
		# Setup
		mock_get_event.return_value = existing_event
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
		result = EventUpdateService.update_event_from_alert(update_alert)
		
		# Assertions
		assert len(result.locations) == 2  # Original + new
		ugc_codes = {loc.ugc_code for loc in result.locations}
		assert "TXC113" in ugc_codes
		assert "TXC215" in ugc_codes
	
	@patch('app.services.event_crud_service.EventCRUDService.get_event')
	@patch('app.services.event_update_service.state')
	def test_update_event_no_duplicate_locations(self, mock_state, mock_get_event, existing_event):
		"""Test that duplicate locations (same ugc_code) are not added."""
		# Setup
		mock_get_event.return_value = existing_event
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
		result = EventUpdateService.update_event_from_alert(update_alert)
		
		# Assertions
		assert len(result.locations) == 1  # No duplicate added
		assert result.locations[0].ugc_code == "TXC113"
	
	@patch('app.services.event_crud_service.EventCRUDService.get_event')
	@patch('app.services.event_update_service.state')
	def test_update_event_not_found_error(self, mock_state, mock_get_event, update_alert):
		"""Test that NotFoundError is raised when event doesn't exist."""
		# Setup
		from app.exceptions import NotFoundError
		mock_get_event.side_effect = NotFoundError("Event", update_alert.key)
		
		# Execute & Assert
		with pytest.raises(NotFoundError):
			EventUpdateService.update_event_from_alert(update_alert)
	
	@patch('app.services.event_crud_service.EventCRUDService.get_event')
	@patch('app.services.event_update_service.state')
	def test_update_event_tracks_previous_ids(self, mock_state, mock_get_event, existing_event, update_alert):
		"""Test that previous alert IDs are tracked correctly."""
		# Setup
		existing_event.previous_ids = ["old-alert-1", "old-alert-2"]
		mock_get_event.return_value = existing_event
		mock_state.update_event = Mock()
		
		# Execute
		result = EventUpdateService.update_event_from_alert(update_alert)
		
		# Assertions
		assert len(result.previous_ids) == 3  # 2 old + 1 current
		assert "old-alert-1" in result.previous_ids
		assert "old-alert-2" in result.previous_ids
		assert existing_event.nws_alert_id in result.previous_ids
	
	@patch('app.services.event_crud_service.EventCRUDService.get_event')
	@patch('app.services.event_update_service.state')
	def test_update_event_no_duplicate_previous_id(self, mock_state, mock_get_event, existing_event):
		"""Test that current alert ID is not added to previous_ids if already there."""
		# Setup
		existing_event.previous_ids = [existing_event.nws_alert_id]  # Already in list
		mock_get_event.return_value = existing_event
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
		result = EventUpdateService.update_event_from_alert(update_alert)
		
		# Assertions - should only have one instance of the old alert ID
		assert result.previous_ids.count(existing_event.nws_alert_id) == 1
	
	@patch('app.services.event_crud_service.EventCRUDService.get_event')
	@patch('app.services.event_update_service.state')
	def test_update_event_case_insensitive_message_type(self, mock_state, mock_get_event, existing_event):
		"""Test that message type comparison is case-insensitive."""
		# Setup
		mock_get_event.return_value = existing_event
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
		result = EventUpdateService.update_event_from_alert(can_alert)
		
		# Assertions - CAN/EXP are now handled by check_completed_events, so this returns None
		assert result is None
	
	@patch('app.services.event_crud_service.EventCRUDService.get_event')
	@patch('app.services.event_update_service.state')
	def test_update_event_with_missing_expected_end(self, mock_state, mock_get_event, existing_event):
		"""Test update when expected_end is None."""
		# Setup
		mock_get_event.return_value = existing_event
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
		result = EventUpdateService.update_event_from_alert(update_alert)
		
		# Assertions
		assert result.expected_end_date is None  # Should handle None gracefully
		# For CAN/EXP, actual_end_date should also be None if expected_end is None
		if update_alert.message_type in ["CAN", "EXP"]:
			# This would be tested in a separate test, but here we're testing CON
			pass




class TestConfirmedFunctionality:
	"""Test cases for confirmed field functionality in event updates."""
	
	@patch('app.services.event_crud_service.EventCRUDService.get_event')
	@patch('app.services.event_update_service.state')
	def test_update_event_with_observed_certainty_sets_confirmed_true(self, mock_state, mock_get_event):
		"""Test that updating an event with certainty='Observed' sets confirmed=True."""
		existing_event = Event(
			event_key="KFWD.TO.W.0015.2024",
			nws_alert_id="alert-1",
			event_type="TOR",
			start_date=datetime.now(timezone.utc),
			description="Existing event",
			is_active=True,
			confirmed=False,
			raw_vtec="/O.NEW.KFWD.TO.W.0015.240115T1000Z-240115T1100Z/"
		)
		
		update_alert = FilteredNWSAlert(
			alert_id="alert-2",
			key="KFWD.TO.W.0015.2024",
			event_type="TOR",
			message_type="CON",
			is_watch=False,
			is_warning=True,
			severity="Extreme",
			urgency="Immediate",
			certainty="Observed",
			effective="2024-01-15T10:00:00-06:00",
			expires="2024-01-15T11:00:00-06:00",
			expected_end="2024-01-15T11:00:00-06:00",
			headline="Updated",
			description="Updated description",
			raw_vtec="/O.CON.KFWD.TO.W.0015.240115T1000Z-240115T1100Z/",
			affected_zones_ugc_endpoints=[],
			affected_zones_raw_ugc_codes=[],
			referenced_alerts=[],
			locations=[]
		)
		
		mock_get_event.return_value = existing_event
		mock_state.update_event = Mock()
		
		result = EventUpdateService.update_event_from_alert(update_alert)
		
		assert result.confirmed is True
	
	@patch('app.services.event_crud_service.EventCRUDService.get_event')
	@patch('app.services.event_update_service.state')
	def test_update_event_preserves_confirmed_if_already_true(self, mock_state, mock_get_event):
		"""Test that updating an event preserves confirmed=True if already set."""
		existing_event = Event(
			event_key="KFWD.TO.W.0015.2024",
			nws_alert_id="alert-1",
			event_type="TOR",
			start_date=datetime.now(timezone.utc),
			description="Existing event",
			is_active=True,
			confirmed=True,
			raw_vtec="/O.NEW.KFWD.TO.W.0015.240115T1000Z-240115T1100Z/"
		)
		
		update_alert = FilteredNWSAlert(
			alert_id="alert-2",
			key="KFWD.TO.W.0015.2024",
			event_type="TOR",
			message_type="CON",
			is_watch=False,
			is_warning=True,
			severity="Extreme",
			urgency="Immediate",
			certainty="Likely",  # Not observed
			effective="2024-01-15T10:00:00-06:00",
			expires="2024-01-15T11:00:00-06:00",
			expected_end="2024-01-15T11:00:00-06:00",
			headline="Updated",
			description="Updated description",
			raw_vtec="/O.CON.KFWD.TO.W.0015.240115T1000Z-240115T1100Z/",
			affected_zones_ugc_endpoints=[],
			affected_zones_raw_ugc_codes=[],
			referenced_alerts=[],
			locations=[]
		)
		
		mock_get_event.return_value = existing_event
		mock_state.update_event = Mock()
		
		result = EventUpdateService.update_event_from_alert(update_alert)
		
		# Should preserve confirmed=True even though new alert is not observed
		assert result.confirmed is True
	
	@patch('app.services.event_crud_service.EventCRUDService.get_event')
	@patch('app.services.event_update_service.state')
	def test_replace_event_with_observed_certainty_sets_confirmed_true(self, mock_state, mock_get_event):
		"""Test that replacing an event (COR/UPG) with certainty='Observed' sets confirmed=True."""
		existing_event = Event(
			event_key="KFWD.TO.W.0015.2024",
			nws_alert_id="alert-1",
			event_type="TOR",
			start_date=datetime.now(timezone.utc),
			description="Existing event",
			is_active=True,
			confirmed=False,
			raw_vtec="/O.NEW.KFWD.TO.W.0015.240115T1000Z-240115T1100Z/"
		)
		
		cor_alert = FilteredNWSAlert(
			alert_id="alert-2",
			key="KFWD.TO.W.0015.2024",
			event_type="TOR",
			message_type="COR",
			is_watch=False,
			is_warning=True,
			severity="Extreme",
			urgency="Immediate",
			certainty="Observed",
			effective="2024-01-15T10:00:00-06:00",
			expires="2024-01-15T11:00:00-06:00",
			expected_end="2024-01-15T11:00:00-06:00",
			headline="Corrected",
			description="Corrected description",
			raw_vtec="/O.COR.KFWD.TO.W.0015.240115T1000Z-240115T1100Z/",
			affected_zones_ugc_endpoints=[],
			affected_zones_raw_ugc_codes=[],
			referenced_alerts=[],
			locations=[]
		)
		
		mock_get_event.return_value = existing_event
		mock_state.update_event = Mock()
		
		result = EventUpdateService.update_event_from_alert(cor_alert)
		
		assert result.confirmed is True
