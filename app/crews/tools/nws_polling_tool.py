"""
Custom CrewAI tool for polling NWS API for active alerts.
"""
import asyncio
from typing import Type, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from crewai.tools import BaseTool
from app.http_client.nws_client import NWSClient
from app.state import state
from app.crews.utils.nws_event_types import ALL_NWS_EVENT_CODES


class NWSPollingInput(BaseModel):
	"""Input schema for NWS polling tool."""
	use_last_poll_time: bool = Field(
		default=True,
		description="Whether to use the last disaster poll time from state"
	)


class NWSPollingTool(BaseTool):
	"""
	Tool to poll the NWS API for active alerts.
	Uses If-Modified-Since header if last poll time is available.
	"""
	name: str = "NWSPollingTool"
	description: str = (
		"Use this tool to query the NWS API active alerts endpoint. "
		"Returns active weather warnings and watches. "
		"If last poll time is available, uses If-Modified-Since header to get only new alerts. "
		"Filters results by severity (Extreme/Severe), urgency (Immediate/Expected), "
		"certainty (Observed/Likely), and status (actual)."
	)
	args_schema: Type[BaseModel] = NWSPollingInput
	
	def _run(
		self,
		use_last_poll_time: bool = True
	) -> str:
		"""
		Query the NWS API active alerts endpoint.
		
		Args:
			use_last_poll_time: Whether to use If-Modified-Since header
		
		Returns:
			JSON string of filtered alerts
		"""
		try:
			# Run async method
			return asyncio.run(self._async_poll(use_last_poll_time))
		except Exception as e:
			return f"Error polling NWS API: {str(e)}"
	
	async def _async_poll(self, use_last_poll_time: bool) -> str:
		"""Async implementation of polling."""
		client = NWSClient()
		
		try:
			# Prepare headers
			headers = {}
			if use_last_poll_time and state.last_disaster_poll_time:
				# Format datetime for If-Modified-Since header (RFC 7231 format)
				last_poll = state.last_disaster_poll_time
				headers["If-Modified-Since"] = last_poll.strftime("%a, %d %b %Y %H:%M:%S GMT")
			
			# Use the base client's get method with custom headers
			try:
				data = await client.get("/alerts/active", headers=headers)
			except Exception as e:
				# Check if it's a 304 Not Modified
				if "304" in str(e) or "Not Modified" in str(e):
					return '{"features": [], "message": "No new alerts since last poll"}'
				raise
			
			# Filter alerts based on criteria
			filtered_features = []
			if "features" in data:
				for feature in data["features"]:
					properties = feature.get("properties", {})
					
					# Check filters
					severity = properties.get("severity", "").lower()
					urgency = properties.get("urgency", "").lower()
					certainty = properties.get("certainty", "").lower()
					status = properties.get("status", "").lower()
					
					# Filter criteria
					severity_ok = severity in ["extreme", "severe"]
					urgency_ok = urgency in ["immediate", "expected"]
					certainty_ok = certainty in ["observed", "likely"]
					status_ok = status == "actual"
					
					if severity_ok and urgency_ok and certainty_ok and status_ok:
						# Check event type - extract 3-letter code from event name
						event_name = properties.get("event", "").upper()
						# Event names are like "Tornado Warning" or "TOR" - extract code
						# Try to find 3-letter code in the event name or use first 3 letters
						event_code = None
						
						# Check if event name contains a known code
						for code in ALL_NWS_EVENT_CODES:
							if code in event_name or event_name.startswith(code[:2]):
								event_code = code
								break
						
						# If no code found, try to extract from event name
						if not event_code:
							# Some events might be abbreviated (e.g., "TOR" for Tornado)
							words = event_name.split()
							for word in words:
								if len(word) == 3 and word.isalpha():
									event_code = word
									break
						
						# Check if it's a watch or warning
						msg_type = properties.get("messageType", "").upper()
						if msg_type in ["WARNING", "WATCH"]:
							# If we have a valid code or can't determine, include it
							# The flexible system allows for future codes
							if event_code in ALL_NWS_EVENT_CODES or event_code is None:
								filtered_features.append(feature)
			
			# Return filtered results
			result = {
				"features": filtered_features,
				"total_filtered": len(filtered_features),
				"timestamp": datetime.utcnow().isoformat()
			}
			
			return str(result)
			
		except Exception as e:
			return f"Error: {str(e)}"

