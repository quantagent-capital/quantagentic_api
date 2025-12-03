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
		vtec_string = parameters.get("VTEC", [""])[0]
		
		# Parse first valid VTEC string
		parts = vtec_string.strip("/").split(".")
		if len(parts) >= 6:
			office = parts[2]  # e.g., "OFF"
			phenomena = parts[3]  # e.g., "TO"
			etn = parts[5]  # e.g., "0015"
			year = parts[6][:2]  # e.g., "24"
		
		significance = get_warning_or_watch(alert_properties)  # e.g., "W"
	
		return f"{office}-{phenomena}-{significance}-{etn}-{year}"
	except ValueError as e:
		raise ValueError(f"Error extracting VTEC key from alert properties: {e}")

# Get whether it is a warning or watch
def get_warning_or_watch(alert_properties: Dict[str, Any]) -> bool:
	"""
	Get whether it is a warning or watch from alert properties.
	
	Args:
		alert_properties: Properties dictionary from NWS alert feature
		
	Returns:
		True if warning, False if watch
	"""
	# Check VTEC for message type
	parameters = alert_properties.get("parameters", {})
	if "VTEC" in parameters:
		vtec_string = parameters["VTEC"][0]
		parts = vtec_string.strip("/").split(".")
		if len(parts) >= 2:
			message_type = parts[4].upper()
			if message_type == "W":
				return "WARNING"
			elif message_type == "A":
				return "WATCH"
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
		vtec_string = parameters["vtec"][0]
		parts = vtec_string.strip("/").split(".")
		if len(parts) >= 2:
			return parts[1].upper()  # NEW, CON, CANCEL, EXP, etc.
	
	return "NEW"  # Default

