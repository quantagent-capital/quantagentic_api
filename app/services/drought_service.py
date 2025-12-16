from typing import Dict, Optional
from app.schemas.counties import County
from app.config import settings
from app.state import state
from app.http_client.drought_client import DroughtClient
from app.services.drought_crud_service import DroughtCRUDService
from app.utils.datetime_utils import get_last_tuesday_date
import logging
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
logger = logging.getLogger(__name__)


# DM integer to severity string mapping
DM_TO_SEVERITY = {
	0: "D0",  # Abnormally Dry
	1: "D1",  # Moderate Drought
	2: "D2",  # Severe Drought
	3: "D3",  # Extreme Drought
	4: "D4"   # Exceptional Drought
}

SEVERITY_TO_DM = {v: k for k, v in DM_TO_SEVERITY.items()}


class DroughtService:
	"""Service for drought data synchronization and event management."""
	@staticmethod
	def sync_drought_data() -> Dict[str, int]:
		"""
		Sync drought data by comparing current and previous week drought maps.
		Creates, updates, or completes drought events based on county intersections.
		
		Returns:
			Dictionary with counts of created, updated, and completed events
		"""
		logger.info("Starting drought data sync")
		
		# 1. Load counties from state
		counties = state.counties
		logger.info(f"Loaded {len(counties)} counties from state")
		
		if not counties:
			logger.warning("No counties found in state. Cannot sync drought data.")
			return {"created": 0, "updated": 0, "completed": 0, "total_counties": 0}
		
		# 2. Fetch current and previous week drought maps
		try:
			current_gdf = DroughtClient.fetch_current_drought_geojson()
			logger.info(f"Fetched current drought map with {len(current_gdf)} polygons")
		except Exception as e:
			logger.error(f"Failed to fetch current drought map: {str(e)}")
			raise
		
		try:
			previous_date_str = get_last_tuesday_date()
			previous_gdf = DroughtClient.fetch_previous_week_drought_shapefile(previous_date_str)
			logger.info(f"Fetched previous week drought map ({previous_date_str}) with {len(previous_gdf)} polygons")
		except Exception as e:
			logger.error(f"Failed to fetch previous week drought map: {str(e)}")
			raise
		
		# 3. Process each county
		created_count = 0
		updated_count = 0
		completed_count = 0
		processed_counties = 0
		
		for county in counties:
			try:
				# Check if county is in current week polygons
				current_drought = DroughtService.check_county_in_polygons(county, current_gdf)
				current_in_drought = current_drought is not None
				current_severity = current_drought['severity'] if current_drought else None
				current_dm = current_drought['dm'] if current_drought else None
				
				# Check if county is in previous week polygons
				previous_drought = DroughtService.check_county_in_polygons(county, previous_gdf)
				previous_in_drought = previous_drought is not None
				
				# Generate event key for this county
				event_key = DroughtService.generate_drought_event_key(county.fips, county.state_fips)

				# START DROUGHT
				if not state.active_drought_exists(event_key) and current_in_drought:
					DroughtCRUDService.create_drought(county, event_key, current_drought)
					created_count += 1
				
				# END DROUGHT
				elif previous_in_drought and not current_in_drought and state.active_drought_exists(event_key):
					DroughtCRUDService.complete_drought(event_key)
					completed_count += 1
				
				# UPDATE DROUGHT
				elif previous_in_drought and current_in_drought and state.active_drought_exists(event_key):
					# Check if severity changed - keep maximum severity
					existing_drought = state.get_drought(event_key)
					existing_severity = existing_drought.severity
					
					# Compare severities using DM integer values (higher DM = more severe)
					# Since we're in UPDATE branch, current_drought should not be None
					if current_dm is None:
						logger.warning(f"Current drought DM is None for county {county.fips} in UPDATE branch - skipping update")
						continue
					
					current_dm_level = current_dm
					existing_dm_level = SEVERITY_TO_DM.get(existing_severity, -1) if existing_severity else -1
					
					# Update to the highest severity (keep maximum)
					if current_dm_level > existing_dm_level:
						DroughtCRUDService.update_drought(existing_drought, current_severity)
						updated_count += 1
					else:
						logger.info(f"Drought event for county {county.fips} continues with same or lower severity (existing: {existing_severity}, current: {current_severity})")
				processed_counties += 1
				logger.info(f"Processed {processed_counties} / {len(counties)} counties")
			except Exception as e:
				logger.error(f"Error processing county {county.fips}: {str(e)}")
				import traceback
				logger.error(traceback.format_exc())
				continue
		
		logger.info(f"Drought sync complete: {created_count} created, {updated_count} updated, {completed_count} completed")
		return {
			"created": created_count,
			"updated": updated_count,
			"completed": completed_count,
			"total_counties": len(counties)
		}


	@staticmethod
	def check_county_in_polygons(county: County, polygons: gpd.GeoDataFrame) -> Optional[Dict]:
		# 1. Create a Point
		centroid_point = Point(county.centroid.longitude, county.centroid.latitude)
		
		# 2. CRS Safety Check (Crucial!)
		# If the user passed polygons in meters, convert them to Lat/Lon matches the point
		if polygons.crs and polygons.crs.to_epsg() != 4326:
			polygons = polygons.to_crs(epsg=4326)

		# 3. Vectorized Check (The Fast Way)
		# polygons.contains(point) returns a boolean Series for ALL rows instantly
		matches = polygons[polygons.contains(centroid_point)]

		if matches.empty:
			return None

		# 4. Get the Max Severity Row efficiently
		# We cast DM to int just to be safe, then find the row with the max value
		try:
			# Create a copy to avoid SettingWithCopy warnings on the view
			matches = matches.copy()
			matches['DM_int'] = pd.to_numeric(matches['DM'], errors='coerce').fillna(-1).astype(int)
			
			# Sort by severity descending and take the top one
			best_match_row = matches.sort_values('DM_int', ascending=False).iloc[0]
			
			dm_value = int(best_match_row['DM_int'])
			
			# Valid range check
			if dm_value < settings.drought_severity_low_threshold or dm_value > settings.drought_severity_high_threshold:
				return None

			return {
				'dm': dm_value,
				'severity': DM_TO_SEVERITY.get(dm_value, "Unknown"), # Safety .get()
				'geometry': best_match_row.geometry
			}
		except Exception as e:
			logger.error(f"Error parsing DM value for county {county.name}: {e}")
			return None

	@staticmethod
	def generate_drought_event_key(county_fips: str, state_fips: str) -> str:
		"""
		Generate a unique event key for a drought event in a county.
		Format: DRT-{county_fips}-{state_fips}
		
		Args:
			county_fips: County FIPS code
			state_fips: State FIPS code
		
		Returns:
			Event key string
		"""
		return f"DRT-{county_fips}-{state_fips}"

	
