"""
Unit tests for EventCompletionService.
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock, PropertyMock
from datetime import datetime, timezone, timedelta
from app.services.event_completion_service import EventCompletionService
from app.schemas.event import Event

class TestCheckCompletedEvents:
	"""Test cases for EventCompletionService.check_completed_events."""
	
	@pytest.fixture
	def active_event_past_end_date(self):
		"""Create an active event past its expected end date."""
		return Event(
			event_key="KFWD.TO.W.0015.2024",
			nws_alert_id="alert-123",
			episode_key=None,
			event_type="TOR",
			hr_event_type="Tornado Warning",
			locations=[],
			start_date=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
			expected_end_date=datetime(2024, 1, 15, 11, 0, 0, tzinfo=timezone.utc),  # Past
			actual_end_date=None,
			updated_at=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
			description="Test",
			is_active=True,
			raw_vtec="/O.NEW.KFWD.TO.W.0015.240115T1000Z-240115T1100Z/",
			previous_ids=[]
		)
	
	@pytest.fixture
	def active_event_future_end_date(self):
		"""Create an active event with future expected end date."""
		future_date = datetime.now(timezone.utc) + timedelta(hours=1)
		return Event(
			event_key="KFWD.TO.W.0016.2024",
			nws_alert_id="alert-456",
			episode_key=None,
			event_type="TOR",
			hr_event_type="Tornado Warning",
			locations=[],
			start_date=datetime.now(timezone.utc),
			expected_end_date=future_date,
			actual_end_date=None,
			updated_at=datetime.now(timezone.utc),
			description="Test",
			is_active=True,
			raw_vtec="/O.NEW.KFWD.TO.W.0016.240115T1000Z-240115T1100Z/",
			previous_ids=[]
		)
	
	@patch('app.services.event_completion_service.state')
	@patch('app.services.event_completion_service.asyncio.run')
	def test_check_completed_events_no_active_events(self, mock_asyncio_run, mock_state):
		"""Test when there are no active events."""
		type(mock_state).active_events = PropertyMock(return_value=[])
		
		EventCompletionService.check_completed_events()
		
		mock_asyncio_run.assert_not_called()
	
	@patch('app.services.event_completion_service.state')
	@patch('app.services.event_completion_service.asyncio.run')
	def test_check_completed_events_no_events_past_end_date(self, mock_asyncio_run, mock_state, active_event_future_end_date):
		"""Test when no events are past their expected end date."""
		type(mock_state).active_events = PropertyMock(return_value=[active_event_future_end_date])
		
		EventCompletionService.check_completed_events()
		
		mock_asyncio_run.assert_not_called()
	
	@patch('app.services.event_completion_service.state')
	@patch('app.services.event_completion_service.asyncio.run')
	def test_check_completed_events_filters_by_end_date(self, mock_asyncio_run, mock_state, active_event_past_end_date, active_event_future_end_date):
		"""Test that only events past expected end date are checked."""
		type(mock_state).active_events = PropertyMock(return_value=[active_event_past_end_date, active_event_future_end_date])
		
		EventCompletionService.check_completed_events()
		
		# Should call asyncio.run
		mock_asyncio_run.assert_called_once()
		# Verify it was called (the coroutine will be passed to asyncio.run)
		assert mock_asyncio_run.called
	
	@patch('app.services.event_completion_service.state')
	@patch('app.services.event_completion_service.NWSClient')
	@patch('app.services.event_completion_service.vtec.get_message_type')
	@patch('app.services.event_completion_service.NWSAlertParser.get_most_recent_alert')
	@patch('app.services.event_completion_service.NWSAlertParser.extract_actual_end_time')
	@pytest.mark.asyncio
	async def test_check_completed_events_can_message_type(self, mock_extract_time, mock_get_alert, mock_get_message_type, mock_client_class, mock_state, active_event_past_end_date):
		"""Test that events with CAN message type are marked inactive."""
		mock_state.update_event = Mock()
		
		# Mock alert data
		alert_data = {
			"features": [{"properties": {"id": "alert-123"}}]
		}
		mock_get_alert.return_value = alert_data
		mock_get_message_type.return_value = "CAN"
		mock_extract_time.return_value = datetime(2024, 1, 15, 11, 0, 0, tzinfo=timezone.utc)
		
		mock_client = AsyncMock()
		mock_client.close = AsyncMock()
		mock_client_class.return_value = mock_client
		
		await EventCompletionService._async_check_completed_events([active_event_past_end_date])
		
		# Should update event to inactive
		mock_state.update_event.assert_called_once()
		updated_event = mock_state.update_event.call_args[0][0]
		assert updated_event.is_active is False
		assert updated_event.actual_end_date is not None
	
	@patch('app.services.event_completion_service.state')
	@patch('app.services.event_completion_service.NWSClient')
	@patch('app.services.event_completion_service.vtec.get_message_type')
	@patch('app.services.event_completion_service.NWSAlertParser.get_most_recent_alert')
	@patch('app.services.event_completion_service.NWSAlertParser.extract_actual_end_time')
	@patch('app.services.event_completion_service.settings')
	@pytest.mark.asyncio
	async def test_check_completed_events_timeout_threshold(self, mock_settings, mock_extract_time, mock_get_alert, mock_get_message_type, mock_client_class, mock_state):
		"""Test that events past timeout threshold are marked inactive."""
		mock_settings.event_completion_timeout_minutes = 20
		
		# Create event past expected end date by more than 20 minutes
		past_date = datetime.now(timezone.utc) - timedelta(minutes=25)
		event = Event(
			event_key="KFWD.TO.W.0017.2024",
			nws_alert_id="alert-789",
			episode_key=None,
			event_type="TOR",
			hr_event_type="Tornado Warning",
			locations=[],
			start_date=past_date - timedelta(minutes=30),
			expected_end_date=past_date,
			actual_end_date=None,
			updated_at=past_date,
			description="Test",
			is_active=True,
			raw_vtec="/O.NEW.KFWD.TO.W.0017.240115T1000Z-240115T1100Z/",
			previous_ids=[]
		)
		
		mock_state.update_event = Mock()
		
		alert_data = {
			"features": [{"properties": {"id": "alert-789"}}]
		}
		mock_get_alert.return_value = alert_data
		mock_get_message_type.return_value = "CON"  # Not CAN or EXP
		mock_extract_time.return_value = datetime.now(timezone.utc)
		
		mock_client = AsyncMock()
		mock_client.close = AsyncMock()
		mock_client_class.return_value = mock_client
		
		await EventCompletionService._async_check_completed_events([event])
		
		# Should update event to inactive due to timeout
		mock_state.update_event.assert_called_once()
		updated_event = mock_state.update_event.call_args[0][0]
		assert updated_event.is_active is False
	
	@patch('app.services.event_completion_service.state')
	@patch('app.services.event_completion_service.NWSClient')
	@patch('app.services.event_completion_service.vtec.get_message_type')
	@patch('app.services.event_completion_service.NWSAlertParser.get_most_recent_alert')
	@patch('app.services.event_completion_service.settings')
	@pytest.mark.asyncio
	async def test_check_completed_events_not_past_timeout(self, mock_settings, mock_get_alert, mock_get_message_type, mock_client_class, mock_state):
		"""Test that events not past timeout threshold are not marked inactive."""
		mock_settings.event_completion_timeout_minutes = 20
		
		# Create event past expected end date but not past timeout (10 minutes < 20 minutes)
		past_date = datetime.now(timezone.utc) - timedelta(minutes=10)
		event = Event(
			event_key="KFWD.TO.W.0018.2024",
			nws_alert_id="alert-999",
			episode_key=None,
			event_type="TOR",
			hr_event_type="Tornado Warning",
			locations=[],
			start_date=past_date - timedelta(minutes=30),
			expected_end_date=past_date,
			actual_end_date=None,
			updated_at=past_date,
			description="Test",
			is_active=True,
			raw_vtec="/O.NEW.KFWD.TO.W.0018.240115T1000Z-240115T1100Z/",
			previous_ids=[]
		)
		
		mock_state.update_event = Mock()
		
		alert_data = {
			"features": [{"properties": {"id": "alert-999"}}]
		}
		mock_get_alert.return_value = alert_data
		mock_get_message_type.return_value = "CON"  # Not CAN or EXP
		
		mock_client = AsyncMock()
		mock_client.close = AsyncMock()
		mock_client_class.return_value = mock_client
		
		await EventCompletionService._async_check_completed_events([event])
		
		# Should NOT update event (not past timeout)
		mock_state.update_event.assert_not_called()
	
	@patch('app.services.event_completion_service.state')
	@patch('app.services.event_completion_service.NWSClient')
	@patch('app.services.event_completion_service.NWSAlertParser.get_most_recent_alert')
	@pytest.mark.asyncio
	async def test_check_completed_events_handles_missing_alert(self, mock_get_alert, mock_client_class, mock_state, active_event_past_end_date):
		"""Test handling when alert cannot be retrieved."""
		mock_state.update_event = Mock()
		
		mock_get_alert.return_value = None  # Alert not found
		
		mock_client = AsyncMock()
		mock_client.close = AsyncMock()
		mock_client_class.return_value = mock_client
		
		await EventCompletionService._async_check_completed_events([active_event_past_end_date])
		
		# Should not update event
		mock_state.update_event.assert_not_called()
	
	@patch('app.services.event_completion_service.state')
	@patch('app.services.event_completion_service.NWSClient')
	@patch('app.services.event_completion_service.NWSAlertParser.get_most_recent_alert')
	@pytest.mark.asyncio
	async def test_check_completed_events_handles_exception(self, mock_get_alert, mock_client_class, mock_state, active_event_past_end_date):
		"""Test handling exceptions during processing."""
		mock_state.update_event = Mock()
		
		mock_get_alert.side_effect = Exception("API Error")
		
		mock_client = AsyncMock()
		mock_client.close = AsyncMock()
		mock_client_class.return_value = mock_client
		
		# Should not raise exception, just log and continue
		await EventCompletionService._async_check_completed_events([active_event_past_end_date])
		
		# Should not update event
		mock_state.update_event.assert_not_called()


