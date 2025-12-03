"""
Unit tests for GetActiveEpisodesAndEventsTool.
"""
import pytest
import json
from unittest.mock import Mock, patch
from app.crews.tools.get_active_events_and_episodes_tool import GetActiveEpisodesAndEventsTool
from app.schemas.event import Event
from app.schemas.episode import Episode
from app.schemas.location import Location
from datetime import datetime


class TestGetActiveEpisodesAndEventsTool:
	"""Test cases for GetActiveEpisodesAndEventsTool."""
	
	@pytest.fixture
	def tool(self):
		"""Create tool instance."""
		return GetActiveEpisodesAndEventsTool()
	
	@patch('app.crews.tools.get_active_events_and_episodes_tool.state')
	def test_get_active_with_metadata(self, mock_state, tool):
		"""Test getting active episodes/events with full metadata."""
		# Setup mock state
		mock_episode = Mock(spec=Episode)
		mock_episode.episode_id = 1
		mock_episode.episode_key = "TEST001"
		mock_episode.start_date = datetime(2024, 1, 15)
		mock_episode.is_active = True
		mock_episode.locations = []
		
		mock_event = Mock(spec=Event)
		mock_event.event_key = "EVT001"
		mock_event.episode_id = 1
		mock_event.event_type = "TOR"
		mock_event.is_active = True
		mock_event.location = Mock(spec=Location)
		mock_event.location.ugc_code = "TXC113"
		mock_event.location.shape = "POLYGON((...))"
		
		mock_state.active_episodes = [mock_episode]
		mock_state.active_events = [mock_event]
		
		# Run test
		result = tool._run(include_metadata=True)
		
		# Assertions
		result_data = json.loads(result)
		assert "active_episodes" in result_data
		assert "active_events" in result_data
		# The tool returns lists, not counts
		assert isinstance(result_data["active_episodes"], list)
		assert isinstance(result_data["active_events"], list)
		assert len(result_data["active_episodes"]) == 1
		assert len(result_data["active_events"]) == 1
	
	@patch('app.crews.tools.get_active_events_and_episodes_tool.state')
	def test_get_active_keys_only(self, mock_state, tool):
		"""Test getting only keys without full metadata."""
		mock_episode = Mock(spec=Episode)
		mock_episode.episode_id = 1
		mock_episode.episode_key = "TEST001"
		
		mock_event = Mock(spec=Event)
		mock_event.event_key = "EVT001"
		
		mock_state.active_episodes = [mock_episode]
		mock_state.active_events = [mock_event]
		
		result = tool._run(include_metadata=False)
		
		# Should still have the structure but minimal data
		result_data = json.loads(result)
		assert "active_episodes" in result_data
		assert "active_events" in result_data
		assert isinstance(result_data["active_episodes"], list)
		assert isinstance(result_data["active_events"], list)
		assert len(result_data["active_episodes"]) == 1
		assert len(result_data["active_events"]) == 1
	
	@patch('app.crews.tools.get_active_events_and_episodes_tool.state')
	def test_get_empty_state(self, mock_state, tool):
		"""Test getting from empty state."""
		mock_state.active_episodes = []
		mock_state.active_events = []
		
		result = tool._run()
		
		result_data = json.loads(result)
		assert "active_episodes" in result_data
		assert "active_events" in result_data
		assert isinstance(result_data["active_episodes"], list)
		assert isinstance(result_data["active_events"], list)
		assert len(result_data["active_episodes"]) == 0
		assert len(result_data["active_events"]) == 0
	
	def test_tool_name_and_description(self, tool):
		"""Test tool metadata."""
		assert tool.name == "GetActiveEpisodesAndEventsTool"
		assert "active" in tool.description.lower()

