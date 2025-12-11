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
	def test_get_events_default_hour_offset(self, mock_state):
		"""Test get_events with default 72 hour offset."""
		now = datetime.now(timezone.utc)
		time_point = now - timedelta(hours=72)
		
		# Event within range
		event_in_range = Event(
			event_key="event-1",
			nws_alert_id="alert-1",
			event_type="TOR",
			start_date=time_point - timedelta(hours=10),
			actual_end_date=time_point + timedelta(hours=10),
			description="Event in range",
			is_active=True,
			raw_vtec="/O.NEW.KFWD.TO.W.0015.240115T1000Z-240115T1100Z/"
		)
		
		# Event before range
		event_before = Event(
			event_key="event-2",
			nws_alert_id="alert-2",
			event_type="TOR",
			start_date=time_point - timedelta(hours=100),
			actual_end_date=time_point - timedelta(hours=50),
			description="Event before range",
			is_active=True,
			raw_vtec="/O.NEW.KFWD.TO.W.0015.240115T1000Z-240115T1100Z/"
		)
		
		# Event after range
		event_after = Event(
			event_key="event-3",
			nws_alert_id="alert-3",
			event_type="TOR",
			start_date=time_point + timedelta(hours=50),
			actual_end_date=time_point + timedelta(hours=100),
			description="Event after range",
			is_active=True,
			raw_vtec="/O.NEW.KFWD.TO.W.0015.240115T1000Z-240115T1100Z/"
		)
		
		mock_state.events = [event_in_range, event_before, event_after]
		
		result = EventCRUDService.get_events()
		
		# Should only return event_in_range
		assert len(result) == 1
		assert result[0].event_key == "event-1"
	
	@patch('app.services.event_crud_service.state')
	def test_get_events_custom_hour_offset(self, mock_state):
		"""Test get_events with custom hour offset."""
		now = datetime.now(timezone.utc)
		time_point_24h = now - timedelta(hours=24)
		time_point_48h = now - timedelta(hours=48)
		
		# Event within 24h range
		event_24h = Event(
			event_key="event-24h",
			nws_alert_id="alert-1",
			event_type="TOR",
			start_date=time_point_24h - timedelta(hours=5),
			actual_end_date=time_point_24h + timedelta(hours=5),
			description="Event in 24h range",
			is_active=True,
			raw_vtec="/O.NEW.KFWD.TO.W.0015.240115T1000Z-240115T1100Z/"
		)
		
		# Event within 48h range but not 24h
		event_48h = Event(
			event_key="event-48h",
			nws_alert_id="alert-2",
			event_type="TOR",
			start_date=time_point_48h - timedelta(hours=5),
			actual_end_date=time_point_48h + timedelta(hours=5),
			description="Event in 48h range",
			is_active=True,
			raw_vtec="/O.NEW.KFWD.TO.W.0015.240115T1000Z-240115T1100Z/"
		)
		
		mock_state.events = [event_24h, event_48h]
		
		result = EventCRUDService.get_events(hour_offset=24)
		
		# Should only return event_24h
		assert len(result) == 1
		assert result[0].event_key == "event-24h"
	
	@patch('app.services.event_crud_service.state')
	def test_get_events_includes_events_with_null_actual_end_date_only(self, mock_state):
		"""Test that events with null actual_end_date are always included (start_date is required)."""
		now = datetime.now(timezone.utc)
		time_point = now - timedelta(hours=72)
		
		# Event with null actual_end_date - should be included
		event_with_null_end = Event(
			event_key="event-null-end",
			nws_alert_id="alert-1",
			event_type="TOR",
			start_date=time_point - timedelta(hours=100),
			actual_end_date=None,
			description="Event with null end",
			is_active=True,
			raw_vtec="/O.NEW.KFWD.TO.W.0015.240115T1000Z-240115T1100Z/"
		)
		
		# Event outside range - should be excluded
		event_normal = Event(
			event_key="event-normal",
			nws_alert_id="alert-2",
			event_type="TOR",
			start_date=time_point - timedelta(hours=100),
			actual_end_date=time_point - timedelta(hours=50),
			description="Event before range",
			is_active=True,
			raw_vtec="/O.NEW.KFWD.TO.W.0015.240115T1000Z-240115T1100Z/"
		)
		
		mock_state.events = [event_with_null_end, event_normal]
		
		result = EventCRUDService.get_events(hour_offset=72)
		
		# Should include event_with_null_end even though it's outside range
		assert len(result) == 1
		assert result[0].event_key == "event-null-end"
	
	@patch('app.services.event_crud_service.state')
	def test_get_events_includes_events_with_null_actual_end_date(self, mock_state):
		"""Test that events with null actual_end_date are always included."""
		now = datetime.now(timezone.utc)
		time_point = now - timedelta(hours=72)
		
		event_with_null_end = Event(
			event_key="event-null-end",
			nws_alert_id="alert-1",
			event_type="TOR",
			start_date=time_point - timedelta(hours=100),
			actual_end_date=None,
			description="Event with null end",
			is_active=True,
			raw_vtec="/O.NEW.KFWD.TO.W.0015.240115T1000Z-240115T1100Z/"
		)
		
		event_normal = Event(
			event_key="event-normal",
			nws_alert_id="alert-2",
			event_type="TOR",
			start_date=time_point - timedelta(hours=100),
			actual_end_date=time_point - timedelta(hours=50),
			description="Event before range",
			is_active=True,
			raw_vtec="/O.NEW.KFWD.TO.W.0015.240115T1000Z-240115T1100Z/"
		)
		
		mock_state.events = [event_with_null_end, event_normal]
		
		result = EventCRUDService.get_events(hour_offset=72)
		
		# Should include event_with_null_end even though it's outside range
		assert len(result) == 1
		assert result[0].event_key == "event-null-end"
	
	@patch('app.services.event_crud_service.state')
	def test_get_events_includes_events_with_null_actual_end_date(self, mock_state):
		"""Test that events with null actual_end_date are always included."""
		now = datetime.now(timezone.utc)
		time_point = now - timedelta(hours=72)
		
		# Event with null actual_end_date - should be included
		event_with_null_end = Event(
			event_key="event-null-end",
			nws_alert_id="alert-1",
			event_type="TOR",
			start_date=datetime.now(timezone.utc) - timedelta(hours=100),
			actual_end_date=None,
			description="Event with null end",
			is_active=True,
			raw_vtec="/O.NEW.KFWD.TO.W.0015.240115T1000Z-240115T1100Z/"
		)
		
		mock_state.events = [event_with_null_end]
		
		result = EventCRUDService.get_events(hour_offset=72)
		
		# Should include event_with_null_end
		assert len(result) == 1
		assert result[0].event_key == "event-null-end"
	
	@patch('app.services.event_crud_service.state')
	def test_get_events_with_zero_hour_offset_returns_all(self, mock_state):
		"""Test that hour_offset of 0 or less returns all events."""
		event1 = Event(
			event_key="event-1",
			nws_alert_id="alert-1",
			event_type="TOR",
			start_date=datetime.now(timezone.utc) - timedelta(hours=100),
			actual_end_date=datetime.now(timezone.utc) - timedelta(hours=50),
			description="Event 1",
			is_active=True,
			raw_vtec="/O.NEW.KFWD.TO.W.0015.240115T1000Z-240115T1100Z/"
		)
		
		event2 = Event(
			event_key="event-2",
			nws_alert_id="alert-2",
			event_type="TOR",
			start_date=datetime.now(timezone.utc) - timedelta(hours=10),
			actual_end_date=datetime.now(timezone.utc) + timedelta(hours=10),
			description="Event 2",
			is_active=True,
			raw_vtec="/O.NEW.KFWD.TO.W.0015.240115T1000Z-240115T1100Z/"
		)
		
		mock_state.events = [event1, event2]
		
		result = EventCRUDService.get_events(hour_offset=0)
		
		# Should return all events
		assert len(result) == 2
	
	@patch('app.services.event_crud_service.state')
	def test_get_events_boundary_conditions(self, mock_state):
		"""Test get_events with boundary conditions (time_point within range)."""
		# Use a fixed time point to avoid timing issues
		# We'll create events that clearly span the time_point
		now = datetime.now(timezone.utc)
		time_point = now - timedelta(hours=72)
		
		# Event where time_point is clearly within range (start before, end after)
		event_in_range = Event(
			event_key="event-in-range",
			nws_alert_id="alert-1",
			event_type="TOR",
			start_date=time_point - timedelta(hours=5),
			actual_end_date=time_point + timedelta(hours=5),
			description="Event in range",
			is_active=True,
			raw_vtec="/O.NEW.KFWD.TO.W.0015.240115T1000Z-240115T1100Z/"
		)
		
		# Event where time_point is exactly at start_date (should be included)
		# Use a small buffer to account for timing differences
		event_at_start = Event(
			event_key="event-at-start",
			nws_alert_id="alert-2",
			event_type="TOR",
			start_date=time_point - timedelta(seconds=1),
			actual_end_date=time_point + timedelta(hours=10),
			description="Event at start",
			is_active=True,
			raw_vtec="/O.NEW.KFWD.TO.W.0015.240115T1000Z-240115T1100Z/"
		)
		
		# Event where time_point is exactly at actual_end_date (should be included)
		event_at_end = Event(
			event_key="event-at-end",
			nws_alert_id="alert-3",
			event_type="TOR",
			start_date=time_point - timedelta(hours=10),
			actual_end_date=time_point + timedelta(seconds=1),
			description="Event at end",
			is_active=True,
			raw_vtec="/O.NEW.KFWD.TO.W.0015.240115T1000Z-240115T1100Z/"
		)
		
		# Event where time_point is just before start_date (should be excluded)
		event_before_start = Event(
			event_key="event-before-start",
			nws_alert_id="alert-4",
			event_type="TOR",
			start_date=time_point + timedelta(minutes=5),
			actual_end_date=time_point + timedelta(hours=10),
			description="Event before start",
			is_active=True,
			raw_vtec="/O.NEW.KFWD.TO.W.0015.240115T1000Z-240115T1100Z/"
		)
		
		# Event where time_point is just after actual_end_date (should be excluded)
		event_after_end = Event(
			event_key="event-after-end",
			nws_alert_id="alert-5",
			event_type="TOR",
			start_date=time_point - timedelta(hours=10),
			actual_end_date=time_point - timedelta(minutes=5),
			description="Event after end",
			is_active=True,
			raw_vtec="/O.NEW.KFWD.TO.W.0015.240115T1000Z-240115T1100Z/"
		)
		
		mock_state.events = [event_in_range, event_at_start, event_at_end, event_before_start, event_after_end]
		
		result = EventCRUDService.get_events(hour_offset=72)
		
		# Should include events that span time_point (in range, at start, at end)
		# Should exclude events before start or after end
		assert len(result) >= 3  # At least the three that should be included
		event_keys = {event.event_key for event in result}
		assert "event-in-range" in event_keys
		assert "event-before-start" not in event_keys
		assert "event-after-end" not in event_keys




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
		
		# Mock Redis to return both events
		mock_redis.get_all_keys.return_value = ["event:active-event", "event:inactive-event"]
		mock_redis.read.side_effect = [
			active_event.to_dict(),
			inactive_event.to_dict()
		]
		
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
		mock_redis.read.return_value = inactive_event.to_dict()
		
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
		mock_redis.read.side_effect = [
			active_event_1.to_dict(),
			inactive_event.to_dict(),
			active_event_2.to_dict()
		]
		
		state = State()
		result = state.active_events
		
		# Should return only the 2 active events
		assert len(result) == 2
		event_keys = {event.event_key for event in result}
		assert "active-1" in event_keys
		assert "active-2" in event_keys
		assert "inactive" not in event_keys


