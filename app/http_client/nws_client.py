from typing import Optional, Dict, Any, List
from datetime import datetime
from app.http_client.base_client import BaseHTTPClient
from app.config import settings
from app.shared_models.nws_poller_models import FilteredLSR
import logging
logger = logging.getLogger(__name__)

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
	
	async def get_lsr(self, office: str, start: datetime) -> List[FilteredLSR]:
		"""
		Get Local Storm Reports (LSR) for a specific NWS office.
		
		First makes an initial request to get a list of LSR products,
		then makes subsequent requests to each fully qualified URL to get
		the full product details including productText.
		
		Args:
			office: NWS office code (e.g., "KSBY"). The leading "K" will be stripped if present.
			start: Optional datetime to filter LSRs by start date. Will be formatted as ISO8601.
		
		Returns:
			List of FilteredLSR objects with full product details
		"""
		# Strip leading "K" if present (e.g., "KSBY" -> "SBY")
		location = office[1:]
		params = {
			"type": "LSR",
			"location": location
		}
		
		params["start"] = start.isoformat()
		
		# Initial request to get list of LSR products
		initial_response = await self.get("/products", params=params)
		
		# Extract @graph from initial response
		products = []
		if isinstance(initial_response, dict) and "@graph" in initial_response:
			products = initial_response["@graph"]
		elif isinstance(initial_response, list):
			products = initial_response
		elif isinstance(initial_response, dict):
			products = [initial_response]
		
		# Make subsequent requests to each fully qualified URL
		filtered_lsrs = []
		for product in products:
			if not isinstance(product, dict):
				continue
			
			fully_qualified_url = product.get("@id", "")
			if not fully_qualified_url:
				continue
			
			# Extract path from fully qualified URL
			# e.g., "https://api.weather.gov/products/c4fc8b83-..." -> "/products/c4fc8b83-..."
			url_path = fully_qualified_url.replace(self.base_url, "") if fully_qualified_url.startswith(self.base_url) else fully_qualified_url
			
			try:
				# Make request to get full product details
				product_response = await self.get(url_path)
				
				# Create FilteredLSR from the detailed response
				filtered_lsr = FilteredLSR(
					fully_qualified_url=fully_qualified_url,
					lsr_id=product_response.get("id", ""),
					office=product_response.get("issuingOffice", ""),
					wmo_collective=product_response.get("wmoCollectiveId", ""),
					reported_at=product_response.get("issuanceTime", ""),
					description=product_response.get("productText", "")
				)
				filtered_lsrs.append(filtered_lsr)
			except Exception as e:
				# Log error but continue with other products
				logger.warning(f"Error fetching LSR details from {fully_qualified_url}: {str(e)}")
				continue
		
		return filtered_lsrs

