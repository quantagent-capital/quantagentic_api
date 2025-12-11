from datetime import datetime, timezone
from typing import Optional, Dict, Any
from app.utils.datetime_utils import parse_datetime_to_utc
from app.http_client.nws_client import NWSClient
import logging

logger = logging.getLogger(__name__)


class NWSAlertParser:
	"""Utility class for parsing NWS alert data."""

	@staticmethod
	def extract_properties_from_alert(alert_data: Dict[str, Any], alert_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
		"""
		Extract properties from NWS alert response data.
		
		Handles different response formats:
		- Response with "features" array (GeoJSON FeatureCollection)
		- Response with direct "properties" (single alert)
		
		Args:
			alert_data: Alert data dictionary from NWS API
			alert_id: Optional alert ID for logging purposes
		
		Returns:
			Properties dictionary or None if not found
		"""
		# Check if this is a feature collection (features array)
		if "features" in alert_data and len(alert_data["features"]) > 0:
			feature = alert_data["features"][0]
			properties = feature.get("properties", {})
			return properties if properties else None
		
		# Check if properties are directly in the response
		elif "properties" in alert_data:
			properties = alert_data["properties"]
			return properties if properties else None
		
		# Properties not found
		else:
			alert_id_str = f" {alert_id}" if alert_id else ""
			logger.warning(f"Could not find properties in alert{alert_id_str}")
			return None

	@staticmethod
	async def get_most_recent_alert(client: NWSClient, alert_id: str) -> Optional[Dict[str, Any]]:
		"""
		Get the most recent alert by following replacedBy links.
		
		Args:
			client: NWSClient instance
			alert_id: Initial alert ID
		
		Returns:
			Most recent alert data or None if not found
		"""
		try:
			current_alert_id = alert_id
			max_iterations = 10  # Prevent infinite loops
			iteration = 0
			
			while iteration < max_iterations:
				# Get alert by ID
				alert_data = await client.get_alert_by_id(current_alert_id)
				
				# Extract properties from alert response
				properties = NWSAlertParser.extract_properties_from_alert(alert_data, current_alert_id)
				if properties is None:
					logger.warning(f"Unexpected alert structure for {current_alert_id}")
					return alert_data
				
				# Check for replacedBy property
				replaced_by = properties.get("replacedBy")
				if not replaced_by:
					# This is the most recent alert
					return alert_data
				
				# Extract alert ID from the replacedBy URL
				# Format: https://api.weather.gov/alerts/{alert_id}
				if isinstance(replaced_by, str):
					# Extract the alert ID from the URL
					if "/alerts/" in replaced_by:
						# Get everything after "/alerts/" and before any query params or fragments
						alert_id_part = replaced_by.split("/alerts/")[-1]
						# Remove query parameters and fragments if present
						current_alert_id = alert_id_part.split("?")[0].split("#")[0]
					else:
						logger.warning(f"Unexpected replacedBy format: {replaced_by}")
						return alert_data
				else:
					logger.warning(f"replacedBy is not a string: {replaced_by}")
					return alert_data
				
				iteration += 1
			
			logger.warning(f"Reached max iterations following replacedBy links for {alert_id}")
			return alert_data
			
		except Exception as e:
			logger.error(f"Error getting most recent alert for {alert_id}: {str(e)}")
			import traceback
			logger.error(traceback.format_exc())
			return None

	@staticmethod
	def extract_actual_end_time(alert_data: Dict[str, Any]) -> datetime:
		"""
		Extract actual end time from alert data with fallback chain:
		1. Try eventEndingTime from parameters
		2. Fallback to ends property
		3. Fallback to expires property
		4. Fallback to datetime.utcnow
		
		Args:
			alert_data: Alert data dictionary from NWS API
		
		Returns:
			datetime object in UTC
		"""
		try:
			# Get properties from alert data
			properties = NWSAlertParser.extract_properties_from_alert(alert_data)
			if properties is None:
				logger.warning("Could not find properties in alert data")
				return datetime.now(timezone.utc)
			
			# Try eventEndingTime from parameters
			event_ending_time_list = properties.get("parameters", {}).get("eventEndingTime")
			if event_ending_time_list and len(event_ending_time_list) > 0:
				event_ending_time = parse_datetime_to_utc(event_ending_time_list[0])
				if event_ending_time:
					return event_ending_time
			
			# Fallback to ends property
			ends = properties.get("ends")
			if ends:
				ends_dt = parse_datetime_to_utc(ends)
				if ends_dt:
					return ends_dt
			
			# Fallback to expires property
			expires = properties.get("expires")
			if expires:
				expires_dt = parse_datetime_to_utc(expires)
				if expires_dt:
					return expires_dt
			
			# Final fallback to current time
			return datetime.now(timezone.utc)
			
		except Exception as e:
			logger.error(f"Error extracting actual end time: {str(e)}")
			import traceback
			logger.error(traceback.format_exc())
			return datetime.now(timezone.utc)
