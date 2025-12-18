"""
HTTP client for fetching wildfire data from ArcGIS API.
Uses synchronous requests since we're working with GeoJSON.
"""
import logging
import requests
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from app.config import settings

logger = logging.getLogger(__name__)


class WildfireClient:
	"""Client for fetching wildfire data from ArcGIS API."""

	@staticmethod
	def fetch_wildfires(timestamp_filter: Optional[datetime] = None) -> Dict[str, Any]:
		"""
		Fetch wildfires from ArcGIS API.
		
		Args:
			timestamp_filter: Optional datetime to filter by ModifiedOnDateTime_dt.
				If provided, will add 2-day buffer and format as TIMESTAMP.
		
		Returns:
			GeoJSON FeatureCollection with wildfire data
		"""
		# Build where clause
		where_clause = (
			"attr_IncidentComplexityLevel IN ('Type 1 Incident', 'Type 2 Incident', 'Type 3 Incident') "
			"AND attr_FireOutDateTime IS NULL "
			"AND (attr_PercentContained < 100 OR attr_PercentContained IS NULL)"
		)
		
		# Add timestamp filter if provided
		if timestamp_filter:
			# Add 2-day buffer
			buffered_timestamp = timestamp_filter - timedelta(days=2)
			# Format as TIMESTAMP 'YYYY-MM-DD HH:mm:SS' (exact format required by API)
			timestamp_str = buffered_timestamp.strftime("%Y-%m-%d %H:%M:%S")
			where_clause += f" AND attr_ModifiedOnDateTime_dt >= TIMESTAMP '{timestamp_str}'"
		
		params = {
			"outFields": "*",
			"f": "geojson",
			"returnGeometry": "true",
			"where": where_clause
		}
		
		response = requests.get(settings.wildfire_arcgis_base_url, params=params)
		response.raise_for_status()
		
		data = response.json()
		logger.info(f"Fetched {len(data.get('features', []))} potentially new wildfire features")
		return data

	@staticmethod
	def fetch_wildfires_by_object_ids(object_ids: list[int]) -> Dict[str, Any]:
		"""
		Fetch specific wildfires by their OBJECTID (arcgis_id).
		
		Args:
			object_ids: List of OBJECTID values to fetch
		
		Returns:
			GeoJSON FeatureCollection with wildfire data
		"""
		if not object_ids:
			return {"type": "FeatureCollection", "features": []}
		
		# Format object IDs as comma-separated, URL-encoded
		object_ids_str = ",".join(str(oid) for oid in object_ids)
		
		params = {
			"outFields": "*",
			"f": "geojson",
			"returnGeometry": "true",
			"objectIds": object_ids_str
		}
		
		response = requests.get(settings.wildfire_arcgis_base_url, params=params)
		response.raise_for_status()
		
		data = response.json()
		logger.info(f"Fetched {len(data.get('features', []))} out of {len(object_ids)} wildfire features by OBJECTID")
		return data
