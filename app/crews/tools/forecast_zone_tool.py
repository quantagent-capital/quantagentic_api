"""
Custom CrewAI tool for getting forecast zone polygon data from NWS API.
"""
import asyncio
from typing import Type, List
from pydantic import BaseModel, Field
from crewai.tools import BaseTool
from app.http_client.nws_client import NWSClient


class GetForecastZoneInput(BaseModel):
	"""Input schema for forecast zone tool."""
	zone_url: str = Field(
		description="Full URL of the forecast zone (e.g., https://api.weather.gov/zones/forecast/PKZ413)"
	)


class GetForecastZoneTool(BaseTool):
	"""
	Tool to get forecast zone polygon coordinates from NWS API.
	Used for mapping affected areas and determining event-episode relationships.
	"""
	name: str = "GetForecastZoneTool"
	description: str = (
		"Use this tool to get forecast zone polygon coordinates from the NWS API. "
		"Takes a zone URL from geocode.affected_zones and returns the polygon coordinates. "
		"Use this to map affected areas and compare with existing episode/event locations."
	)
	args_schema: Type[BaseModel] = GetForecastZoneInput
	
	def _run(self, zone_url: str) -> str:
		"""
		Get forecast zone polygon data.
		
		Args:
			zone_url: Full URL of the forecast zone
		
		Returns:
			JSON string with zone polygon coordinates
		"""
		try:
			return asyncio.run(self._async_get_zone(zone_url))
		except Exception as e:
			return f"Error getting forecast zone: {str(e)}"
	
	async def _async_get_zone(self, zone_url: str) -> str:
		"""Async implementation of getting zone data."""
		client = NWSClient()
		
		try:
			# Extract path from full URL
			if zone_url.startswith("http"):
				# Extract path from URL
				from urllib.parse import urlparse
				parsed = urlparse(zone_url)
				path = parsed.path
			else:
				path = zone_url
			
			# Use base client's get method
			data = await client.get(path)
			
			# Extract polygon coordinates
			geometry = data.get("geometry", {})
			coordinates = geometry.get("coordinates", [])
			properties = data.get("properties", {})
			
			result = {
				"zone_id": properties.get("id", ""),
				"zone_name": properties.get("name", ""),
				"coordinates": coordinates,
				"geometry_type": geometry.get("type", ""),
				"full_data": data
			}
			
			return str(result)
			
		except Exception as e:
			return f"Error: {str(e)}"

