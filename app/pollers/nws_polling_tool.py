"""
Standard class for polling NWS API for active alerts.
"""
import asyncio
from typing import Any, Dict, List
from urllib.parse import urlparse
from app.schemas.location import Coordinate, Location
from app.shared_models.nws_poller_models import FilteredNWSAlert
from app.utils import vtec
from app.http_client.nws_client import NWSClient
from app.utils.event_types import ALL_NWS_EVENT_CODES
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class NWSConfirmedEventsPoller:
	"""
	Tool to poll the NWS API for active alerts.
	"""
	
	def poll(self) -> List[FilteredNWSAlert]:
		"""
		Query the NWS API active alerts endpoint.
		
		Returns:
			List of FilteredNWSAlert objects
		"""
		try:
			# Run async method
			return asyncio.run(self._async_poll())
		except Exception as e:
			raise RuntimeError(f"Error polling NWS API: {str(e)}")
	
	async def _async_poll(self) -> List[FilteredNWSAlert]:
		"""Async implementation of polling."""
		client = NWSClient()
		
		try:
			# Prepare headers
			headers = {}
			
			# Use the base client's get method with custom headers
			try:
				params = {
					"status": "actual",
					"severity": "Extreme,Severe",
					"urgency": "Immediate,Expected",
					"certainty": settings.nws_polling_certainty
				}

				data = await client.get("/alerts/active", params=params, headers=headers)
			except Exception as e:
				# Check if it's a 304 Not Modified
				if "304" in str(e) or "Not Modified" in str(e):
					return []
				raise
			
			# Filter alerts based on criteria
			alerts = []
			if "features" in data:
				for feature in data["features"]:
					properties = feature.get("properties", {})
					# Check event type - extract 3-letter code from event name
					event_name = properties.get("eventCode").get("NationalWeatherService", "")[0].upper()

					if event_name not in ALL_NWS_EVENT_CODES:
						logger.warning(f"Skipping alert {properties.get('id')} with event name {event_name} because it doesn't match our event type codes")
						continue

					message_type = vtec.get_message_type(properties)
					warning_or_watch = vtec.get_warning_or_watch(properties)

					if warning_or_watch is None:
						logger.warning(f"Skipping alert {properties.get('id')} because it doesn't match our warning or watch")
						continue

					alert_key = vtec.extract_vtec_key(properties)
					
					# Extract geometry from the feature (returns list of locations, one per SAME code)
					locations = await self._extract_location_meta(feature, alert_key, client)
					
					# Determine expected_end with fallback chain:
					# 1. Try eventEndingTime from parameters
					# 2. Fallback to ends property
					# 3. Fallback to expires property
					event_ending_time_list = properties.get("parameters", {}).get("eventEndingTime")
					if event_ending_time_list and len(event_ending_time_list) > 0:
						event_ending_time = event_ending_time_list[0]
					else:
						event_ending_time = None
					expected_end = event_ending_time or properties.get("ends") or properties.get("expires")
					
					alert = FilteredNWSAlert(
						alert_id=properties.get("id"),
						event_type=event_name,
						message_type=message_type,
						is_watch=warning_or_watch == "WATCH",
						is_warning=warning_or_watch == "WARNING",
						severity=properties.get("severity"),
						urgency=properties.get("urgency"),
						certainty=properties.get("certainty"),
						effective=properties.get("effective"),
						expires=properties.get("expires"),
						sent_at=properties.get("sent"),
						headline=properties.get("headline"),
						description=properties.get("description"), 
						key=alert_key,
						affected_zones_ugc_endpoints=properties.get("affectedZones", []),
						affected_zones_raw_ugc_codes=properties.get("geocode", {}).get("UGC", []),
						raw_vtec=properties.get("parameters", {}).get("VTEC", [""])[0],
						expected_end=expected_end,
						referenced_alerts=properties.get("references", []),
						locations=locations
						)
					alerts.append(alert)
			
			return alerts
			
		except Exception as e:
			raise RuntimeError(f"Error polling NWS API: {str(e)}")


	async def _extract_location_meta(self, feature: Dict[str, Any], alert_key: str, client: NWSClient) -> List[Location]:
		"""
		Extract location data from the NWS API response feature.
		If geometry is null, fetches geometry from each full_zone_ugc_endpoint.
		"""
		geometry = feature.get("geometry")
		properties = feature.get("properties", {})
		
		# Get SAME codes from geocode.SAME
		# SAME codes are in format 0SSCCC where SS = state fips and CCC = county fips
		same_codes = properties.get("geocode", {}).get("SAME", [])
		
		# Get UGC codes - these correspond 1:1 with SAME codes by index
		ugc_codes = properties.get("geocode", {}).get("UGC", [])
		
		# Get affected zones endpoints - these contain the full URLs for each zone
		affected_zones_ugc_endpoints = properties.get("affectedZones", [])
		
		locations = []
		
		# Create one Location object for each SAME code, paired with its corresponding UGC code
		for idx, same_code in enumerate(same_codes):
			# Get the corresponding UGC code at the same index
			ugc_code = ugc_codes[idx] if idx < len(ugc_codes) else ""
			
			# Parse SAME code: 0SSCCC where SS = state fips, CCC = county fips
			# Ignore the leading 0
			if len(same_code) >= 6:
				# Extract state_fips (positions 1-2) and county_fips (positions 3-5)
				state_fips = same_code[1:3]
				county_fips = same_code[3:6]
			else:
				# Fallback if format is unexpected
				state_fips = ""
				county_fips = ""
			
			# Find the corresponding endpoint from affectedZones that contains this UGC code
			full_zone_ugc_endpoint = None
			zone_endpoint_path = None
			
			for endpoint_url in affected_zones_ugc_endpoints:
				if ugc_code in endpoint_url:
					full_zone_ugc_endpoint = endpoint_url
					# Extract the path from the full URL
					# URLs are like "https://api.weather.gov/zones/forecast/TXC113"
					# We need just the path part: "/zones/forecast/TXC113"
					if endpoint_url.startswith("http"):
						# Parse URL to get path
						parsed = urlparse(endpoint_url)
						zone_endpoint_path = parsed.path
					else:
						# Already a path
						zone_endpoint_path = endpoint_url
					break
			
			# Fallback: if we couldn't find a matching endpoint, construct it
			if not full_zone_ugc_endpoint:
				full_zone_ugc_endpoint = f"{settings.ugc_zone_base_url}{ugc_code}"
				zone_endpoint_path = f"/zones/county/{ugc_code}"
				logger.warning(f"Could not find matching endpoint for UGC code {ugc_code}, using fallback construction")
			
			# Extract shape coordinates
			shape = []
			
			if geometry and geometry.get("type"):
				# Use geometry from the feature if available
				shape = self._extract_coordinates_from_geometry(geometry)
			else:
				# Geometry is null, fetch from the UGC endpoint
				try:
					zone_data = await client.get(zone_endpoint_path, headers={})
					zone_geometry = zone_data.get("geometry")
					if zone_geometry:
						shape = self._extract_coordinates_from_geometry(zone_geometry)
					else:
						logger.warning(f"Could not extract geometry from UGC endpoint {full_zone_ugc_endpoint}")
				except Exception as e:
					logger.warning(f"Error fetching geometry from {full_zone_ugc_endpoint}: {str(e)}")
			
			# Create Location object
			location = Location(
				episode_key=None,  # Will be set later if part of an episode
				event_key=alert_key,
				state_fips=state_fips,
				county_fips=county_fips,
				ugc_code=ugc_code,
				shape=shape,
				full_zone_ugc_endpoint=full_zone_ugc_endpoint
			)
			
			locations.append(location)
		
		return locations
	
	def _extract_coordinates_from_geometry(self, geometry: Dict[str, Any]) -> List[Coordinate]:
		"""
		Extract coordinates from a geometry object (Polygon or MultiPolygon).
		
		Args:
			geometry: Geometry object with type and coordinates
		
		Returns:
			List of Coordinate objects extracted from the geometry
		"""
		return Location.extract_coordinates_from_geometry(geometry)
