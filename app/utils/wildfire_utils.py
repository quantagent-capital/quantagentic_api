"""
Utility functions for wildfire data processing.
"""
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class WildfireUtils:
	"""Helper class for wildfire-related utility methods."""
	
	@staticmethod
	def map_severity(complexity_level: Optional[str]) -> int:
		"""
		Map incident complexity level to severity integer.
		
		Args:
			complexity_level: String like "Type 1 Incident", "Type 2 Incident", "Type 3 Incident"
		
		Returns:
			Integer severity (1, 2, or 3), defaults to 3 if unknown
		"""
		if not complexity_level:
			return 3
		
		complexity_level = complexity_level.strip().lower()
		if "type 1" in complexity_level:
			return 1
		elif "type 2" in complexity_level:
			return 2
		elif "type 3" in complexity_level:
			return 3
		else:
			logger.warning(f"Unknown complexity level: {complexity_level}, defaulting to 3")
			return 3
	
	@staticmethod
	def build_description(incident_name: Optional[str], incident_short_description: Optional[str]) -> Optional[str]:
		"""
		Build description from incident name and short description.
		
		Args:
			incident_name: Name of the incident
			incident_short_description: Short description of the incident
		
		Returns:
			Combined description string
		"""
		parts = []
		if incident_name:
			parts.append(incident_name)
		if incident_short_description:
			parts.append(incident_short_description)
		return " - ".join(parts) if parts else None
	
	@staticmethod
	def build_fuel_source(primary_fuel: Optional[str], secondary_fuel: Optional[str]) -> Optional[str]:
		"""
		Build fuel source from primary and secondary fuel models.
		
		Args:
			primary_fuel: Primary fuel model
			secondary_fuel: Secondary fuel model
		
		Returns:
			Combined fuel source string
		"""
		parts = []
		if primary_fuel:
			parts.append(primary_fuel)
		if secondary_fuel:
			parts.append(secondary_fuel)
		return " / ".join(parts) if parts else None
