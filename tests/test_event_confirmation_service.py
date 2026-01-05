"""
Tests for EventConfirmationService.
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, timezone
from app.services.event_confirmation_service import EventConfirmationService
from app.schemas.event import Event
from app.schemas.location import Location, Coordinate
from app.shared_models.nws_poller_models import FilteredLSR


class TestEventConfirmationService:
	"""Test suite for EventConfirmationService."""
	
	@pytest.fixture
	def sample_event(self):
		"""Create a sample event for testing."""
		return Event(
			event_key="TEST-KEY-001",
			nws_alert_id="alert-1",
			event_type="TOR",
			start_date=datetime.now(timezone.utc),
			description="Test tornado warning",
			is_active=True,
			confirmed=False,
			raw_vtec="/O.NEW.TEST.TO.W.0015.240115T1000Z/",
			office="KTEST",
			locations=[
				Location(
					event_key="TEST-KEY-001",
					state_fips="48",
					county_fips="113",
					ugc_code="TXC113",
					full_zone_ugc_endpoint="https://api.weather.gov/zones/forecast/TXC113",
					full_shape=[[Coordinate(latitude=32.8, longitude=-97.5)]]
				)
			]
		)
	
	@pytest.fixture
	def sample_lsr(self):
		"""Create a sample LSR for testing."""
		return FilteredLSR(
			fully_qualified_url="https://api.weather.gov/lsr/test",
			lsr_id="lsr-1",
			office="KTEST",
			wmo_collective="NWUS56",
			reported_at="2024-01-15T11:00:00Z",
			description="1100 AM     Tornado            Test City                32.8N 97.5W"
		)
	
	@pytest.fixture
	def mock_nws_client(self):
		"""Mock NWS client."""
		with patch('app.services.event_confirmation_service.NWSClient') as mock_client_class:
			mock_client = AsyncMock()
			mock_client.get_lsr = AsyncMock()
			mock_client.close = AsyncMock()
			mock_client_class.return_value = mock_client
			yield mock_client
	
	@pytest.fixture
	def mock_state(self):
		"""Mock state object."""
		with patch('app.services.event_confirmation_service.state') as mock_state:
			yield mock_state
	
	@pytest.fixture
	def mock_executor(self):
		"""Mock EventConfirmationExecutor."""
		with patch('app.services.event_confirmation_service.EventConfirmationExecutor') as mock_executor_class:
			mock_executor = Mock()
			mock_executor_class.return_value = mock_executor
			yield mock_executor
	
	@pytest.mark.asyncio
	async def test_confirm_event_already_confirmed(self, sample_event, mock_nws_client, mock_state):
		"""Test that already confirmed events are skipped."""
		sample_event.confirmed = True
		
		result = await EventConfirmationService.confirm_event(sample_event)
		
		assert result["message"] == "Event already confirmed"
		assert result["lsrs_processed"] == 0
		mock_nws_client.get_lsr.assert_not_called()
	
	@pytest.mark.asyncio
	async def test_confirm_event_no_office(self, sample_event, mock_nws_client, mock_state):
		"""Test that events without office code raise ValueError."""
		sample_event.office = None
		
		with pytest.raises(ValueError, match="does not have an office code"):
			await EventConfirmationService.confirm_event(sample_event)
	
	@pytest.mark.asyncio
	async def test_confirm_event_no_lsrs(self, sample_event, mock_nws_client, mock_state, mock_executor):
		"""Test confirmation when no LSRs are found."""
		mock_nws_client.get_lsr.return_value = []
		
		result = await EventConfirmationService.confirm_event(sample_event)
		
		assert result["message"] == "No LSRs found"
		assert result["lsrs_processed"] == 0
		mock_nws_client.get_lsr.assert_called_once_with(sample_event.office, sample_event.start_date)
		mock_executor.execute.assert_not_called()
	
	@pytest.mark.asyncio
	async def test_confirm_event_successful_confirmation(self, sample_event, sample_lsr, mock_nws_client, mock_state, mock_executor):
		"""Test successful event confirmation."""
		from app.crews.event_confirmation_crew.models import EventConfirmationOutput
		
		mock_nws_client.get_lsr.return_value = [sample_lsr]
		mock_state.is_lsr_polled.return_value = False  # LSR not yet polled
		
		# Mock the executor result
		mock_result = MagicMock()
		mock_result.pydantic = EventConfirmationOutput(
			confirmed=True,
			observed_coordinate=Coordinate(latitude=32.8, longitude=-97.5),
			location_index=0
		)
		mock_executor.execute.return_value = mock_result
		
		result = await EventConfirmationService.confirm_event(sample_event)
		
		assert result["confirmed"] is True
		assert result["lsrs_processed"] == 1
		assert result["observed_coordinate"] is not None
		assert sample_event.confirmed is True
		# Only the location at index 0 should have the observed coordinate
		assert sample_event.locations[0].observed_coordinate == Coordinate(latitude=32.8, longitude=-97.5)
		mock_state.add_polled_lsr_id.assert_called_once_with(sample_lsr.lsr_id)
		mock_state.update_event.assert_called_once()
		mock_executor.execute.assert_called_once_with(
			sample_event.event_key,
			description=sample_lsr.description,
			issuing_office=sample_lsr.office
		)
	
	@pytest.mark.asyncio
	async def test_confirm_event_no_confirmation_found(self, sample_event, sample_lsr, mock_nws_client, mock_state, mock_executor):
		"""Test confirmation when no LSR confirms the event."""
		from app.crews.event_confirmation_crew.models import EventConfirmationOutput
		
		mock_nws_client.get_lsr.return_value = [sample_lsr]
		mock_state.is_lsr_polled.return_value = False  # LSR not yet polled
		
		# Mock the executor result - not confirmed
		mock_result = MagicMock()
		mock_result.pydantic = EventConfirmationOutput(
			confirmed=False,
			observed_coordinate=None,
			location_index=None
		)
		mock_executor.execute.return_value = mock_result
		
		result = await EventConfirmationService.confirm_event(sample_event)
		
		assert result["confirmed"] is False
		assert result["lsrs_processed"] == 1
		assert result["observed_coordinate"] is None
		assert sample_event.confirmed is False
		# LSR should still be marked as polled even if not confirmed
		mock_state.add_polled_lsr_id.assert_called_once_with(sample_lsr.lsr_id)
		mock_state.update_event.assert_not_called()
	
	@pytest.mark.asyncio
	async def test_confirm_event_multiple_lsrs_processes_all(self, sample_event, mock_nws_client, mock_state, mock_executor):
		"""Test that all LSRs are processed and each confirmation sets coordinate on its location."""
		from app.crews.event_confirmation_crew.models import EventConfirmationOutput
		
		# Add a second location to test multiple confirmations
		sample_event.locations.append(
			Location(
				event_key="TEST-KEY-001",
				state_fips="48",
				county_fips="115",
				ugc_code="TXC115",
				full_zone_ugc_endpoint="https://api.weather.gov/zones/forecast/TXC115",
				full_shape=[[Coordinate(latitude=33.0, longitude=-97.0)]]
			)
		)
		
		lsr1 = FilteredLSR(
			fully_qualified_url="https://api.weather.gov/lsr/test1",
			lsr_id="lsr-1",
			office="KTEST",
			wmo_collective="NWUS56",
			reported_at="2024-01-15T11:00:00Z",
			description="LSR 1"
		)
		lsr2 = FilteredLSR(
			fully_qualified_url="https://api.weather.gov/lsr/test2",
			lsr_id="lsr-2",
			office="KTEST",
			wmo_collective="NWUS56",
			reported_at="2024-01-15T11:00:00Z",
			description="LSR 2"
		)
		
		mock_nws_client.get_lsr.return_value = [lsr1, lsr2]
		mock_state.is_lsr_polled.return_value = False  # LSRs not yet polled
		
		# First LSR confirms location 0
		mock_result1 = MagicMock()
		mock_result1.pydantic = EventConfirmationOutput(
			confirmed=True,
			observed_coordinate=Coordinate(latitude=32.8, longitude=-97.5),
			location_index=0
		)
		
		# Second LSR confirms location 1
		mock_result2 = MagicMock()
		mock_result2.pydantic = EventConfirmationOutput(
			confirmed=True,
			observed_coordinate=Coordinate(latitude=33.0, longitude=-97.0),
			location_index=1
		)
		
		mock_executor.execute.side_effect = [mock_result1, mock_result2]
		
		result = await EventConfirmationService.confirm_event(sample_event)
		
		# Should process both LSRs
		assert result["lsrs_processed"] == 2
		assert result["confirmations_count"] == 2
		assert mock_executor.execute.call_count == 2
		# Both LSRs should be marked as polled
		assert mock_state.add_polled_lsr_id.call_count == 2
		mock_state.add_polled_lsr_id.assert_any_call(lsr1.lsr_id)
		mock_state.add_polled_lsr_id.assert_any_call(lsr2.lsr_id)
		# Both locations should have their coordinates set
		assert sample_event.locations[0].observed_coordinate.latitude == 32.8
		assert sample_event.locations[1].observed_coordinate.latitude == 33.0
		# Return value should have last confirmed coordinate
		assert result["confirmed"] is True
		assert result["observed_coordinate"].latitude == 33.0  # Last confirmation
	
	@pytest.mark.asyncio
	async def test_confirm_events_empty_list(self, mock_state):
		"""Test confirm_events with no events to confirm."""
		mock_state.active_and_unconfirmed_events = []
		
		result = await EventConfirmationService.confirm_events()
		
		assert result["events_processed"] == 0
		assert result["events_confirmed"] == 0
		assert result["events_failed"] == 0
		assert result["message"] == "No events to confirm"
	
	@pytest.mark.asyncio
	async def test_confirm_events_single_event_success(self, sample_event, mock_state, mock_nws_client, mock_executor):
		"""Test confirm_events with a single successful confirmation."""
		from app.crews.event_confirmation_crew.models import EventConfirmationOutput
		
		mock_state.active_and_unconfirmed_events = [sample_event]
		mock_nws_client.get_lsr.return_value = []
		
		result = await EventConfirmationService.confirm_events()
		
		assert result["events_processed"] == 1
		assert result["events_confirmed"] == 0  # No LSRs found
		assert result["events_failed"] == 0
		assert len(result["results"]) == 1
	
	@pytest.mark.asyncio
	async def test_confirm_events_multiple_events(self, sample_event, mock_state, mock_nws_client, mock_executor):
		"""Test confirm_events with multiple events."""
		event2 = Event(
			event_key="TEST-KEY-002",
			nws_alert_id="alert-2",
			event_type="SVR",
			start_date=datetime.now(timezone.utc),
			description="Test severe thunderstorm warning",
			is_active=True,
			confirmed=False,
			raw_vtec="/O.NEW.TEST.SV.W.0015.240115T1000Z/",
			office="KTEST",
			locations=[]
		)
		
		mock_state.active_and_unconfirmed_events = [sample_event, event2]
		mock_nws_client.get_lsr.return_value = []
		
		result = await EventConfirmationService.confirm_events()
		
		assert result["events_processed"] == 2
		assert len(result["results"]) == 2
	
	@pytest.mark.asyncio
	async def test_confirm_events_with_concurrency_limit(self, sample_event, mock_state, mock_nws_client, mock_executor):
		"""Test confirm_events with custom concurrency limit."""
		mock_state.active_and_unconfirmed_events = [sample_event]
		mock_nws_client.get_lsr.return_value = []
		
		result = await EventConfirmationService.confirm_events(max_concurrent=3)
		
		assert result["max_concurrent"] == 3
		assert result["events_processed"] == 1
	
	@pytest.mark.asyncio
	async def test_confirm_events_handles_exceptions(self, sample_event, mock_state, mock_nws_client, mock_executor):
		"""Test that confirm_events handles exceptions gracefully."""
		mock_state.active_and_unconfirmed_events = [sample_event]
		mock_nws_client.get_lsr.side_effect = Exception("NWS API error")
		
		result = await EventConfirmationService.confirm_events()
		
		assert result["events_processed"] == 1
		assert result["events_failed"] == 1
		assert result["results"][0]["error"] is not None
		assert result["results"][0]["confirmed"] is False
	
	@pytest.mark.asyncio
	async def test_confirm_event_sets_observed_coordinate_on_specific_location(self, sample_event, sample_lsr, mock_nws_client, mock_state, mock_executor):
		"""Test that confirmed events have observed_coordinate set only on the specific location index."""
		from app.crews.event_confirmation_crew.models import EventConfirmationOutput
		
		# Add a second location to test specificity
		sample_event.locations.append(
			Location(
				event_key="TEST-KEY-001",
				state_fips="48",
				county_fips="115",
				ugc_code="TXC115",
				full_zone_ugc_endpoint="https://api.weather.gov/zones/forecast/TXC115",
				full_shape=[[Coordinate(latitude=33.0, longitude=-97.0)]]
			)
		)
		
		mock_nws_client.get_lsr.return_value = [sample_lsr]
		mock_state.is_lsr_polled.return_value = False
		
		observed_coord = Coordinate(latitude=32.8, longitude=-97.5)
		mock_result = MagicMock()
		mock_result.pydantic = EventConfirmationOutput(
			confirmed=True,
			observed_coordinate=observed_coord,
			location_index=0  # Only first location should get the coordinate
		)
		mock_executor.execute.return_value = mock_result
		
		await EventConfirmationService.confirm_event(sample_event)
		
		# Only location at index 0 should have the observed coordinate
		assert sample_event.locations[0].observed_coordinate == observed_coord
		# Location at index 1 should not have the coordinate
		assert sample_event.locations[1].observed_coordinate is None
	
	@pytest.mark.asyncio
	async def test_confirm_event_filters_polled_lsrs(self, sample_event, sample_lsr, mock_nws_client, mock_state, mock_executor):
		"""Test that already polled LSRs are filtered out."""
		from app.crews.event_confirmation_crew.models import EventConfirmationOutput
		
		lsr1 = FilteredLSR(
			fully_qualified_url="https://api.weather.gov/lsr/test1",
			lsr_id="lsr-1",
			office="KTEST",
			wmo_collective="NWUS56",
			reported_at="2024-01-15T11:00:00Z",
			description="LSR 1"
		)
		lsr2 = FilteredLSR(
			fully_qualified_url="https://api.weather.gov/lsr/test2",
			lsr_id="lsr-2",
			office="KTEST",
			wmo_collective="NWUS56",
			reported_at="2024-01-15T11:00:00Z",
			description="LSR 2"
		)
		
		mock_nws_client.get_lsr.return_value = [lsr1, lsr2]
		
		# First LSR already polled, second is new
		def is_lsr_polled_side_effect(lsr_id):
			return lsr_id == "lsr-1"
		mock_state.is_lsr_polled.side_effect = is_lsr_polled_side_effect
		
		# Mock the executor result - not confirmed
		mock_result = MagicMock()
		mock_result.pydantic = EventConfirmationOutput(
			confirmed=False,
			observed_coordinate=None,
			location_index=None
		)
		mock_executor.execute.return_value = mock_result
		
		result = await EventConfirmationService.confirm_event(sample_event)
		
		# Should only process lsr-2 (new LSR)
		assert result["lsrs_processed"] == 1
		mock_executor.execute.assert_called_once_with(
			sample_event.event_key,
			description=lsr2.description,
			issuing_office=lsr2.office
		)
		# Only lsr-2 should be marked as polled
		mock_state.add_polled_lsr_id.assert_called_once_with(lsr2.lsr_id)
	
	@pytest.mark.asyncio
	async def test_confirm_event_all_lsrs_already_polled(self, sample_event, sample_lsr, mock_nws_client, mock_state, mock_executor):
		"""Test that when all LSRs are already polled, confirmation is skipped."""
		mock_nws_client.get_lsr.return_value = [sample_lsr]
		mock_state.is_lsr_polled.return_value = True  # All LSRs already polled
		
		result = await EventConfirmationService.confirm_event(sample_event)
		
		assert result["message"] == "All LSRs already polled"
		assert result["lsrs_processed"] == 0
		mock_executor.execute.assert_not_called()
		mock_state.add_polled_lsr_id.assert_not_called()
	
	@pytest.mark.asyncio
	async def test_confirm_event_exception_does_not_mark_lsr_as_polled(self, sample_event, mock_nws_client, mock_state, mock_executor):
		"""Test that if an exception occurs during LSR processing, the LSR is not marked as polled."""
		from app.crews.event_confirmation_crew.models import EventConfirmationOutput
		
		lsr1 = FilteredLSR(
			fully_qualified_url="https://api.weather.gov/lsr/test1",
			lsr_id="lsr-1",
			office="KTEST",
			wmo_collective="NWUS56",
			reported_at="2024-01-15T11:00:00Z",
			description="LSR 1"
		)
		lsr2 = FilteredLSR(
			fully_qualified_url="https://api.weather.gov/lsr/test2",
			lsr_id="lsr-2",
			office="KTEST",
			wmo_collective="NWUS56",
			reported_at="2024-01-15T11:00:00Z",
			description="LSR 2"
		)
		
		mock_nws_client.get_lsr.return_value = [lsr1, lsr2]
		mock_state.is_lsr_polled.return_value = False
		
		# First LSR raises exception, second succeeds
		mock_result2 = MagicMock()
		mock_result2.pydantic = EventConfirmationOutput(
			confirmed=False,
			observed_coordinate=None,
			location_index=None
		)
		
		mock_executor.execute.side_effect = [
			Exception("Processing error"),  # First LSR fails
			mock_result2  # Second LSR succeeds
		]
		
		result = await EventConfirmationService.confirm_event(sample_event)
		
		# Only second LSR should be marked as polled (first failed with exception)
		assert result["lsrs_processed"] == 1  # Only successful one counts
		mock_state.add_polled_lsr_id.assert_called_once_with(lsr2.lsr_id)
		# Should have attempted to process both
		assert mock_executor.execute.call_count == 2

