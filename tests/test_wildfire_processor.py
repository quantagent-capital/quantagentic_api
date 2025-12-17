"""
Unit tests for WildfireProcessor.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone, timedelta
from app.processors.wildfire_processor import WildfireProcessor
from app.schemas.wildfire import Wildfire
from app.schemas.location import Location, Coordinate


class TestProcessNewWildfires:
	"""Test cases for WildfireProcessor._process_new_wildfires."""
	
	def _get_sample_feature(self):
		"""Helper method to create a sample feature for testing."""
		return {
			"properties": {
				"attr_UniqueFireIdentifier": "2025-TEST-001"
			},
			"geometry": {
				"type": "Polygon",
				"coordinates": [[[-97.5, 32.8], [-97.2, 32.8], [-97.2, 33.1], [-97.5, 33.1], [-97.5, 32.8]]]
			}
		}
	
	@patch('app.processors.wildfire_processor.WildfireCRUDService')
	@patch('app.processors.wildfire_processor.state')
	@patch('app.processors.wildfire_processor.WildfireClient')
	def test_process_new_wildfires_creates_new(self, mock_client, mock_state, mock_crud):
		"""Test processing new wildfires creates them."""
		mock_state.active_wildfires = []
		mock_client.fetch_wildfires.return_value = {
			"features": [self._get_sample_feature()]
		}
		mock_crud.create_wildfire.return_value = Mock()
		
		timestamp_filter = datetime.now(timezone.utc) - timedelta(days=2)
		created_count, new_event_keys = WildfireProcessor._process_new_wildfires(timestamp_filter)
		
		assert created_count == 1
		assert "2025-TEST-001" in new_event_keys
		mock_crud.create_wildfire.assert_called_once()
	
	@patch('app.processors.wildfire_processor.WildfireCRUDService')
	@patch('app.processors.wildfire_processor.state')
	@patch('app.processors.wildfire_processor.WildfireClient')
	def test_process_new_wildfires_skips_existing(self, mock_client, mock_state, mock_crud):
		"""Test processing skips existing wildfires."""
		existing_wildfire = Mock()
		existing_wildfire.event_key = "2025-TEST-001"
		mock_state.active_wildfires = [existing_wildfire]
		mock_client.fetch_wildfires.return_value = {
			"features": [self._get_sample_feature()]
		}
		
		timestamp_filter = datetime.now(timezone.utc) - timedelta(days=2)
		created_count, new_event_keys = WildfireProcessor._process_new_wildfires(timestamp_filter)
		
		assert created_count == 0
		assert len(new_event_keys) == 0
		mock_crud.create_wildfire.assert_not_called()
	
	@patch('app.processors.wildfire_processor.WildfireCRUDService')
	@patch('app.processors.wildfire_processor.state')
	@patch('app.processors.wildfire_processor.WildfireClient')
	def test_process_new_wildfires_handles_errors(self, mock_client, mock_state, mock_crud):
		"""Test processing handles errors gracefully."""
		mock_state.active_wildfires = []
		mock_client.fetch_wildfires.return_value = {
			"features": [self._get_sample_feature()]
		}
		mock_crud.create_wildfire.side_effect = Exception("Test error")
		
		timestamp_filter = datetime.now(timezone.utc) - timedelta(days=2)
		created_count, new_event_keys = WildfireProcessor._process_new_wildfires(timestamp_filter)
		
		assert created_count == 0
		assert len(new_event_keys) == 0


class TestProcessWildfireUpdatesAndCompletion:
	"""Test cases for WildfireProcessor._process_wildfire_updates_and_completion."""
	
	@pytest.fixture
	def sample_wildfire(self):
		"""Create a sample wildfire for testing."""
		location = Location(
			episode_key=None,
			event_key="2025-TEST-001",
			state_fips="35",
			county_fips="033",
			ugc_code="",
			shape=[],
			full_zone_ugc_endpoint="",
			starting_point=Coordinate(latitude=35.814081, longitude=-104.962435)
		)
		return Wildfire(
			event_key="2025-TEST-001",
			episode_key=None,
			arcgis_id="40095",
			location=location,
			acres_burned=20000,
			severity=3,
			start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
			last_modified=datetime(2024, 1, 1, tzinfo=timezone.utc),
			end_date=None,
			cost=300000,
			description="Test fire",
			fuel_source="Grass",
			active=True,
			percent_contained=90
		)
	
	@pytest.fixture
	def sample_feature(self):
		"""Create a sample feature for updates."""
		current_time_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
		return {
			"properties": {
				"OBJECTID": 40095,
				"attr_UniqueFireIdentifier": "2025-TEST-001",
				"attr_ModifiedOnDateTime_dt": current_time_ms,  # Fresh data
				"attr_FireOutDateTime": None,  # Not out
				"attr_PercentContained": 95,  # Not 100% contained
				"poly_GISAcres": 25000,
				"attr_IncidentComplexityLevel": "Type 2 Incident",
				"attr_EstimatedFinalCost": 400000,
				"attr_IncidentName": "Updated Name",
				"attr_IncidentShortDescription": "Updated description",
				"attr_PrimaryFuelModel": "Updated Fuel",
				"attr_SecondaryFuelModel": None
			},
			"geometry": {
				"type": "Polygon",
				"coordinates": [[[-97.5, 32.8], [-97.2, 32.8], [-97.2, 33.1], [-97.5, 33.1], [-97.5, 32.8]]]
			}
		}
	
	@patch('app.processors.wildfire_processor.WildfireCRUDService')
	@patch('app.processors.wildfire_processor.state')
	@patch('app.processors.wildfire_processor.WildfireClient')
	@patch('app.processors.wildfire_processor.settings')
	def test_process_updates_and_completion_updates_active(self, mock_settings, mock_client, mock_state, mock_crud, sample_wildfire, sample_feature):
		"""Test processing updates and keeps active wildfire active."""
		mock_state.active_wildfires = [sample_wildfire]
		mock_client.fetch_wildfires_by_object_ids.return_value = {
			"features": [sample_feature]
		}
		mock_settings.wildfire_staleness_threshold_ms = 7 * 24 * 60 * 60 * 1000
		
		updated_wildfire = Mock()
		updated_wildfire.active = True
		updated_wildfire.event_key = "2025-TEST-001"
		mock_crud.update_wildfire.return_value = updated_wildfire
		
		updated_count, completed_count = WildfireProcessor._process_wildfire_updates_and_completion(set())
		
		assert updated_count == 1
		assert completed_count == 0
		mock_crud.update_wildfire.assert_called_once()
		mock_crud.complete_wildfire.assert_not_called()
	
	@patch('app.processors.wildfire_processor.WildfireCRUDService')
	@patch('app.processors.wildfire_processor.state')
	@patch('app.processors.wildfire_processor.WildfireClient')
	@patch('app.processors.wildfire_processor.settings')
	def test_process_updates_and_completion_deactivates(self, mock_settings, mock_client, mock_state, mock_crud, sample_wildfire):
		"""Test processing deactivates wildfire when conditions met."""
		mock_state.active_wildfires = [sample_wildfire]
		current_time_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
		stale_time_ms = current_time_ms - (8 * 24 * 60 * 60 * 1000)  # 8 days ago (stale)
		
		feature = {
			"properties": {
				"OBJECTID": 40095,
				"attr_UniqueFireIdentifier": "2025-TEST-001",
				"attr_ModifiedOnDateTime_dt": stale_time_ms,  # Stale data
				"attr_FireOutDateTime": None,
				"attr_PercentContained": 95,
				"poly_GISAcres": 25000,
				"attr_IncidentComplexityLevel": "Type 2 Incident",
				"attr_EstimatedFinalCost": 400000,
				"attr_IncidentName": "Updated Name",
				"attr_IncidentShortDescription": "Updated description",
				"attr_PrimaryFuelModel": "Updated Fuel",
				"attr_SecondaryFuelModel": None
			},
			"geometry": {
				"type": "Polygon",
				"coordinates": [[[-97.5, 32.8], [-97.2, 32.8], [-97.2, 33.1], [-97.5, 33.1], [-97.5, 32.8]]]
			}
		}
		
		mock_client.fetch_wildfires_by_object_ids.return_value = {
			"features": [feature]
		}
		mock_settings.wildfire_staleness_threshold_ms = 7 * 24 * 60 * 60 * 1000
		
		updated_wildfire = Mock()
		updated_wildfire.active = True
		updated_wildfire.event_key = "2025-TEST-001"
		mock_crud.update_wildfire.return_value = updated_wildfire
		
		updated_count, completed_count = WildfireProcessor._process_wildfire_updates_and_completion(set())
		
		assert updated_count == 1
		assert completed_count == 1  # Should be deactivated due to stale data
		mock_crud.complete_wildfire.assert_called_once_with("2025-TEST-001")
	
	@patch('app.processors.wildfire_processor.state')
	@patch('app.processors.wildfire_processor.WildfireClient')
	def test_process_updates_and_completion_no_active_wildfires(self, mock_client, mock_state):
		"""Test processing with no active wildfires."""
		mock_state.active_wildfires = []
		
		updated_count, completed_count = WildfireProcessor._process_wildfire_updates_and_completion(set())
		
		assert updated_count == 0
		assert completed_count == 0
		mock_client.fetch_wildfires_by_object_ids.assert_not_called()
	
	@patch('app.processors.wildfire_processor.WildfireCRUDService')
	@patch('app.processors.wildfire_processor.state')
	@patch('app.processors.wildfire_processor.WildfireClient')
	@patch('app.processors.wildfire_processor.settings')
	def test_process_updates_skips_new_event_keys(self, mock_settings, mock_client, mock_state, mock_crud, sample_wildfire, sample_feature):
		"""Test processing skips newly created wildfires."""
		mock_state.active_wildfires = [sample_wildfire]
		mock_client.fetch_wildfires_by_object_ids.return_value = {
			"features": [sample_feature]
		}
		mock_settings.wildfire_staleness_threshold_ms = 7 * 24 * 60 * 60 * 1000
		
		new_event_keys = {"2025-TEST-001"}  # Same as sample_wildfire.event_key
		
		updated_count, completed_count = WildfireProcessor._process_wildfire_updates_and_completion(new_event_keys)
		
		assert updated_count == 0
		assert completed_count == 0
		mock_crud.update_wildfire.assert_not_called()


class TestSyncWildfireData:
	"""Test cases for WildfireProcessor.sync_wildfire_data."""
	
	@patch('app.processors.wildfire_processor.WildfireProcessor._process_wildfire_updates_and_completion')
	@patch('app.processors.wildfire_processor.WildfireProcessor._process_new_wildfires')
	@patch('app.processors.wildfire_processor.state')
	def test_sync_wildfire_data_success(self, mock_state, mock_process_new, mock_process_updates):
		"""Test successful wildfire sync."""
		mock_state.get_wildfire_last_poll_date.return_value = None
		mock_state.set_wildfire_last_poll_date = Mock()
		mock_process_new.return_value = (5, {"key1", "key2"})
		mock_process_updates.return_value = (3, 2)
		
		result = WildfireProcessor.sync_wildfire_data()
		
		assert result["created"] == 5
		assert result["updated"] == 3
		assert result["completed"] == 2
		mock_process_new.assert_called_once()
		mock_process_updates.assert_called_once()
		mock_state.set_wildfire_last_poll_date.assert_called_once()
	
	@patch('app.processors.wildfire_processor.WildfireProcessor._process_wildfire_updates_and_completion')
	@patch('app.processors.wildfire_processor.WildfireProcessor._process_new_wildfires')
	@patch('app.processors.wildfire_processor.state')
	def test_sync_wildfire_data_with_last_poll_date(self, mock_state, mock_process_new, mock_process_updates):
		"""Test sync with existing last poll date."""
		last_poll = datetime.now(timezone.utc) - timedelta(days=5)
		mock_state.get_wildfire_last_poll_date.return_value = last_poll
		mock_state.set_wildfire_last_poll_date = Mock()
		mock_process_new.return_value = (0, set())
		mock_process_updates.return_value = (0, 0)
		
		result = WildfireProcessor.sync_wildfire_data()
		
		# Should use last_poll_date - 2 days
		call_args = mock_process_new.call_args[0][0]
		expected_timestamp = last_poll - timedelta(days=2)
		assert abs((call_args - expected_timestamp).total_seconds()) < 1  # Within 1 second


class TestPollMethods:
	"""Test cases for polling helper methods."""
	
	@patch('app.processors.wildfire_processor.WildfireClient')
	def test_poll_for_new_wildfires(self, mock_client):
		"""Test polling for new wildfires."""
		mock_client.fetch_wildfires.return_value = {
			"features": [{"test": "feature"}]
		}
		
		timestamp_filter = datetime.now(timezone.utc)
		result = WildfireProcessor._poll_for_new_wildfires(timestamp_filter)
		
		assert len(result) == 1
		assert result[0] == {"test": "feature"}
		mock_client.fetch_wildfires.assert_called_once_with(timestamp_filter)
	
	@patch('app.processors.wildfire_processor.WildfireClient')
	def test_poll_for_wildfires_updates(self, mock_client):
		"""Test polling for wildfire updates."""
		mock_client.fetch_wildfires_by_object_ids.return_value = {
			"features": [
				{"properties": {"OBJECTID": 123}, "geometry": {}},
				{"properties": {"OBJECTID": 456}, "geometry": {}}
			]
		}
		
		object_ids = [123, 456]
		result = WildfireProcessor._poll_for_wildfires_updates(object_ids)
		
		assert len(result) == 2
		assert "123" in result
		assert "456" in result
		mock_client.fetch_wildfires_by_object_ids.assert_called_once_with(object_ids)
	
	@patch('app.processors.wildfire_processor.WildfireClient')
	def test_poll_for_wildfires_updates_empty(self, mock_client):
		"""Test polling for updates with empty object_ids."""
		mock_client.fetch_wildfires_by_object_ids.return_value = {
			"features": []
		}
		
		result = WildfireProcessor._poll_for_wildfires_updates([])
		
		assert result == {}
		mock_client.fetch_wildfires_by_object_ids.assert_called_once_with([])
