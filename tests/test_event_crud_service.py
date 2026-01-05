"""
Unit tests for EventCRUDService.
"""
import pytest
from unittest.mock import Mock, patch, PropertyMock
from datetime import datetime, timezone, timedelta
from app.services.event_crud_service import EventCRUDService
from app.schemas.event import Event

class TestGetEvents:
	"""Test cases for EventCRUDService.get_events filtering functionality."""
	
	@patch('app.services.event_crud_service.state')
	def test_get_events_returns_active_events_by_default(self, mock_state):
		"""Test get_events returns only active events by default (active_only=True)."""
		active_event = Event(
			event_key="event-1",
			nws_alert_id="alert-1",
			event_type="TOR",
			start_date=datetime.now(timezone.utc),
			description="Active event",
			is_active=True,
			raw_vtec="/O.NEW.KFWD.TO.W.0015.240115T1000Z-240115T1100Z/"
		)
		
		inactive_event = Event(
			event_key="event-2",
			nws_alert_id="alert-2",
			event_type="TOR",
			start_date=datetime.now(timezone.utc),
			description="Inactive event",
			is_active=False,
			raw_vtec="/O.NEW.KFWD.TO.W.0015.240115T1000Z-240115T1100Z/"
		)
		
		mock_state.events = [active_event, inactive_event]
		mock_state.active_events = [active_event]
		
		result = EventCRUDService.get_events()
		
		# Should return only active events by default
		assert len(result) == 1
		assert result[0].event_key == "event-1"
	
	@patch('app.services.event_crud_service.state')
	def test_get_events_with_active_only_true_returns_only_active_events(self, mock_state):
		"""Test get_events with active_only=True returns only active events."""
		active_event_1 = Event(
			event_key="active-1",
			nws_alert_id="alert-1",
			event_type="TOR",
			start_date=datetime.now(timezone.utc),
			description="Active event 1",
			is_active=True,
			raw_vtec="/O.NEW.KFWD.TO.W.0015.240115T1000Z-240115T1100Z/"
		)
		
		active_event_2 = Event(
			event_key="active-2",
			nws_alert_id="alert-2",
			event_type="TOR",
			start_date=datetime.now(timezone.utc),
			description="Active event 2",
			is_active=True,
			raw_vtec="/O.NEW.KFWD.TO.W.0015.240115T1000Z-240115T1100Z/"
		)
		
		inactive_event = Event(
			event_key="inactive-1",
			nws_alert_id="alert-3",
			event_type="TOR",
			start_date=datetime.now(timezone.utc),
			description="Inactive event",
			is_active=False,
			raw_vtec="/O.NEW.KFWD.TO.W.0015.240115T1000Z-240115T1100Z/"
		)
		
		mock_state.events = [active_event_1, inactive_event, active_event_2]
		mock_state.active_events = [active_event_1, active_event_2]
		
		result = EventCRUDService.get_events(active_only=True)
		
		# Should return only active events
		assert len(result) == 2
		event_keys = {event.event_key for event in result}
		assert "active-1" in event_keys
		assert "active-2" in event_keys
		assert "inactive-1" not in event_keys
	
	@patch('app.services.event_crud_service.state')
	def test_get_events_with_active_only_false_returns_all_events(self, mock_state):
		"""Test get_events with active_only=False returns all events."""
		active_event = Event(
			event_key="active-1",
			nws_alert_id="alert-1",
			event_type="TOR",
			start_date=datetime.now(timezone.utc),
			description="Active event",
			is_active=True,
			raw_vtec="/O.NEW.KFWD.TO.W.0015.240115T1000Z-240115T1100Z/"
		)
		
		inactive_event = Event(
			event_key="inactive-1",
			nws_alert_id="alert-2",
			event_type="TOR",
			start_date=datetime.now(timezone.utc),
			description="Inactive event",
			is_active=False,
			raw_vtec="/O.NEW.KFWD.TO.W.0015.240115T1000Z-240115T1100Z/"
		)
		
		mock_state.events = [active_event, inactive_event]
		
		result = EventCRUDService.get_events(active_only=False)
		
		# Should return all events
		assert len(result) == 2
		event_keys = {event.event_key for event in result}
		assert "active-1" in event_keys
		assert "inactive-1" in event_keys
	
	@patch('app.services.event_crud_service.state')
	def test_get_events_with_active_only_returns_empty_when_no_active_events(self, mock_state):
		"""Test get_events with active_only=True returns empty list when no active events."""
		inactive_event_1 = Event(
			event_key="inactive-1",
			nws_alert_id="alert-1",
			event_type="TOR",
			start_date=datetime.now(timezone.utc),
			description="Inactive event 1",
			is_active=False,
			raw_vtec="/O.NEW.KFWD.TO.W.0015.240115T1000Z-240115T1100Z/"
		)
		
		inactive_event_2 = Event(
			event_key="inactive-2",
			nws_alert_id="alert-2",
			event_type="TOR",
			start_date=datetime.now(timezone.utc),
			description="Inactive event 2",
			is_active=False,
			raw_vtec="/O.NEW.KFWD.TO.W.0015.240115T1000Z-240115T1100Z/"
		)
		
		mock_state.events = [inactive_event_1, inactive_event_2]
		mock_state.active_events = []
		
		result = EventCRUDService.get_events(active_only=True)
		
		# Should return empty list
		assert len(result) == 0




class TestStateActiveEvents:
	"""Test cases for State.active_events property."""
	
	@patch('app.state.quantagent_redis')
	def test_active_events_filters_by_is_active(self, mock_redis):
		"""Test that active_events only returns events where is_active=True."""
		from app.state import State
		
		# Create mock events
		active_event = Event(
			event_key="active-event",
			nws_alert_id="alert-1",
			event_type="TOR",
			start_date=datetime.now(timezone.utc),
			description="Active",
			is_active=True,
			raw_vtec="/O.NEW.KFWD.TO.W.0015.240115T1000Z-240115T1100Z/"
		)
		
		inactive_event = Event(
			event_key="inactive-event",
			nws_alert_id="alert-2",
			event_type="TOR",
			start_date=datetime.now(timezone.utc),
			description="Inactive",
			is_active=False,
			raw_vtec="/O.NEW.KFWD.TO.W.0015.240115T1000Z-240115T1100Z/"
		)
		
		# Mock Redis to return both events using read_all_as_schema
		mock_redis.get_all_keys.return_value = ["event:active-event", "event:inactive-event"]
		mock_redis.read_all_as_schema.return_value = [active_event, inactive_event]
		
		state = State()
		result = state.active_events
		
		# Should only return active event
		assert len(result) == 1
		assert result[0].event_key == "active-event"
		assert result[0].is_active is True
	
	@patch('app.state.quantagent_redis')
	def test_active_events_returns_empty_list_when_no_active_events(self, mock_redis):
		"""Test that active_events returns empty list when no active events exist."""
		from app.state import State
		
		inactive_event = Event(
			event_key="inactive-event",
			nws_alert_id="alert-1",
			event_type="TOR",
			start_date=datetime.now(timezone.utc),
			description="Inactive",
			is_active=False,
			raw_vtec="/O.NEW.KFWD.TO.W.0015.240115T1000Z-240115T1100Z/"
		)
		
		mock_redis.get_all_keys.return_value = ["event:inactive-event"]
		mock_redis.read_all_as_schema.return_value = [inactive_event]
		
		state = State()
		result = state.active_events
		
		assert len(result) == 0
	
	@patch('app.state.quantagent_redis')
	def test_active_events_handles_mixed_active_inactive(self, mock_redis):
		"""Test that active_events correctly filters mixed active/inactive events."""
		from app.state import State
		
		active_event_1 = Event(
			event_key="active-1",
			nws_alert_id="alert-1",
			event_type="TOR",
			start_date=datetime.now(timezone.utc),
			description="Active 1",
			is_active=True,
			raw_vtec="/O.NEW.KFWD.TO.W.0015.240115T1000Z-240115T1100Z/"
		)
		
		active_event_2 = Event(
			event_key="active-2",
			nws_alert_id="alert-2",
			event_type="TOR",
			start_date=datetime.now(timezone.utc),
			description="Active 2",
			is_active=True,
			raw_vtec="/O.NEW.KFWD.TO.W.0015.240115T1000Z-240115T1100Z/"
		)
		
		inactive_event = Event(
			event_key="inactive",
			nws_alert_id="alert-3",
			event_type="TOR",
			start_date=datetime.now(timezone.utc),
			description="Inactive",
			is_active=False,
			raw_vtec="/O.NEW.KFWD.TO.W.0015.240115T1000Z-240115T1100Z/"
		)
		
		mock_redis.get_all_keys.return_value = ["event:active-1", "event:inactive", "event:active-2"]
		mock_redis.read_all_as_schema.return_value = [active_event_1, inactive_event, active_event_2]
		
		state = State()
		result = state.active_events
		
		# Should return only the 2 active events
		assert len(result) == 2
		event_keys = {event.event_key for event in result}
		assert "active-1" in event_keys
		assert "active-2" in event_keys
		assert "inactive" not in event_keys


class TestDeactivateEvent:
	"""Test cases for EventCRUDService.deactivate_event method."""
	
	@patch('app.services.event_crud_service.state')
	def test_deactivate_event_success(self, mock_state):
		"""Test successful deactivation of an event."""
		from app.exceptions import NotFoundError
		
		# Create an active event
		start_date = datetime.now(timezone.utc) - timedelta(hours=2)
		expected_end_date = datetime.now(timezone.utc) + timedelta(hours=1)
		original_updated_at = datetime.now(timezone.utc) - timedelta(minutes=30)
		
		active_event = Event(
			event_key="event-1",
			nws_alert_id="alert-1",
			episode_key="episode-1",
			event_type="TOR",
			hr_event_type="Tornado Warning",
			start_date=start_date,
			expected_end_date=expected_end_date,
			actual_end_date=None,
			updated_at=original_updated_at,
			description="Test event",
			is_active=True,
			confirmed=False,
			raw_vtec="/O.NEW.KFWD.TO.W.0015.240115T1000Z-240115T1100Z/",
			office="KFWD",
			property_damage=None,
			crops_damage=None,
			range_miles=None,
			previous_ids=[],
			locations=[]
		)
		
		# Mock state.get_event to return the active event
		mock_state.get_event.return_value = active_event
		
		# Capture the time before deactivation
		before_deactivation = datetime.now(timezone.utc)
		
		# Deactivate the event
		result = EventCRUDService.deactivate_event("event-1")
		
		# Capture the time after deactivation
		after_deactivation = datetime.now(timezone.utc)
		
		# Verify the event was retrieved
		mock_state.get_event.assert_called_once_with("event-1")
		
		# Verify the event was updated in state
		mock_state.update_event.assert_called_once()
		updated_event = mock_state.update_event.call_args[0][0]
		
		# Verify the result matches the updated event
		assert result == updated_event
		
		# Verify is_active is False
		assert result.is_active is False
		assert updated_event.is_active is False
		
		# Verify actual_end_date is set and within reasonable time range
		assert result.actual_end_date is not None
		assert updated_event.actual_end_date is not None
		assert before_deactivation <= result.actual_end_date <= after_deactivation
		
		# Verify updated_at is set and within reasonable time range
		assert result.updated_at is not None
		assert updated_event.updated_at is not None
		assert before_deactivation <= result.updated_at <= after_deactivation
		
		# Verify all other fields are preserved
		assert result.event_key == "event-1"
		assert result.nws_alert_id == "alert-1"
		assert result.episode_key == "episode-1"
		assert result.event_type == "TOR"
		assert result.hr_event_type == "Tornado Warning"
		assert result.start_date == start_date
		assert result.expected_end_date == expected_end_date
		assert result.description == "Test event"
		assert result.confirmed is False
		assert result.raw_vtec == "/O.NEW.KFWD.TO.W.0015.240115T1000Z-240115T1100Z/"
		assert result.office == "KFWD"
		assert result.property_damage is None
		assert result.crops_damage is None
		assert result.range_miles is None
		assert result.previous_ids == []
		assert result.locations == []
	
	@patch('app.services.event_crud_service.state')
	def test_deactivate_event_not_found(self, mock_state):
		"""Test deactivate_event raises NotFoundError when event doesn't exist."""
		from app.exceptions import NotFoundError
		
		# Mock state.get_event to return None (event not found)
		mock_state.get_event.return_value = None
		
		# Attempt to deactivate non-existent event
		with pytest.raises(NotFoundError) as exc_info:
			EventCRUDService.deactivate_event("non-existent-event")
		
		# Verify the error message
		assert "Event" in str(exc_info.value)
		assert "non-existent-event" in str(exc_info.value)
		
		# Verify state.get_event was called
		mock_state.get_event.assert_called_once_with("non-existent-event")
		
		# Verify state.update_event was NOT called
		mock_state.update_event.assert_not_called()
	
	@patch('app.services.event_crud_service.state')
	def test_deactivate_event_preserves_all_fields(self, mock_state):
		"""Test that deactivate_event preserves all event fields except is_active and actual_end_date."""
		# Create an event with all optional fields populated
		start_date = datetime.now(timezone.utc) - timedelta(hours=1)
		expected_end_date = datetime.now(timezone.utc) + timedelta(hours=2)
		
		active_event = Event(
			event_key="event-full",
			nws_alert_id="alert-full",
			episode_key="episode-full",
			event_type="FFW",
			hr_event_type="Flash Flood Warning",
			start_date=start_date,
			expected_end_date=expected_end_date,
			actual_end_date=None,
			updated_at=datetime.now(timezone.utc) - timedelta(minutes=10),
			description="Full test event with all fields",
			is_active=True,
			confirmed=True,
			raw_vtec="/O.NEW.KFWD.FF.W.0015.240115T1000Z-240115T1100Z/",
			office="KFWD",
			property_damage=100000,
			crops_damage=50000,
			range_miles=5.5,
			previous_ids=["alert-old-1", "alert-old-2"],
			locations=[]
		)
		
		mock_state.get_event.return_value = active_event
		
		# Deactivate the event
		result = EventCRUDService.deactivate_event("event-full")
		
		# Verify is_active changed
		assert result.is_active is False
		
		# Verify actual_end_date is set
		assert result.actual_end_date is not None
		
		# Verify all other fields are preserved exactly
		assert result.event_key == "event-full"
		assert result.nws_alert_id == "alert-full"
		assert result.episode_key == "episode-full"
		assert result.event_type == "FFW"
		assert result.hr_event_type == "Flash Flood Warning"
		assert result.start_date == start_date
		assert result.expected_end_date == expected_end_date
		assert result.description == "Full test event with all fields"
		assert result.confirmed is True
		assert result.raw_vtec == "/O.NEW.KFWD.FF.W.0015.240115T1000Z-240115T1100Z/"
		assert result.office == "KFWD"
		assert result.property_damage == 100000
		assert result.crops_damage == 50000
		assert result.range_miles == 5.5
		assert result.previous_ids == ["alert-old-1", "alert-old-2"]
		assert result.locations == []
	
	@patch('app.services.event_crud_service.state')
	def test_deactivate_event_already_has_actual_end_date(self, mock_state):
		"""Test deactivating an event that already has an actual_end_date (should overwrite it)."""
		start_date = datetime.now(timezone.utc) - timedelta(hours=3)
		old_actual_end_date = datetime.now(timezone.utc) - timedelta(hours=1)
		
		event_with_end_date = Event(
			event_key="event-with-end",
			nws_alert_id="alert-1",
			event_type="TOR",
			start_date=start_date,
			expected_end_date=None,
			actual_end_date=old_actual_end_date,
			updated_at=datetime.now(timezone.utc) - timedelta(minutes=20),
			description="Event with existing end date",
			is_active=True,
			raw_vtec="/O.NEW.KFWD.TO.W.0015.240115T1000Z-240115T1100Z/"
		)
		
		mock_state.get_event.return_value = event_with_end_date
		
		before_deactivation = datetime.now(timezone.utc)
		result = EventCRUDService.deactivate_event("event-with-end")
		after_deactivation = datetime.now(timezone.utc)
		
		# Verify actual_end_date was updated to current time
		assert result.actual_end_date is not None
		assert result.actual_end_date != old_actual_end_date
		assert before_deactivation <= result.actual_end_date <= after_deactivation
		
		# Verify is_active is False
		assert result.is_active is False
