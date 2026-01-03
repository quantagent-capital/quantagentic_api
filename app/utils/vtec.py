"""
Utilities for working with VTEC (Valid Time Event Code) from NWS alerts.
"""
from typing import Optional, Dict, Any
from datetime import datetime, timezone


def extract_office_from_vtec(vtec_string: str) -> Optional[str]:
	"""
	Extract office code from a VTEC string.
	
	Args:
		vtec_string: Raw VTEC string (e.g., "/O.NEW.KSBY.TO.W.0015.251212T2203Z-251212T2300Z/")
		
	Returns:
		Office code string (e.g., "KSBY") or None if not found
	"""
	try:
		parts = vtec_string.strip("/").split(".")
		if len(parts) >= 3:
			return parts[2]  # e.g., "KSBY"
		return None
	except (ValueError, IndexError):
		return None


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
			
			# Extract year from date range in parts[6]
			# Format: YYMMDDTHHmmZ-YYMMDDTHHmmZ or just YYMMDDTHHmmZ
			date_range = parts[6]
			year = _extract_year_from_vtec_date(date_range)
		else:
			raise ValueError("VTEC string does not have enough parts")
		
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
	if "VTEC" in parameters:
		vtec_string = parameters["VTEC"][0]
		parts = vtec_string.strip("/").split(".")
		if len(parts) >= 2:
			return parts[1].upper()  # NEW, CON, CANCEL, EXP, etc.
	
	return "NEW"  # Default


def _extract_year_from_vtec_date(date_range: str) -> str:
	"""
	Extract year from VTEC date range string.
	
	Format: YYMMDDTHHmmZ-YYMMDDTHHmmZ or YYMMDDTHHmmZ
	If first date is all zeros, use second date.
	If neither are valid, use current UTC year.
	
	Args:
		date_range: Date range string from VTEC (e.g., "000000T0000Z-251212T2203Z")
		
	Returns:
		Two-digit year string (e.g., "25")
	"""
	# Split by '-' to get start and end dates
	if "-" in date_range:
		start_date_str, end_date_str = date_range.split("-", 1)
	else:
		# Single date format
		start_date_str = date_range
		end_date_str = None
	
	# Check if first date is valid (not all zeros)
	# Format: YYMMDDTHHmmZ, we need first 2 digits for year
	if len(start_date_str) >= 2:
		start_year = start_date_str[:2]
		# Check if it's all zeros or invalid
		if start_year != "00" and start_year.isdigit():
			return start_year  # Return 2-digit year
	
	# First date invalid, try second date
	if end_date_str and len(end_date_str) >= 2:
		end_year = end_date_str[:2]
		if end_year != "00" and end_year.isdigit():
			return end_year  # Return 2-digit year
	
	# Neither date valid, use current UTC year
	current_year = datetime.now(timezone.utc).year
	return str(current_year)[-2:]

