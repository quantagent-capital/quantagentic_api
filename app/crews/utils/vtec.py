"""
Utilities for working with VTEC (Valid Time Event Code) from NWS alerts.
"""
from typing import Optional, Dict, Any


def extract_vtec_key(alert_properties: Dict[str, Any]) -> Optional[str]:
	"""
	Extract VTEC key from NWS alert properties.
	Format: Office + Phenomena + Significance + ETN + Year
	
	Args:
		alert_properties: Properties dictionary from NWS alert feature
		
	Returns:
		VTEC key string or None if not found
	"""
	try:
		# VTEC is typically in the parameters field
		parameters = alert_properties.get("parameters", {})
		
		# Look for VTEC in various possible locations
		vtec_strings = []
		
		# Check parameters.vtec array
		if "vtec" in parameters:
			vtec_strings.extend(parameters["vtec"])
		
		# Check if VTEC is directly in properties
		if "vtec" in alert_properties:
			if isinstance(alert_properties["vtec"], list):
				vtec_strings.extend(alert_properties["vtec"])
			else:
				vtec_strings.append(alert_properties["vtec"])
		
		# Parse first valid VTEC string
		for vtec_str in vtec_strings:
			if isinstance(vtec_str, str) and len(vtec_str) > 0:
				# VTEC format: /O.NEW.KOFF.TO.W.0015.240101T1200Z-240101T1800Z/
				# We need: Office (OFF) + Phenomena (TO) + Significance (W) + ETN (0015) + Year (24)
				parts = vtec_str.strip("/").split(".")
				if len(parts) >= 6:
					office = parts[2]  # e.g., "OFF"
					phenomena = parts[3]  # e.g., "TO"
					significance = parts[4]  # e.g., "W"
					etn = parts[5]  # e.g., "0015"
					
					# Extract year from timestamp (last part)
					timestamp = parts[6] if len(parts) > 6 else ""
					year = timestamp[:2] if len(timestamp) >= 2 else ""
					
					# Construct key: Office + Phenomena + Significance + ETN + Year
					key = f"{office}{phenomena}{significance}{etn}{year}"
					return key
		
		# Fallback: try to construct from available fields
		office = alert_properties.get("senderName", "").upper()[:3]
		event = alert_properties.get("event", "").upper()
		
		# Map event to phenomena code
		event_to_phenomena = {
			"TORNADO WARNING": "TO",
			"SEVERE THUNDERSTORM WARNING": "SV",
			"FLASH FLOOD WARNING": "FF",
			"FLOOD WARNING": "FL",
			"HURRICANE WARNING": "HU",
			"TROPICAL STORM WARNING": "TR",
			"WINTER STORM WARNING": "WS",
			"BLIZZARD WARNING": "BZ",
			"EXTREME WIND WARNING": "EW",
			"COASTAL FLOOD WARNING": "CF",
			"DUST STORM WARNING": "DS",
			"HIGH WIND WARNING": "HW",
			"SPECIAL MARINE WARNING": "SM",
			"STORM SURGE WARNING": "SS",
			"TSUNAMI WARNING": "TS",
			"AVALANCHE WARNING": "AV",
			"FIRE WARNING": "FR",
			"EARTHQUAKE WARNING": "EQ",
			"VOLCANO WARNING": "VO",
			"TORNADO WATCH": "TO",
			"SEVERE THUNDERSTORM WATCH": "SV",
			"FLOOD WATCH": "FA",
			"HURRICANE WATCH": "HU",
			"TROPICAL STORM WATCH": "TR",
			"WINTER STORM WATCH": "WS"
		}
		
		phenomena = event_to_phenomena.get(event, event[:2] if len(event) >= 2 else "XX")
		
		# Determine significance: W = Warning, A = Watch
		message_type = alert_properties.get("messageType", "").upper()
		significance = "W" if message_type == "WARNING" else "A" if message_type == "WATCH" else "X"
		
		# Try to get ETN from geocode
		geocode = alert_properties.get("geocode", {})
		etn = geocode.get("eventTrackingNumber", ["0000"])[0] if isinstance(geocode.get("eventTrackingNumber"), list) else "0000"
		
		# Get year from effective date
		effective = alert_properties.get("effective", "")
		year = effective[:2] if len(effective) >= 2 else "24"
		
		key = f"{office}{phenomena}{significance}{etn}{year}"
		return key
		
	except Exception as e:
		# If all else fails, return None
		return None


def get_message_type(alert_properties: Dict[str, Any]) -> str:
	"""
	Get message type (CON, CANCEL, EXP, NEW, etc.) from alert properties.
	
	Args:
		alert_properties: Properties dictionary from NWS alert feature
		
	Returns:
		Message type string
	"""
	# Check VTEC for message type
	parameters = alert_properties.get("parameters", {})
	if "vtec" in parameters:
		vtec_strings = parameters["vtec"]
		for vtec_str in vtec_strings:
			if isinstance(vtec_str, str):
				# VTEC format: /O.NEW.KOFF.TO.W.0015.240101T1200Z-240101T1800Z/
				parts = vtec_str.strip("/").split(".")
				if len(parts) >= 2:
					return parts[1].upper()  # NEW, CON, CANCEL, EXP, etc.
	
	return "NEW"  # Default

