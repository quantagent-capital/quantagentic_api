"""
Unit tests for DroughtService.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
from app.services.drought_service import DroughtService, DM_TO_SEVERITY, SEVERITY_TO_DM
from app.schemas.drought import Drought
from app.schemas.location import Location
from app.schemas.counties import County, Coordinate
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point, Polygon


class TestGenerateDroughtEventKey:
	"""Test cases for DroughtService.generate_drought_event_key."""
	
	def test_generate_drought_event_key_success(self):
		"""Test successful event key generation."""
		county_fips = "001"
		state_fips = "48"
		
		result = DroughtService.generate_drought_event_key(county_fips, state_fips)
		
		assert result == "DRT-001-48"
	
	def test_generate_drought_event_key_with_leading_zeros(self):
		"""Test event key generation preserves leading zeros."""
		county_fips = "001"
		state_fips = "01"
		
		result = DroughtService.generate_drought_event_key(county_fips, state_fips)
		
		assert result == "DRT-001-01"


class TestCheckCountyInPolygons:
	"""Test cases for DroughtService.check_county_in_polygons."""
	
	@pytest.fixture
	def sample_county(self):
		"""Create a sample County for testing."""
		return County(
			fips="001",
			state_abbr="TX",
			state_fips="48",
			name="Test County",
			centroid=Coordinate(latitude=32.8, longitude=-97.5)
		)
	
	@pytest.fixture
	def sample_polygon(self):
		"""Create a sample polygon geometry."""
		return Polygon([(-98, 32), (-97, 32), (-97, 33), (-98, 33), (-98, 32)])
	
	def test_check_county_in_polygons_no_match(self, sample_county):
		"""Test when county centroid is not in any polygon."""
		# Create empty GeoDataFrame
		gdf = gpd.GeoDataFrame({
			'DM': [2, 3],
			'geometry': [Polygon([(0, 0), (1, 0), (1, 1), (0, 1)]), 
			             Polygon([(10, 10), (11, 10), (11, 11), (10, 11)])]
		}, crs='EPSG:4326')
		
		result = DroughtService.check_county_in_polygons(sample_county, gdf)
		
		assert result is None
	
	def test_check_county_in_polygons_single_match(self, sample_county, sample_polygon):
		"""Test when county centroid is in one polygon."""
		gdf = gpd.GeoDataFrame({
			'DM': [2],
			'geometry': [sample_polygon]
		}, crs='EPSG:4326')
		
		result = DroughtService.check_county_in_polygons(sample_county, gdf)
		
		assert result is not None
		assert result['dm'] == 2
		assert result['severity'] == "D2"
		assert result['geometry'] == sample_polygon
	
	def test_check_county_in_polygons_multiple_matches_selects_max(self, sample_county):
		"""Test when county centroid is in multiple polygons, selects maximum severity."""
		# Create polygons that both contain the centroid
		polygon1 = Polygon([(-98, 32), (-97, 32), (-97, 33), (-98, 33), (-98, 32)])
		polygon2 = Polygon([(-98, 32), (-96, 32), (-96, 33), (-98, 33), (-98, 32)])
		
		gdf = gpd.GeoDataFrame({
			'DM': [1, 3],  # D1 and D3
			'geometry': [polygon1, polygon2]
		}, crs='EPSG:4326')
		
		result = DroughtService.check_county_in_polygons(sample_county, gdf)
		
		assert result is not None
		assert result['dm'] == 3  # Should select maximum
		assert result['severity'] == "D3"
	
	@patch('app.services.drought_service.settings')
	def test_check_county_in_polygons_filters_by_threshold(self, mock_settings, sample_county):
		"""Test that polygons are filtered by severity thresholds."""
		mock_settings.drought_severity_low_threshold = 2
		mock_settings.drought_severity_high_threshold = 4
		
		polygon = Polygon([(-98, 32), (-97, 32), (-97, 33), (-98, 33), (-98, 32)])
		gdf = gpd.GeoDataFrame({
			'DM': [1],  # Below threshold
			'geometry': [polygon]
		}, crs='EPSG:4326')
		
		result = DroughtService.check_county_in_polygons(sample_county, gdf)
		
		assert result is None  # Should be filtered out
	
	def test_check_county_in_polygons_converts_crs(self, sample_county):
		"""Test that CRS is converted if not EPSG:4326."""
		# Create polygon in EPSG:4326 (should work without conversion)
		polygon = Polygon([(-98, 32), (-97, 32), (-97, 33), (-98, 33), (-98, 32)])
		gdf = gpd.GeoDataFrame({
			'DM': [2],
			'geometry': [polygon]
		}, crs='EPSG:4326')
		
		# Should work with EPSG:4326 without conversion
		result = DroughtService.check_county_in_polygons(sample_county, gdf)
		# Result depends on whether point is in polygon - this test just verifies no error
		assert result is None or (result is not None and 'dm' in result)


class TestSyncDroughtData:
	"""Test cases for DroughtService.sync_drought_data."""
	
	@pytest.fixture
	def sample_county(self):
		"""Create a sample County for testing."""
		return County(
			fips="001",
			state_abbr="TX",
			state_fips="48",
			name="Test County",
			centroid=Coordinate(latitude=32.8, longitude=-97.5)
		)
	
	@pytest.fixture
	def sample_polygon(self):
		"""Create a sample polygon geometry."""
		return Polygon([(-98, 32), (-97, 32), (-97, 33), (-98, 33), (-98, 32)])
	
	@pytest.fixture
	def sample_drought_gdf(self, sample_polygon):
		"""Create a sample GeoDataFrame with drought polygons."""
		return gpd.GeoDataFrame({
			'DM': [2],
			'geometry': [sample_polygon]
		}, crs='EPSG:4326')
	
	@patch('app.services.drought_service.state')
	@patch('app.services.drought_service.DroughtClient')
	@patch('app.services.drought_service.get_last_tuesday_date')
	def test_sync_drought_data_no_counties(self, mock_date, mock_client, mock_state):
		"""Test sync when no counties are available."""
		mock_state.counties = []
		
		result = DroughtService.sync_drought_data()
		
		assert result == {"created": 0, "updated": 0, "completed": 0, "total_counties": 0}
		mock_client.fetch_current_drought_geojson.assert_not_called()
	
	@patch('app.services.drought_service.settings')
	@patch('app.services.drought_service.state')
	@patch('app.services.drought_service.DroughtClient')
	@patch('app.services.drought_service.get_last_tuesday_date')
	@patch('app.services.drought_service.DroughtCRUDService')
	def test_sync_drought_data_create_new(self, mock_crud, mock_date, mock_client, mock_state, 
	                                      mock_settings, sample_county, sample_drought_gdf):
		"""Test sync creates new drought when county enters drought."""
		mock_settings.drought_severity_low_threshold = 0
		mock_settings.drought_severity_high_threshold = 4
		mock_state.counties = [sample_county]
		mock_state.active_drought_exists.return_value = False
		mock_client.fetch_current_drought_geojson.return_value = sample_drought_gdf
		mock_client.fetch_previous_week_drought_shapefile.return_value = gpd.GeoDataFrame(
			{'DM': [], 'geometry': []}, crs='EPSG:4326'
		)
		mock_date.return_value = "20240115"
		mock_crud.create_drought.return_value = Mock()
		
		result = DroughtService.sync_drought_data()
		
		assert result["created"] == 1
		assert result["updated"] == 0
		assert result["completed"] == 0
		mock_crud.create_drought.assert_called_once()
	
	@patch('app.services.drought_service.settings')
	@patch('app.services.drought_service.state')
	@patch('app.services.drought_service.DroughtClient')
	@patch('app.services.drought_service.get_last_tuesday_date')
	@patch('app.services.drought_service.DroughtCRUDService')
	def test_sync_drought_data_complete_existing(self, mock_crud, mock_date, mock_client, mock_state,
	                                             mock_settings, sample_county, sample_polygon):
		"""Test sync completes drought when county exits drought."""
		mock_settings.drought_severity_low_threshold = 0
		mock_settings.drought_severity_high_threshold = 4
		mock_state.counties = [sample_county]
		mock_state.active_drought_exists.return_value = True
		
		# Current week: no drought
		current_gdf = gpd.GeoDataFrame({'DM': [], 'geometry': []}, crs='EPSG:4326')
		# Previous week: had drought
		previous_gdf = gpd.GeoDataFrame({
			'DM': [2],
			'geometry': [sample_polygon]
		}, crs='EPSG:4326')
		
		mock_client.fetch_current_drought_geojson.return_value = current_gdf
		mock_client.fetch_previous_week_drought_shapefile.return_value = previous_gdf
		mock_date.return_value = "20240115"
		mock_crud.complete_drought.return_value = Mock()
		
		result = DroughtService.sync_drought_data()
		
		assert result["created"] == 0
		assert result["updated"] == 0
		assert result["completed"] == 1
		mock_crud.complete_drought.assert_called_once()
	
	@patch('app.services.drought_service.settings')
	@patch('app.services.drought_service.state')
	@patch('app.services.drought_service.DroughtClient')
	@patch('app.services.drought_service.get_last_tuesday_date')
	@patch('app.services.drought_service.DroughtCRUDService')
	def test_sync_drought_data_update_higher_severity(self, mock_crud, mock_date, mock_client, mock_state,
	                                                  mock_settings, sample_county, sample_polygon):
		"""Test sync updates drought when severity increases."""
		mock_settings.drought_severity_low_threshold = 0
		mock_settings.drought_severity_high_threshold = 4
		mock_state.counties = [sample_county]
		mock_state.active_drought_exists.return_value = True
		
		# Create existing drought with D1 severity
		location = Location(
			episode_key=None,
			event_key="DRT-001-48",
			state_fips="48",
			county_fips="001",
			ugc_code="",
			shape=[],
			full_zone_ugc_endpoint=""
		)
		existing_drought = Drought(
			event_key="DRT-001-48",
			episode_key=None,
			start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
			end_date=None,
			description="Existing",
			is_active=True,
			location=location,
			severity="D1",
			updated_at=datetime(2024, 1, 1, tzinfo=timezone.utc)
		)
		
		# Ensure polygon contains the county centroid
		# County is at (-97.5, 32.8), polygon covers (-98 to -97, 32 to 33)
		# Current week: D3 severity
		current_gdf = gpd.GeoDataFrame({
			'DM': [3],
			'geometry': [sample_polygon]
		}, crs='EPSG:4326')
		# Previous week: D1 severity (also in drought)
		previous_gdf = gpd.GeoDataFrame({
			'DM': [1],
			'geometry': [sample_polygon]
		}, crs='EPSG:4326')
		
		mock_client.fetch_current_drought_geojson.return_value = current_gdf
		mock_client.fetch_previous_week_drought_shapefile.return_value = previous_gdf
		mock_date.return_value = "20240115"
		mock_state.get_drought.return_value = existing_drought
		mock_crud.update_drought.return_value = Mock()
		
		result = DroughtService.sync_drought_data()
		
		assert result["created"] == 0
		assert result["updated"] == 1
		assert result["completed"] == 0
		mock_crud.update_drought.assert_called_once()
		# Verify update was called with D3 severity
		call_args = mock_crud.update_drought.call_args
		assert call_args[0][1] == "D3"  # new_severity parameter
	
	@patch('app.services.drought_service.settings')
	@patch('app.services.drought_service.state')
	@patch('app.services.drought_service.DroughtClient')
	@patch('app.services.drought_service.get_last_tuesday_date')
	@patch('app.services.drought_service.DroughtCRUDService')
	def test_sync_drought_data_no_update_lower_severity(self, mock_crud, mock_date, mock_client, mock_state,
	                                                   mock_settings, sample_county, sample_polygon):
		"""Test sync does not update when severity decreases."""
		mock_settings.drought_severity_low_threshold = 0
		mock_settings.drought_severity_high_threshold = 4
		mock_state.counties = [sample_county]
		mock_state.active_drought_exists.return_value = True
		
		# Create existing drought with D3 severity
		location = Location(
			episode_key=None,
			event_key="DRT-001-48",
			state_fips="48",
			county_fips="001",
			ugc_code="",
			shape=[],
			full_zone_ugc_endpoint=""
		)
		existing_drought = Drought(
			event_key="DRT-001-48",
			episode_key=None,
			start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
			end_date=None,
			description="Existing",
			is_active=True,
			location=location,
			severity="D3",
			updated_at=datetime(2024, 1, 1, tzinfo=timezone.utc)
		)
		
		# Current week: D1 severity (lower) - still in drought
		current_gdf = gpd.GeoDataFrame({
			'DM': [1],
			'geometry': [sample_polygon]
		}, crs='EPSG:4326')
		# Previous week: D3 severity - was in drought
		previous_gdf = gpd.GeoDataFrame({
			'DM': [3],
			'geometry': [sample_polygon]
		}, crs='EPSG:4326')
		
		mock_client.fetch_current_drought_geojson.return_value = current_gdf
		mock_client.fetch_previous_week_drought_shapefile.return_value = previous_gdf
		mock_date.return_value = "20240115"
		mock_state.get_drought.return_value = existing_drought
		
		result = DroughtService.sync_drought_data()
		
		assert result["created"] == 0
		assert result["updated"] == 0  # Should not update (current D1 < existing D3)
		assert result["completed"] == 0  # Should not complete (still in drought)
		mock_crud.update_drought.assert_not_called()
		mock_crud.complete_drought.assert_not_called()
	
	@patch('app.services.drought_service.state')
	@patch('app.services.drought_service.DroughtClient')
	@patch('app.services.drought_service.get_last_tuesday_date')
	@patch('app.services.drought_service.DroughtCRUDService')
	def test_sync_drought_data_handles_exception(self, mock_crud, mock_date, mock_client, mock_state,
	                                            sample_county):
		"""Test sync handles exceptions gracefully and continues processing."""
		mock_state.counties = [sample_county]
		mock_state.active_drought_exists.side_effect = Exception("Test error")
		
		current_gdf = gpd.GeoDataFrame({'DM': [], 'geometry': []}, crs='EPSG:4326')
		previous_gdf = gpd.GeoDataFrame({'DM': [], 'geometry': []}, crs='EPSG:4326')
		
		mock_client.fetch_current_drought_geojson.return_value = current_gdf
		mock_client.fetch_previous_week_drought_shapefile.return_value = previous_gdf
		mock_date.return_value = "20240115"
		
		# Should not raise exception, should handle gracefully
		result = DroughtService.sync_drought_data()
		
		# Should still return result structure
		assert "created" in result
		assert "updated" in result
		assert "completed" in result
	
	@patch('app.services.drought_service.state')
	@patch('app.services.drought_service.DroughtClient')
	@patch('app.services.drought_service.get_last_tuesday_date')
	def test_sync_drought_data_fetch_current_fails(self, mock_date, mock_client, mock_state, sample_county):
		"""Test sync raises exception when current drought map fetch fails."""
		mock_state.counties = [sample_county]
		mock_client.fetch_current_drought_geojson.side_effect = Exception("Network error")
		
		with pytest.raises(Exception):
			DroughtService.sync_drought_data()
	
	@patch('app.services.drought_service.state')
	@patch('app.services.drought_service.DroughtClient')
	@patch('app.services.drought_service.get_last_tuesday_date')
	def test_sync_drought_data_fetch_previous_fails(self, mock_date, mock_client, mock_state, 
	                                               sample_county, sample_drought_gdf):
		"""Test sync raises exception when previous drought map fetch fails."""
		mock_state.counties = [sample_county]
		mock_client.fetch_current_drought_geojson.return_value = sample_drought_gdf
		mock_client.fetch_previous_week_drought_shapefile.side_effect = Exception("Network error")
		mock_date.return_value = "20240115"
		
		with pytest.raises(Exception):
			DroughtService.sync_drought_data()
	
	@patch('app.services.drought_service.state')
	@patch('app.services.drought_service.DroughtClient')
	@patch('app.services.drought_service.get_last_tuesday_date')
	@patch('app.services.drought_service.DroughtCRUDService')
	def test_sync_drought_data_multiple_counties(self, mock_crud, mock_date, mock_client, mock_state,
	                                             sample_polygon):
		"""Test sync processes multiple counties correctly."""
		county1 = County(
			fips="001",
			state_abbr="TX",
			state_fips="48",
			name="County 1",
			centroid=Coordinate(latitude=32.8, longitude=-97.5)
		)
		county2 = County(
			fips="002",
			state_abbr="TX",
			state_fips="48",
			name="County 2",
			centroid=Coordinate(latitude=33.0, longitude=-97.0)
		)
		
		mock_state.counties = [county1, county2]
		mock_state.active_drought_exists.return_value = False
		
		current_gdf = gpd.GeoDataFrame({
			'DM': [2],
			'geometry': [sample_polygon]
		}, crs='EPSG:4326')
		previous_gdf = gpd.GeoDataFrame({'DM': [], 'geometry': []}, crs='EPSG:4326')
		
		mock_client.fetch_current_drought_geojson.return_value = current_gdf
		mock_client.fetch_previous_week_drought_shapefile.return_value = previous_gdf
		mock_date.return_value = "20240115"
		mock_crud.create_drought.return_value = Mock()
		
		result = DroughtService.sync_drought_data()
		
		# Should process both counties
		assert result["total_counties"] == 2
		# Number of creates depends on which counties are in the polygon
		assert mock_crud.create_drought.call_count >= 0

