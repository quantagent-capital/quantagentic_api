"""
Custom CrewAI tool for polling NWS API for active alerts.
"""
import asyncio
import json
from datetime import datetime
from crewai.tools import BaseTool
from app.crews.disaster_polling_agent.models import FilteredNWSAlert
from app.crews.utils import vtec
from app.http_client.nws_client import NWSClient
from app.state import state
from app.crews.utils.nws_event_types import ALL_NWS_EVENT_CODES

class NWSPollingTool(BaseTool):
	"""
	Tool to poll the NWS API for active alerts.
	"""
	name: str = "NWSPollingTool"
	description: str = (
		"Use this tool to query the NWS API active alerts endpoint. "
		"Returns active weather warnings and watches. "
	)
	
	def _run(
		self,
	) -> str:
		"""
		Query the NWS API active alerts endpoint.
		
		Returns:
			JSON string of filtered alerts
		"""
		try:
			# Run async method
			return asyncio.run(self._async_poll())
		except Exception as e:
			return f"Error polling NWS API: {str(e)}"
	
	async def _async_poll(self) -> str:
		"""Async implementation of polling."""
		client = NWSClient()
		
		try:
			# Prepare headers
			headers = {}
			if state.last_disaster_poll_time:
				# Format datetime for If-Modified-Since header (RFC 7231 format)
				last_poll = state.last_disaster_poll_time
				headers["If-Modified-Since"] = last_poll.strftime("%a, %d %b %Y %H:%M:%S GMT")
			
			# Use the base client's get method with custom headers
			try:
				params = {
					"status": "actual",
					"severity": "Extreme,Severe",
					"urgency": "Immediate,Expected",
					"certainty": "Observed,Likely"
				}

				data = await client.get("/alerts/active", params=params, headers=headers)
			except Exception as e:
				# Check if it's a 304 Not Modified
				if "304" in str(e) or "Not Modified" in str(e):
					return '{"features": [], "message": "No new alerts since last poll"}'
				raise
			
			# Filter alerts based on criteria
			alerts = []
			if "features" in data:
				for feature in data["features"]:
					properties = feature.get("properties", {})
					# Check event type - extract 3-letter code from event name
					event_name = properties.get("eventCode").get("NationalWeatherService", "")[0].upper()

					if event_name not in ALL_NWS_EVENT_CODES:
						continue

					# Check if it's a watch or warning
					message_type = vtec.get_message_type(properties)
					warning_or_watch = vtec.get_warning_or_watch(properties)

					if warning_or_watch is None:
						continue

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
						headline=properties.get("headline"),
						description=properties.get("description"), 
						key=vtec.extract_vtec_key(properties),
						affected_zones_ugc_endpoints=properties.get("affectedZones", []),
						affected_zones_raw_ugc_codes=properties.get("geocode", {}).get("UGC", []),
						raw_vtec=properties.get("parameters", {}).get("VTEC", [""])[0],
						expected_end=properties.get("parameters", {}).get("eventEndingTime", None)[0],
						referenced_alerts=properties.get("references", [])
						)
					alerts.append(alert)
			
			alerts_json = [alert.model_dump() for alert in alerts]
			result = {
				"filtered_alerts": alerts_json,
				"total_count": len(alerts_json)
			}
			
			return json.dumps(result, indent=2)
			
		except Exception as e:
			return f"Error: {str(e)}"

