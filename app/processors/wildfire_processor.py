from typing import Dict
from datetime import datetime, timezone, timedelta
from app.state import state
from app.http_client.wildfire_client import WildfireClient
from app.services.wildfire_crud_service import WildfireCRUDService
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class WildfireProcessor:
	"""Processor for wildfire data synchronization and event management."""
	
	@staticmethod
	def sync_wildfire_data() -> Dict[str, int]:
		"""
		Sync wildfire data by polling ArcGIS API.
		Creates, updates, or completes wildfire events based on API responses.
		
		Returns:
			Dictionary with counts of created, updated, and completed events
		"""
		logger.info("Starting wildfire data sync")
		
		# Get last poll date (with 2-day buffer for initial query)
		last_poll_date = state.get_wildfire_last_poll_date()
		if last_poll_date:
			# Add 2-day buffer as specified
			timestamp_filter = last_poll_date - timedelta(days=2)
		else:
			# First time polling, use two days ago
			timestamp_filter = datetime.now(timezone.utc) - timedelta(days=2)
		
		# Step 1: Poll for new wildfires
		created_count, new_event_keys = WildfireProcessor._process_new_wildfires(timestamp_filter)
		logger.info(f"Created {created_count} new wildfires")

		# Step 2 & 3: Poll for updates and determine active status for existing wildfires
		updated_count, completed_count = WildfireProcessor._process_wildfire_updates_and_completion(new_event_keys)
		logger.info(f"Updated {updated_count} wildfires and completed {completed_count} wildfires")

		# Update last poll date
		state.set_wildfire_last_poll_date(datetime.now(timezone.utc))
		logger.info(f"Total wildfire sync complete: {created_count} created, {updated_count} updated, {completed_count} completed")
		return {
			"created": created_count,
			"updated": updated_count,
			"completed": completed_count
		}
	
	@staticmethod
	def _process_new_wildfires(timestamp_filter: datetime) -> tuple[int, set]:
		"""
		Step 1: Poll for new wildfires and create them.
		
		Args:
			timestamp_filter: datetime to filter by ModifiedOnDateTime_dt
		
		Returns:
			Tuple of (created_count, new_event_keys set)
		"""
		logger.info("Step 1: Polling for new wildfires...")
		new_features = WildfireProcessor._poll_for_new_wildfires(timestamp_filter)
		created_count = 0
		
		# Get existing event keys (only active wildfires)
		existing_wildfires = state.active_wildfires
		existing_event_keys = {wf.event_key for wf in existing_wildfires}
		
		# Process new wildfires
		new_event_keys = set()
		for feature in new_features:
			event_key = feature.get("properties", {}).get("attr_UniqueFireIdentifier", "")
			if event_key and event_key not in existing_event_keys:
				try:
					WildfireCRUDService.create_wildfire(feature)
					new_event_keys.add(event_key)
					created_count += 1
					logger.info(f"Created new wildfire: {event_key}")
				except Exception as e:
					logger.error(f"Error creating wildfire {event_key}: {str(e)}")
					import traceback
					logger.error(traceback.format_exc())
		
		return created_count, new_event_keys
	
	@staticmethod
	def _process_wildfire_updates_and_completion(new_event_keys: set) -> tuple[int, int]:
		"""
		Step 2 & 3: Poll for updates and determine active status for existing active wildfires.
		Combines both operations to avoid duplicate API calls.
		
		Args:
			new_event_keys: Set of event keys that were just created (to skip)
		
		Returns:
			Tuple of (updated_count, completed_count)
		"""
		logger.info("Step 2 & 3: Polling for updates and determining active status for active wildfires...")
		updated_count = 0
		completed_count = 0
		
		# Get all active wildfires to check for updates and completion
		all_active_wildfires = state.active_wildfires
		
		# Get arcgis_ids for all active wildfires
		all_arcgis_ids = [int(wf.arcgis_id) for wf in all_active_wildfires]
		
		if not all_arcgis_ids:
			return updated_count, completed_count
		
		try:
			# Fetch updates and status for all active wildfires in one API call
			update_features_dict = WildfireProcessor._poll_for_wildfires_updates(all_arcgis_ids)
			
			# Calculate staleness threshold from config
			current_time_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
			staleness_threshold = current_time_ms - settings.wildfire_staleness_threshold_ms
			
			for wildfire in all_active_wildfires:
				feature = update_features_dict.get(wildfire.arcgis_id)
				
				if not feature:
					# Fire not found in API response - skip processing
					logger.warning(f"Wildfire event key {wildfire.event_key} not found in API response, skipping")
					continue
				
				properties = feature.get("properties", {})
				event_key = properties.get("attr_UniqueFireIdentifier", "")
				
				# Skip if this is a newly created wildfire (already processed in Step 1)
				if wildfire.event_key in new_event_keys:
					continue
				
				# Update the wildfire with new data
				try:
					updated_wildfire = WildfireCRUDService.update_wildfire(wildfire, feature)
					updated_count += 1
					logger.info(f"Updated wildfire: {event_key}")
				except Exception as e:
					logger.error(f"Error updating wildfire {event_key}: {str(e)}")
					import traceback
					logger.error(traceback.format_exc())
					continue
				
				# Apply 3-tiered logic for active status (completion logic)
				# A. Not officially out
				fire_out_datetime = properties.get("attr_FireOutDateTime")
				is_not_out = fire_out_datetime is None
				
				# B. Not 100% Contained (Handle NULLs as active/0%)
				percent_contained = properties.get("attr_PercentContained")
				is_not_fully_contained = (percent_contained is None or percent_contained < 100)
				
				# C. Data is fresh (Modified within last 14 days)
				modified_timestamp_ms = properties.get("attr_ModifiedOnDateTime_dt")
				is_fresh = modified_timestamp_ms is not None and modified_timestamp_ms >= staleness_threshold
				
				# Determine if should be active
				should_be_active = is_not_out and is_not_fully_contained and is_fresh
				
				# Update active status if changed (only deactivate, never reactivate)
				# Use updated_wildfire to check current active status
				if updated_wildfire.active and not should_be_active:
					# Deactivate
					logger.info(f"Deactivating wildfire {updated_wildfire.event_key}")
					WildfireCRUDService.complete_wildfire(wildfire.event_key)
					completed_count += 1
		except Exception as e:
			logger.error(f"Error processing wildfire updates and completion: {str(e)}")
			import traceback
			logger.error(traceback.format_exc())
		
		return updated_count, completed_count
	
	@staticmethod
	def _poll_for_new_wildfires(timestamp_filter: datetime) -> list:
		"""
		Poll ArcGIS API for new wildfires.
		
		Args:
			timestamp_filter: datetime to filter by ModifiedOnDateTime_dt
		
		Returns:
			List of GeoJSON features
		"""
		try:
			response = WildfireClient.fetch_wildfires(timestamp_filter)
			return response.get("features", [])
		except Exception as e:
			logger.error(f"Error polling for new wildfires: {str(e)}")
			raise
	
	@staticmethod
	def _poll_for_wildfires_updates(object_ids: list[int]) -> Dict[str, Dict]:
		"""
		Poll ArcGIS API for wildfire updates by object IDs.
		
		Args:
			object_ids: List of OBJECTID values to fetch
		
		Returns:
			Dictionary mapping arcgis_id (as string) to feature dictionary
		"""
		try:
			response = WildfireClient.fetch_wildfires_by_object_ids(object_ids)
			features = response.get("features", [])
			# Create a dictionary mapping arcgis_id to feature
			return {
				str(f.get("properties", {}).get("OBJECTID", "")): f 
				for f in features
			}
		except Exception as e:
			logger.error(f"Error polling for wildfire updates: {str(e)}")
			raise
