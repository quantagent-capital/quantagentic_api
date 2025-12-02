from typing import Optional, Dict, Any
from app.http_client.base_client import BaseHTTPClient
from app.config import settings

class NWSClient(BaseHTTPClient):
	"""
	National Weather Service API client.
	All requests include the required User-Agent header from settings.
	"""
	
	def __init__(self, base_url: str = "https://api.weather.gov"):
		default_headers = {
			"User-Agent": settings.nws_user_agent
		}
		super().__init__(base_url, default_headers=default_headers)
	
	async def get_active_alerts(self) -> Dict[str, Any]:
		"""
		Get active weather alerts.
		
		Returns:
			Active alerts data from NWS API
		"""
		return await self.get("/alerts/active")
	
	async def get_alert_by_id(self, alert_id: str) -> Dict[str, Any]:
		"""
		Get a specific alert by ID.
		
		Args:
			alert_id: Alert identifier
		
		Returns:
			Alert data from NWS API
		"""
		return await self.get(f"/alerts/{alert_id}")

