"""
Facade tests for EventService to ensure backward compatibility.
These tests verify that EventService correctly delegates to the underlying services.
"""
from unittest.mock import Mock, patch
from app.services.event_service import EventService
from app.schemas.event import Event


class TestEventServiceFacade:
	"""Test that EventService correctly delegates to underlying services."""
	
	@patch('app.services.event_crud_service.EventCRUDService.get_event')
	def test_get_event_delegates(self, mock_get_event):
		"""Test that EventService.get_event delegates to EventCRUDService."""
		mock_event = Mock(spec=Event)
		mock_get_event.return_value = mock_event
		
		result = EventService.get_event("test-key")
		
		mock_get_event.assert_called_once_with("test-key")
		assert result == mock_event
	
	@patch('app.services.event_crud_service.EventCRUDService.get_events')
	def test_get_events_delegates(self, mock_get_events):
		"""Test that EventService.get_events delegates to EventCRUDService."""
		mock_events = [Mock(spec=Event), Mock(spec=Event)]
		mock_get_events.return_value = mock_events
		
		result = EventService.get_events(24)
		
		mock_get_events.assert_called_once_with(24)
		assert result == mock_events
	
	@patch('app.services.event_create_service.EventCreateService.create_event_from_alert')
	def test_create_event_from_alert_delegates(self, mock_create):
		"""Test that EventService.create_event_from_alert delegates to EventCreateService."""
		mock_alert = Mock()
		mock_event = Mock(spec=Event)
		mock_create.return_value = mock_event
		
		result = EventService.create_event_from_alert(mock_alert)
		
		mock_create.assert_called_once_with(mock_alert)
		assert result == mock_event
	
	@patch('app.services.event_update_service.EventUpdateService.update_event_from_alert')
	def test_update_event_from_alert_delegates(self, mock_update):
		"""Test that EventService.update_event_from_alert delegates to EventUpdateService."""
		mock_alert = Mock()
		mock_event = Mock(spec=Event)
		mock_update.return_value = mock_event
		
		result = EventService.update_event_from_alert(mock_alert)
		
		mock_update.assert_called_once_with(mock_alert)
		assert result == mock_event
	
	@patch('app.services.event_completion_service.EventCompletionService.check_completed_events')
	def test_check_completed_events_delegates(self, mock_check):
		"""Test that EventService.check_completed_events delegates to EventCompletionService."""
		EventService.check_completed_events()
		
		mock_check.assert_called_once()

