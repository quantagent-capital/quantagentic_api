"""
Unit tests for WildfireUtils.
"""
import pytest
from app.utils.wildfire_utils import WildfireUtils


class TestMapSeverity:
	"""Test cases for WildfireUtils.map_severity."""
	
	def test_map_type_1_incident(self):
		"""Test mapping Type 1 Incident to severity 1."""
		assert WildfireUtils.map_severity("Type 1 Incident") == 1
		assert WildfireUtils.map_severity("TYPE 1 INCIDENT") == 1
		assert WildfireUtils.map_severity("  Type 1 Incident  ") == 1
	
	def test_map_type_2_incident(self):
		"""Test mapping Type 2 Incident to severity 2."""
		assert WildfireUtils.map_severity("Type 2 Incident") == 2
		assert WildfireUtils.map_severity("TYPE 2 INCIDENT") == 2
		assert WildfireUtils.map_severity("  Type 2 Incident  ") == 2
	
	def test_map_type_3_incident(self):
		"""Test mapping Type 3 Incident to severity 3."""
		assert WildfireUtils.map_severity("Type 3 Incident") == 3
		assert WildfireUtils.map_severity("TYPE 3 INCIDENT") == 3
		assert WildfireUtils.map_severity("  Type 3 Incident  ") == 3
	
	def test_map_unknown_complexity(self):
		"""Test mapping unknown complexity level defaults to 3."""
		assert WildfireUtils.map_severity("Type 4 Incident") == 3
		assert WildfireUtils.map_severity("Unknown") == 3
		assert WildfireUtils.map_severity("") == 3
	
	def test_map_none(self):
		"""Test mapping None defaults to 3."""
		assert WildfireUtils.map_severity(None) == 3


class TestBuildDescription:
	"""Test cases for WildfireUtils.build_description."""
	
	def test_build_description_with_both(self):
		"""Test building description from both name and short description."""
		result = WildfireUtils.build_description("Fire Name", "Short description")
		assert result == "Fire Name - Short description"
	
	def test_build_description_with_name_only(self):
		"""Test building description from name only."""
		result = WildfireUtils.build_description("Fire Name", None)
		assert result == "Fire Name"
	
	def test_build_description_with_short_only(self):
		"""Test building description from short description only."""
		result = WildfireUtils.build_description(None, "Short description")
		assert result == "Short description"
	
	def test_build_description_with_none(self):
		"""Test building description with both None returns None."""
		result = WildfireUtils.build_description(None, None)
		assert result is None
	
	def test_build_description_with_empty_strings(self):
		"""Test building description with empty strings returns None."""
		result = WildfireUtils.build_description("", "")
		assert result is None  # Empty strings are falsy, so parts list is empty


class TestBuildFuelSource:
	"""Test cases for WildfireUtils.build_fuel_source."""
	
	def test_build_fuel_source_with_both(self):
		"""Test building fuel source from both primary and secondary."""
		result = WildfireUtils.build_fuel_source("Primary Fuel", "Secondary Fuel")
		assert result == "Primary Fuel / Secondary Fuel"
	
	def test_build_fuel_source_with_primary_only(self):
		"""Test building fuel source from primary only."""
		result = WildfireUtils.build_fuel_source("Primary Fuel", None)
		assert result == "Primary Fuel"
	
	def test_build_fuel_source_with_secondary_only(self):
		"""Test building fuel source from secondary only."""
		result = WildfireUtils.build_fuel_source(None, "Secondary Fuel")
		assert result == "Secondary Fuel"
	
	def test_build_fuel_source_with_none(self):
		"""Test building fuel source with both None returns None."""
		result = WildfireUtils.build_fuel_source(None, None)
		assert result is None
	
	def test_build_fuel_source_with_empty_strings(self):
		"""Test building fuel source with empty strings returns None."""
		result = WildfireUtils.build_fuel_source("", "")
		assert result is None  # Empty strings are falsy, so parts list is empty
