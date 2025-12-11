"""
NWS Event Type Codes Configuration.
This module provides a flexible, extensible system for managing NWS event type codes.
"""
from typing import List, Set, Dict


# Valid event type codes for warnings (3-letter codes)
# Format: Code -> Full Name
NWS_WARNING_CODES: Dict[str, str] = {
	"BZW": "Blizzard Warning",
	"EWW": "Extreme Wind Warning",
	"CFW": "Coastal Flood Warning",
	"DSW": "Dust Storm Warning",
	"FFW": "Flash Flood Warning",
	"FLW": "Flood Warning",
	"HWW": "High Wind Warning",
	"HUW": "Hurricane Warning",
	"SVR": "Severe Thunderstorm Warning",
	"SMW": "Special Marine Warning",
	"MAW": "Special Marine Warning",
	"SSW": "Storm Surge Warning",
	"SRW": "Storm Warning",
	"TOR": "Tornado Warning",
	"TSW": "Tsunami Warning",
	"TRW": "Tropical Storm Warning",
	"WSW": "Winter Storm Warning",
	"AVW": "Avalanche Warning",
	"FRW": "Fire Warning",
	"EQW": "Earthquake Warning",
	"VOW": "Volcano Warning",
	"SQW": "Snow Squall Warning",
	"UPW": "Heavy Freezing Spray Warning",
	"FAW": "Areal Flood Warning",
	"ECW": "Extreme Cold Warning",
	"LEW": "Lake Effect Snow Warning",
	"ISW": "Ice Storm Warning"
}

# Valid event type codes for watches (3-letter codes)
NWS_WATCH_CODES: Dict[str, str] = {
	"TOA": "Tornado Watch",
	"SVA": "Severe Thunderstorm Watch",
	"FFA": "Flash Flood Watch",
	"HUA": "Hurricane Watch",
	"TRA": "Tropical Storm Watch",
	"WSA": "Winter Storm Watch",
	"BZA": "Blizzard Watch",
}

# Combined set of all valid codes
ALL_NWS_EVENT_CODES: Set[str] = set(NWS_WARNING_CODES.keys()) | set(NWS_WATCH_CODES.keys())


def is_valid_event_code(code: str) -> bool:
	"""
	Check if an event code is valid.
	
	Args:
		code: 3-letter event code
		
	Returns:
		True if valid, False otherwise
	"""
	return code.upper() in ALL_NWS_EVENT_CODES


def get_event_code_name(code: str) -> str:
	"""
	Get the full name for an event code.
	
	Args:
		code: 3-letter event code
		
	Returns:
		Full name or "Unknown" if not found
	"""
	code_upper = code.upper()
	return NWS_WARNING_CODES.get(code_upper) or NWS_WATCH_CODES.get(code_upper) or "Unknown"


def get_warning_codes() -> List[str]:
	"""Get list of all warning codes."""
	return list(NWS_WARNING_CODES.keys())


def get_watch_codes() -> List[str]:
	"""Get list of all watch codes."""
	return list(NWS_WATCH_CODES.keys())


def add_custom_event_code(code: str, name: str, is_warning: bool = True):
	"""
	Add a custom event code (for future expansion).
	
	Args:
		code: 3-letter event code
		name: Full name of the event
		is_warning: True for warning, False for watch
	"""
	code_upper = code.upper()
	if is_warning:
		NWS_WARNING_CODES[code_upper] = name
	else:
		NWS_WATCH_CODES[code_upper] = name
	ALL_NWS_EVENT_CODES.add(code_upper)

