"""
Tests for EventCreationProcessor.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
from app.processors.event_creation_processor import EventCreationProcessor
from app.shared_models.nws_poller_models import FilteredNWSAlert
from app.schemas.event import Event
from app.schemas.location import Location, Coordinate
from app.exceptions.base import ConflictError
from app.state import State


class TestEventCreationProcessor:
	"""Test suite for EventCreationProcessor."""
	
	@pytest.fixture
	def processor(self):
		"""Create a processor instance."""
		return EventCreationProcessor()
	
	@pytest.fixture
	def sample_alert(self):
		"""Create a sample alert for testing."""
		return FilteredNWSAlert(
			alert_id="alert-1",
			key="TEST-KEY-001",
			event_type="TOR",
			message_type="NEW",
			is_watch=False,
			is_warning=True,
			severity="Extreme",
			urgency="Immediate",
			certainty="Observed",
			effective="2024-01-15T10:00:00Z",
			expires="2024-01-15T11:00:00Z",
			expected_end="2024-01-15T11:00:00Z",
			sent_at="2024-01-15T10:00:00Z",
			headline="Test Alert",
			description="Test description",
			raw_vtec="/O.NEW.TEST.TO.W.0015.240115T1000Z/",
			affected_zones_ugc_endpoints=[],
			affected_zones_raw_ugc_codes=[],
			referenced_alerts=[],
			locations=[]
		)
	
	@pytest.fixture
	def mock_state(self):
		"""Mock state object."""
		with patch('app.processors.event_creation_processor.state') as mock_state:
			yield mock_state
	
	@pytest.fixture
	def mock_event_service(self):
		"""Mock EventService."""
		with patch('app.processors.event_creation_processor.EventService') as mock_service:
			yield mock_service
	
	def test_process_empty_list(self, processor, mock_state, mock_event_service):
		"""Test processing empty list of alerts."""
		processor.process([])
		mock_event_service.create_event_from_alert.assert_not_called()
	
	def test_process_single_alert_success(self, processor, sample_alert, mock_state, mock_event_service):
		"""Test processing a single alert successfully."""
		mock_state.event_exists.return_value = False
		mock_event = Mock(spec=Event)
		mock_event.event_key = sample_alert.key
		mock_event_service.create_event_from_alert.return_value = mock_event
		
		processor.process([sample_alert])
		
		mock_event_service.create_event_from_alert.assert_called_once_with(sample_alert)
	
	def test_process_multiple_unique_alerts(self, processor, mock_state, mock_event_service):
		"""Test processing multiple alerts with different keys."""
		alert1 = FilteredNWSAlert(
			alert_id="alert-1",
			key="KEY-1",
			event_type="TOR",
			message_type="NEW",
			is_watch=False,
			is_warning=True,
			severity="Extreme",
			urgency="Immediate",
			certainty="Observed",
			effective="2024-01-15T10:00:00Z",
			sent_at="2024-01-15T10:00:00Z",
			raw_vtec="",
			affected_zones_ugc_endpoints=[],
			affected_zones_raw_ugc_codes=[],
			referenced_alerts=[],
			locations=[]
		)
		alert2 = FilteredNWSAlert(
			alert_id="alert-2",
			key="KEY-2",
			event_type="SVR",
			message_type="NEW",
			is_watch=False,
			is_warning=True,
			severity="Extreme",
			urgency="Immediate",
			certainty="Observed",
			effective="2024-01-15T10:00:00Z",
			sent_at="2024-01-15T10:00:00Z",
			raw_vtec="",
			affected_zones_ugc_endpoints=[],
			affected_zones_raw_ugc_codes=[],
			referenced_alerts=[],
			locations=[]
		)
		
		mock_event1 = Mock(spec=Event)
		mock_event1.event_key = "KEY-1"
		mock_event2 = Mock(spec=Event)
		mock_event2.event_key = "KEY-2"
		mock_event_service.create_event_from_alert.side_effect = [mock_event1, mock_event2]
		
		processor.process([alert1, alert2])
		
		assert mock_event_service.create_event_from_alert.call_count == 2
	
	def test_deduplicate_by_key_selects_most_recent(self, processor, mock_state, mock_event_service):
		"""Test that deduplication selects the most recent alert by sent_at."""
		alert1 = FilteredNWSAlert(
			alert_id="alert-1",
			key="SAME-KEY",
			event_type="TOR",
			message_type="NEW",
			is_watch=False,
			is_warning=True,
			severity="Extreme",
			urgency="Immediate",
			certainty="Observed",
			effective="2024-01-15T10:00:00Z",
			sent_at="2024-01-15T10:00:00Z",  # Older
			raw_vtec="",
			affected_zones_ugc_endpoints=[],
			affected_zones_raw_ugc_codes=[],
			referenced_alerts=[],
			locations=[]
		)
		alert2 = FilteredNWSAlert(
			alert_id="alert-2",
			key="SAME-KEY",
			event_type="TOR",
			message_type="NEW",
			is_watch=False,
			is_warning=True,
			severity="Extreme",
			urgency="Immediate",
			certainty="Observed",
			effective="2024-01-15T10:00:00Z",
			sent_at="2024-01-15T11:00:00Z",  # More recent
			raw_vtec="",
			affected_zones_ugc_endpoints=[],
			affected_zones_raw_ugc_codes=[],
			referenced_alerts=[],
			locations=[]
		)
		
		mock_event = Mock(spec=Event)
		mock_event.event_key = "SAME-KEY"
		mock_event_service.create_event_from_alert.return_value = mock_event
		
		processor.process([alert1, alert2])
		
		# Should only be called once with the most recent alert
		assert mock_event_service.create_event_from_alert.call_count == 1
		# Verify it was called with alert2 (the more recent one)
		call_args = mock_event_service.create_event_from_alert.call_args[0][0]
		assert call_args.alert_id == "alert-2"
		assert call_args.sent_at == "2024-01-15T11:00:00Z"
	
	def test_deduplicate_by_key_handles_none_sent_at(self, processor, mock_state, mock_event_service):
		"""Test deduplication when some alerts have None sent_at."""
		alert1 = FilteredNWSAlert(
			alert_id="alert-1",
			key="SAME-KEY",
			event_type="TOR",
			message_type="NEW",
			is_watch=False,
			is_warning=True,
			severity="Extreme",
			urgency="Immediate",
			certainty="Observed",
			effective="2024-01-15T10:00:00Z",
			sent_at=None,  # No sent_at
			raw_vtec="",
			affected_zones_ugc_endpoints=[],
			affected_zones_raw_ugc_codes=[],
			referenced_alerts=[],
			locations=[]
		)
		alert2 = FilteredNWSAlert(
			alert_id="alert-2",
			key="SAME-KEY",
			event_type="TOR",
			message_type="NEW",
			is_watch=False,
			is_warning=True,
			severity="Extreme",
			urgency="Immediate",
			certainty="Observed",
			effective="2024-01-15T10:00:00Z",
			sent_at="2024-01-15T11:00:00Z",  # Has sent_at
			raw_vtec="",
			affected_zones_ugc_endpoints=[],
			affected_zones_raw_ugc_codes=[],
			referenced_alerts=[],
			locations=[]
		)
		
		mock_event = Mock(spec=Event)
		mock_event.event_key = "SAME-KEY"
		mock_event_service.create_event_from_alert.return_value = mock_event
		
		processor.process([alert1, alert2])
		
		# Should select alert2 (has valid sent_at)
		assert mock_event_service.create_event_from_alert.call_count == 1
		call_args = mock_event_service.create_event_from_alert.call_args[0][0]
		assert call_args.alert_id == "alert-2"
	
	def test_deduplicate_by_key_all_none_sent_at(self, processor, mock_state, mock_event_service):
		"""Test deduplication when all alerts have None sent_at."""
		alert1 = FilteredNWSAlert(
			alert_id="alert-1",
			key="SAME-KEY",
			event_type="TOR",
			message_type="NEW",
			is_watch=False,
			is_warning=True,
			severity="Extreme",
			urgency="Immediate",
			certainty="Observed",
			effective="2024-01-15T10:00:00Z",
			sent_at=None,
			raw_vtec="",
			affected_zones_ugc_endpoints=[],
			affected_zones_raw_ugc_codes=[],
			referenced_alerts=[],
			locations=[]
		)
		alert2 = FilteredNWSAlert(
			alert_id="alert-2",
			key="SAME-KEY",
			event_type="TOR",
			message_type="NEW",
			is_watch=False,
			is_warning=True,
			severity="Extreme",
			urgency="Immediate",
			certainty="Observed",
			effective="2024-01-15T10:00:00Z",
			sent_at=None,
			raw_vtec="",
			affected_zones_ugc_endpoints=[],
			affected_zones_raw_ugc_codes=[],
			referenced_alerts=[],
			locations=[]
		)
		
		mock_event = Mock(spec=Event)
		mock_event.event_key = "SAME-KEY"
		mock_event_service.create_event_from_alert.return_value = mock_event
		
		processor.process([alert1, alert2])
		
		# Should select first alert (fallback)
		assert mock_event_service.create_event_from_alert.call_count == 1
		call_args = mock_event_service.create_event_from_alert.call_args[0][0]
		assert call_args.alert_id == "alert-1"
	
	def test_deduplicate_by_key_invalid_sent_at(self, processor, mock_state, mock_event_service):
		"""Test deduplication when sent_at is invalid."""
		alert1 = FilteredNWSAlert(
			alert_id="alert-1",
			key="SAME-KEY",
			event_type="TOR",
			message_type="NEW",
			is_watch=False,
			is_warning=True,
			severity="Extreme",
			urgency="Immediate",
			certainty="Observed",
			effective="2024-01-15T10:00:00Z",
			sent_at="invalid-date",  # Invalid format
			raw_vtec="",
			affected_zones_ugc_endpoints=[],
			affected_zones_raw_ugc_codes=[],
			referenced_alerts=[],
			locations=[]
		)
		alert2 = FilteredNWSAlert(
			alert_id="alert-2",
			key="SAME-KEY",
			event_type="TOR",
			message_type="NEW",
			is_watch=False,
			is_warning=True,
			severity="Extreme",
			urgency="Immediate",
			certainty="Observed",
			effective="2024-01-15T10:00:00Z",
			sent_at="2024-01-15T11:00:00Z",  # Valid
			raw_vtec="",
			affected_zones_ugc_endpoints=[],
			affected_zones_raw_ugc_codes=[],
			referenced_alerts=[],
			locations=[]
		)
		
		mock_event = Mock(spec=Event)
		mock_event.event_key = "SAME-KEY"
		mock_event_service.create_event_from_alert.return_value = mock_event
		
		processor.process([alert1, alert2])
		
		# Should select alert2 (valid sent_at)
		assert mock_event_service.create_event_from_alert.call_count == 1
		call_args = mock_event_service.create_event_from_alert.call_args[0][0]
		assert call_args.alert_id == "alert-2"
	
	def test_conflict_error_duplicate_alert_id(self, processor, sample_alert, mock_state, mock_event_service):
		"""Test handling ConflictError when alert_id is duplicate."""
		mock_event_service.create_event_from_alert.side_effect = ConflictError("Event already exists")
		
		existing_event = Mock(spec=Event)
		existing_event.nws_alert_id = sample_alert.alert_id  # Same alert_id
		existing_event.previous_ids = []
		mock_state.get_event.return_value = existing_event
		
		processor.process([sample_alert])
		
		# Should not call update_event_from_alert
		mock_event_service.update_event_from_alert.assert_not_called()
	
	def test_conflict_error_different_alert_id(self, processor, sample_alert, mock_state, mock_event_service):
		"""Test handling ConflictError when alert_id is different (should update)."""
		mock_event_service.create_event_from_alert.side_effect = ConflictError("Event already exists")
		
		existing_event = Mock(spec=Event)
		existing_event.nws_alert_id = "different-alert-id"
		existing_event.previous_ids = []
		mock_state.get_event.return_value = existing_event
		
		updated_event = Mock(spec=Event)
		updated_event.event_key = sample_alert.key
		mock_event_service.update_event_from_alert.return_value = updated_event
		
		processor.process([sample_alert])
		
		# Should call update_event_from_alert
		mock_event_service.update_event_from_alert.assert_called_once_with(sample_alert)
	
	def test_conflict_error_alert_id_in_previous_ids(self, processor, sample_alert, mock_state, mock_event_service):
		"""Test handling ConflictError when alert_id is in previous_ids."""
		mock_event_service.create_event_from_alert.side_effect = ConflictError("Event already exists")
		
		existing_event = Mock(spec=Event)
		existing_event.nws_alert_id = "different-alert-id"
		existing_event.previous_ids = [sample_alert.alert_id]  # In previous_ids
		mock_state.get_event.return_value = existing_event
		
		processor.process([sample_alert])
		
		# Should not call update_event_from_alert (duplicate)
		mock_event_service.update_event_from_alert.assert_not_called()
	
	def test_conflict_error_event_deleted(self, processor, sample_alert, mock_state, mock_event_service):
		"""Test handling ConflictError when event is deleted between check and retrieval."""
		mock_event_service.create_event_from_alert.side_effect = ConflictError("Event already exists")
		mock_state.get_event.return_value = None  # Event was deleted
		
		processor.process([sample_alert])
		
		# Should not call update_event_from_alert
		mock_event_service.update_event_from_alert.assert_not_called()
	
	def test_conflict_error_update_fails(self, processor, sample_alert, mock_state, mock_event_service):
		"""Test handling when update fails after ConflictError."""
		mock_event_service.create_event_from_alert.side_effect = ConflictError("Event already exists")
		
		existing_event = Mock(spec=Event)
		existing_event.nws_alert_id = "different-alert-id"
		existing_event.previous_ids = []
		mock_state.get_event.return_value = existing_event
		
		mock_event_service.update_event_from_alert.side_effect = Exception("Update failed")
		
		# Should not raise, should continue processing
		processor.process([sample_alert])
		
		# Should have attempted update
		mock_event_service.update_event_from_alert.assert_called_once_with(sample_alert)
	
	def test_general_exception_handling(self, processor, sample_alert, mock_state, mock_event_service):
		"""Test handling of general exceptions during event creation."""
		mock_event_service.create_event_from_alert.side_effect = Exception("General error")
		
		# Should not raise, should continue processing
		processor.process([sample_alert])
		
		mock_event_service.create_event_from_alert.assert_called_once_with(sample_alert)
	
	def test_process_multiple_alerts_with_exceptions(self, processor, mock_state, mock_event_service):
		"""Test that processing continues even when some alerts fail."""
		alert1 = FilteredNWSAlert(
			alert_id="alert-1",
			key="KEY-1",
			event_type="TOR",
			message_type="NEW",
			is_watch=False,
			is_warning=True,
			severity="Extreme",
			urgency="Immediate",
			certainty="Observed",
			effective="2024-01-15T10:00:00Z",
			sent_at="2024-01-15T10:00:00Z",
			raw_vtec="",
			affected_zones_ugc_endpoints=[],
			affected_zones_raw_ugc_codes=[],
			referenced_alerts=[],
			locations=[]
		)
		alert2 = FilteredNWSAlert(
			alert_id="alert-2",
			key="KEY-2",
			event_type="SVR",
			message_type="NEW",
			is_watch=False,
			is_warning=True,
			severity="Extreme",
			urgency="Immediate",
			certainty="Observed",
			effective="2024-01-15T10:00:00Z",
			sent_at="2024-01-15T10:00:00Z",
			raw_vtec="",
			affected_zones_ugc_endpoints=[],
			affected_zones_raw_ugc_codes=[],
			referenced_alerts=[],
			locations=[]
		)
		
		mock_event = Mock(spec=Event)
		mock_event.event_key = "KEY-2"
		mock_event_service.create_event_from_alert.side_effect = [
			Exception("Error for alert-1"),
			mock_event
		]
		
		# Should process both, even though first fails
		processor.process([alert1, alert2])
		
		# Should have attempted both
		assert mock_event_service.create_event_from_alert.call_count == 2
	
	def test_select_most_recent_alert_single_alert(self, processor):
		"""Test _select_most_recent_alert with single alert."""
		alert = FilteredNWSAlert(
			alert_id="alert-1",
			key="KEY-1",
			event_type="TOR",
			message_type="NEW",
			is_watch=False,
			is_warning=True,
			severity="Extreme",
			urgency="Immediate",
			certainty="Observed",
			effective="2024-01-15T10:00:00Z",
			sent_at="2024-01-15T10:00:00Z",
			raw_vtec="",
			affected_zones_ugc_endpoints=[],
			affected_zones_raw_ugc_codes=[],
			referenced_alerts=[],
			locations=[]
		)
		
		result = processor._select_most_recent_alert([alert], "KEY-1")
		assert result == alert
	
	def test_select_most_recent_alert_multiple_alerts(self, processor):
		"""Test _select_most_recent_alert with multiple alerts."""
		alert1 = FilteredNWSAlert(
			alert_id="alert-1",
			key="SAME-KEY",
			event_type="TOR",
			message_type="NEW",
			is_watch=False,
			is_warning=True,
			severity="Extreme",
			urgency="Immediate",
			certainty="Observed",
			effective="2024-01-15T10:00:00Z",
			sent_at="2024-01-15T10:00:00Z",
			raw_vtec="",
			affected_zones_ugc_endpoints=[],
			affected_zones_raw_ugc_codes=[],
			referenced_alerts=[],
			locations=[]
		)
		alert2 = FilteredNWSAlert(
			alert_id="alert-2",
			key="SAME-KEY",
			event_type="TOR",
			message_type="NEW",
			is_watch=False,
			is_warning=True,
			severity="Extreme",
			urgency="Immediate",
			certainty="Observed",
			effective="2024-01-15T10:00:00Z",
			sent_at="2024-01-15T11:00:00Z",  # More recent
			raw_vtec="",
			affected_zones_ugc_endpoints=[],
			affected_zones_raw_ugc_codes=[],
			referenced_alerts=[],
			locations=[]
		)
		
		result = processor._select_most_recent_alert([alert1, alert2], "SAME-KEY")
		assert result.alert_id == "alert-2"
		assert result.sent_at == "2024-01-15T11:00:00Z"
	
	def test_deduplicate_by_key_single_alert_per_key(self, processor):
		"""Test _deduplicate_by_key with unique keys."""
		alert1 = FilteredNWSAlert(
			alert_id="alert-1",
			key="KEY-1",
			event_type="TOR",
			message_type="NEW",
			is_watch=False,
			is_warning=True,
			severity="Extreme",
			urgency="Immediate",
			certainty="Observed",
			effective="2024-01-15T10:00:00Z",
			sent_at="2024-01-15T10:00:00Z",
			raw_vtec="",
			affected_zones_ugc_endpoints=[],
			affected_zones_raw_ugc_codes=[],
			referenced_alerts=[],
			locations=[]
		)
		alert2 = FilteredNWSAlert(
			alert_id="alert-2",
			key="KEY-2",
			event_type="SVR",
			message_type="NEW",
			is_watch=False,
			is_warning=True,
			severity="Extreme",
			urgency="Immediate",
			certainty="Observed",
			effective="2024-01-15T10:00:00Z",
			sent_at="2024-01-15T10:00:00Z",
			raw_vtec="",
			affected_zones_ugc_endpoints=[],
			affected_zones_raw_ugc_codes=[],
			referenced_alerts=[],
			locations=[]
		)
		
		result = processor._deduplicate_by_key([alert1, alert2])
		assert len(result) == 2
		assert result[0].alert_id == "alert-1"
		assert result[1].alert_id == "alert-2"
	
	def test_deduplicate_by_key_multiple_alerts_same_key(self, processor):
		"""Test _deduplicate_by_key with multiple alerts having same key."""
		alert1 = FilteredNWSAlert(
			alert_id="alert-1",
			key="SAME-KEY",
			event_type="TOR",
			message_type="NEW",
			is_watch=False,
			is_warning=True,
			severity="Extreme",
			urgency="Immediate",
			certainty="Observed",
			effective="2024-01-15T10:00:00Z",
			sent_at="2024-01-15T10:00:00Z",
			raw_vtec="",
			affected_zones_ugc_endpoints=[],
			affected_zones_raw_ugc_codes=[],
			referenced_alerts=[],
			locations=[]
		)
		alert2 = FilteredNWSAlert(
			alert_id="alert-2",
			key="SAME-KEY",
			event_type="TOR",
			message_type="NEW",
			is_watch=False,
			is_warning=True,
			severity="Extreme",
			urgency="Immediate",
			certainty="Observed",
			effective="2024-01-15T10:00:00Z",
			sent_at="2024-01-15T11:00:00Z",
			raw_vtec="",
			affected_zones_ugc_endpoints=[],
			affected_zones_raw_ugc_codes=[],
			referenced_alerts=[],
			locations=[]
		)
		
		result = processor._deduplicate_by_key([alert1, alert2])
		assert len(result) == 1
		assert result[0].alert_id == "alert-2"  # Most recent
	
	def test_try_fallback_to_update_event_deleted(self, processor, sample_alert, mock_state, mock_event_service):
		"""Test _try_fallback_to_update when event is deleted."""
		mock_state.get_event.return_value = None
		
		processor._try_fallback_to_update(sample_alert)
		
		# Should not call update_event_from_alert
		mock_event_service.update_event_from_alert.assert_not_called()
		mock_state.get_event.assert_called_once_with(sample_alert.key)
	
	def test_try_fallback_to_update_duplicate_alert_id(self, processor, sample_alert, mock_state, mock_event_service):
		"""Test _try_fallback_to_update when alert_id matches existing event."""
		existing_event = Mock(spec=Event)
		existing_event.nws_alert_id = sample_alert.alert_id  # Same alert_id
		existing_event.previous_ids = []
		mock_state.get_event.return_value = existing_event
		
		processor._try_fallback_to_update(sample_alert)
		
		# Should not call update_event_from_alert (duplicate)
		mock_event_service.update_event_from_alert.assert_not_called()
	
	def test_try_fallback_to_update_alert_id_in_previous_ids(self, processor, sample_alert, mock_state, mock_event_service):
		"""Test _try_fallback_to_update when alert_id is in previous_ids."""
		existing_event = Mock(spec=Event)
		existing_event.nws_alert_id = "different-alert-id"
		existing_event.previous_ids = [sample_alert.alert_id]  # In previous_ids
		mock_state.get_event.return_value = existing_event
		
		processor._try_fallback_to_update(sample_alert)
		
		# Should not call update_event_from_alert (duplicate)
		mock_event_service.update_event_from_alert.assert_not_called()
	
	def test_try_fallback_to_update_different_alert_id_success(self, processor, sample_alert, mock_state, mock_event_service):
		"""Test _try_fallback_to_update when alert_id is different and update succeeds."""
		existing_event = Mock(spec=Event)
		existing_event.nws_alert_id = "different-alert-id"
		existing_event.previous_ids = []
		mock_state.get_event.return_value = existing_event
		
		updated_event = Mock(spec=Event)
		updated_event.event_key = sample_alert.key
		mock_event_service.update_event_from_alert.return_value = updated_event
		
		processor._try_fallback_to_update(sample_alert)
		
		# Should call update_event_from_alert
		mock_event_service.update_event_from_alert.assert_called_once_with(sample_alert)
	
	def test_try_fallback_to_update_different_alert_id_update_fails(self, processor, sample_alert, mock_state, mock_event_service):
		"""Test _try_fallback_to_update when alert_id is different but update fails."""
		existing_event = Mock(spec=Event)
		existing_event.nws_alert_id = "different-alert-id"
		existing_event.previous_ids = []
		mock_state.get_event.return_value = existing_event
		
		mock_event_service.update_event_from_alert.side_effect = Exception("Update failed")
		
		# Should not raise, should handle gracefully
		processor._try_fallback_to_update(sample_alert)
		
		# Should have attempted update
		mock_event_service.update_event_from_alert.assert_called_once_with(sample_alert)
	
	def test_try_fallback_to_update_multiple_previous_ids(self, processor, sample_alert, mock_state, mock_event_service):
		"""Test _try_fallback_to_update when alert_id is in a list with multiple previous_ids."""
		existing_event = Mock(spec=Event)
		existing_event.nws_alert_id = "different-alert-id"
		existing_event.previous_ids = ["old-alert-1", sample_alert.alert_id, "old-alert-2"]
		mock_state.get_event.return_value = existing_event
		
		processor._try_fallback_to_update(sample_alert)
		
		# Should not call update_event_from_alert (duplicate)
		mock_event_service.update_event_from_alert.assert_not_called()
	
	def test_try_fallback_to_update_empty_previous_ids(self, processor, sample_alert, mock_state, mock_event_service):
		"""Test _try_fallback_to_update when previous_ids is empty."""
		existing_event = Mock(spec=Event)
		existing_event.nws_alert_id = "different-alert-id"
		existing_event.previous_ids = []  # Empty list
		mock_state.get_event.return_value = existing_event
		
		updated_event = Mock(spec=Event)
		updated_event.event_key = sample_alert.key
		mock_event_service.update_event_from_alert.return_value = updated_event
		
		processor._try_fallback_to_update(sample_alert)
		
		# Should call update_event_from_alert
		mock_event_service.update_event_from_alert.assert_called_once_with(sample_alert)
	
	def test_filter_fww_events(self, processor, mock_state, mock_event_service):
		"""Test that FWW (Fire Weather Warning) events are filtered out."""
		fww_alert = FilteredNWSAlert(
			alert_id="fww-alert-1",
			key="FWW-KEY-001",
			event_type="FWW",
			message_type="NEW",
			is_watch=False,
			is_warning=True,
			severity="Moderate",
			urgency="Expected",
			certainty="Likely",
			effective="2024-01-15T10:00:00Z",
			sent_at="2024-01-15T10:00:00Z",
			raw_vtec="",
			affected_zones_ugc_endpoints=[],
			affected_zones_raw_ugc_codes=[],
			referenced_alerts=[],
			locations=[]
		)
		normal_alert = FilteredNWSAlert(
			alert_id="normal-alert-1",
			key="TOR-KEY-001",
			event_type="TOR",
			message_type="NEW",
			is_watch=False,
			is_warning=True,
			severity="Extreme",
			urgency="Immediate",
			certainty="Observed",
			effective="2024-01-15T10:00:00Z",
			sent_at="2024-01-15T10:00:00Z",
			raw_vtec="",
			affected_zones_ugc_endpoints=[],
			affected_zones_raw_ugc_codes=[],
			referenced_alerts=[],
			locations=[]
		)
		
		mock_event = Mock(spec=Event)
		mock_event.event_key = "TOR-KEY-001"
		mock_event_service.create_event_from_alert.return_value = mock_event
		
		processor.process([fww_alert, normal_alert])
		
		# Should only process the normal alert, not the FWW
		mock_event_service.create_event_from_alert.assert_called_once_with(normal_alert)
	
	def test_filter_fww_events_case_insensitive(self, processor, mock_state, mock_event_service):
		"""Test that FWW filtering is case-insensitive."""
		fww_alert_lower = FilteredNWSAlert(
			alert_id="fww-alert-1",
			key="FWW-KEY-001",
			event_type="fww",  # lowercase
			message_type="NEW",
			is_watch=False,
			is_warning=True,
			severity="Moderate",
			urgency="Expected",
			certainty="Likely",
			effective="2024-01-15T10:00:00Z",
			sent_at="2024-01-15T10:00:00Z",
			raw_vtec="",
			affected_zones_ugc_endpoints=[],
			affected_zones_raw_ugc_codes=[],
			referenced_alerts=[],
			locations=[]
		)
		
		processor.process([fww_alert_lower])
		
		# Should not create any events
		mock_event_service.create_event_from_alert.assert_not_called()
	
	@patch('app.processors.event_creation_processor.WindValidationAgent')
	def test_hww_validation_valid_wind_speed(self, mock_wind_agent_class, processor, mock_state, mock_event_service):
		"""Test that HWW events with valid wind speeds are created."""
		from app.agents.models import WindValidationOutput
		
		hww_alert = FilteredNWSAlert(
			alert_id="hww-alert-1",
			key="HWW-KEY-001",
			event_type="HWW",
			message_type="NEW",
			is_watch=False,
			is_warning=True,
			severity="Moderate",
			urgency="Expected",
			certainty="Likely",
			effective="2024-01-15T10:00:00Z",
			sent_at="2024-01-15T10:00:00Z",
			headline="High Wind Warning",
			description="Sustained winds of 70 mph expected",
			raw_vtec="",
			affected_zones_ugc_endpoints=[],
			affected_zones_raw_ugc_codes=[],
			referenced_alerts=[],
			locations=[]
		)
		
		# Mock the wind validation agent
		mock_wind_agent = Mock()
		mock_wind_agent.validate.return_value = WindValidationOutput(valid=True)
		mock_wind_agent_class.return_value = mock_wind_agent
		
		# Reinitialize processor to get the mocked agent
		processor.wind_validation_agent = mock_wind_agent
		
		mock_event = Mock(spec=Event)
		mock_event.event_key = "HWW-KEY-001"
		mock_event_service.create_event_from_alert.return_value = mock_event
		
		processor.process([hww_alert])
		
		# Should validate and then create the event
		mock_wind_agent.validate.assert_called_once_with(
			headline="High Wind Warning",
			description="Sustained winds of 70 mph expected"
		)
		mock_event_service.create_event_from_alert.assert_called_once_with(hww_alert)
	
	@patch('app.processors.event_creation_processor.WindValidationAgent')
	def test_hww_validation_invalid_wind_speed(self, mock_wind_agent_class, processor, mock_state, mock_event_service):
		"""Test that HWW events with invalid wind speeds are skipped."""
		from app.agents.models import WindValidationOutput
		
		hww_alert = FilteredNWSAlert(
			alert_id="hww-alert-1",
			key="HWW-KEY-001",
			event_type="HWW",
			message_type="NEW",
			is_watch=False,
			is_warning=True,
			severity="Moderate",
			urgency="Expected",
			certainty="Likely",
			effective="2024-01-15T10:00:00Z",
			sent_at="2024-01-15T10:00:00Z",
			headline="High Wind Warning",
			description="Sustained winds of 50 mph expected",
			raw_vtec="",
			affected_zones_ugc_endpoints=[],
			affected_zones_raw_ugc_codes=[],
			referenced_alerts=[],
			locations=[]
		)
		
		# Mock the wind validation agent
		mock_wind_agent = Mock()
		mock_wind_agent.validate.return_value = WindValidationOutput(valid=False)
		mock_wind_agent_class.return_value = mock_wind_agent
		
		# Reinitialize processor to get the mocked agent
		processor.wind_validation_agent = mock_wind_agent
		
		processor.process([hww_alert])
		
		# Should validate but not create the event
		mock_wind_agent.validate.assert_called_once_with(
			headline="High Wind Warning",
			description="Sustained winds of 50 mph expected"
		)
		mock_event_service.create_event_from_alert.assert_not_called()
	
	@patch('app.processors.event_creation_processor.WindValidationAgent')
	def test_hww_validation_error_handling(self, mock_wind_agent_class, processor, mock_state, mock_event_service):
		"""Test that HWW validation errors cause the event to be skipped."""
		hww_alert = FilteredNWSAlert(
			alert_id="hww-alert-1",
			key="HWW-KEY-001",
			event_type="HWW",
			message_type="NEW",
			is_watch=False,
			is_warning=True,
			severity="Moderate",
			urgency="Expected",
			certainty="Likely",
			effective="2024-01-15T10:00:00Z",
			sent_at="2024-01-15T10:00:00Z",
			headline="High Wind Warning",
			description="Sustained winds expected",
			raw_vtec="",
			affected_zones_ugc_endpoints=[],
			affected_zones_raw_ugc_codes=[],
			referenced_alerts=[],
			locations=[]
		)
		
		# Mock the wind validation agent to raise an error
		mock_wind_agent = Mock()
		mock_wind_agent.validate.side_effect = Exception("Validation error")
		mock_wind_agent_class.return_value = mock_wind_agent
		
		# Reinitialize processor to get the mocked agent
		processor.wind_validation_agent = mock_wind_agent
		
		processor.process([hww_alert])
		
		# Should attempt validation but not create the event
		mock_wind_agent.validate.assert_called_once()
		mock_event_service.create_event_from_alert.assert_not_called()
	
	@patch('app.processors.event_creation_processor.WindValidationAgent')
	def test_hww_validation_with_none_headline_description(self, mock_wind_agent_class, processor, mock_state, mock_event_service):
		"""Test that HWW validation handles None headline/description by converting to empty strings."""
		from app.agents.models import WindValidationOutput
		
		hww_alert = FilteredNWSAlert(
			alert_id="hww-alert-1",
			key="HWW-KEY-001",
			event_type="HWW",
			message_type="NEW",
			is_watch=False,
			is_warning=True,
			severity="Moderate",
			urgency="Expected",
			certainty="Likely",
			effective="2024-01-15T10:00:00Z",
			sent_at="2024-01-15T10:00:00Z",
			headline=None,
			description=None,
			raw_vtec="",
			affected_zones_ugc_endpoints=[],
			affected_zones_raw_ugc_codes=[],
			referenced_alerts=[],
			locations=[]
		)
		
		# Mock the wind validation agent
		mock_wind_agent = Mock()
		mock_wind_agent.validate.return_value = WindValidationOutput(valid=True)
		mock_wind_agent_class.return_value = mock_wind_agent
		
		# Reinitialize processor to get the mocked agent
		processor.wind_validation_agent = mock_wind_agent
		
		mock_event = Mock(spec=Event)
		mock_event.event_key = "HWW-KEY-001"
		mock_event_service.create_event_from_alert.return_value = mock_event
		
		processor.process([hww_alert])
		
		# Should validate with empty strings
		mock_wind_agent.validate.assert_called_once_with(
			headline="",
			description=""
		)
		mock_event_service.create_event_from_alert.assert_called_once_with(hww_alert)
	
	def test_non_hww_events_not_validated(self, processor, sample_alert, mock_state, mock_event_service):
		"""Test that non-HWW events are not validated."""
		# Mock the wind validation agent
		mock_wind_agent = Mock()
		processor.wind_validation_agent = mock_wind_agent
		
		mock_event = Mock(spec=Event)
		mock_event.event_key = sample_alert.key
		mock_event_service.create_event_from_alert.return_value = mock_event
		
		processor.process([sample_alert])
		
		# Should not call validation for non-HWW events
		mock_wind_agent.validate.assert_not_called()
		mock_event_service.create_event_from_alert.assert_called_once_with(sample_alert)