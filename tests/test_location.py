"""
Unit tests for Location schema methods.
"""
import pytest
from app.schemas.location import Location, Coordinate


class TestParseFips:
	"""Test cases for Location.parse_fips."""
	
	def test_parse_full_fips(self):
		"""Test parsing a full FIPS code."""
		state_fips, county_fips = Location.parse_fips("01012")
		assert state_fips == "01"
		assert county_fips == "012"
	
	def test_parse_fips_with_leading_zero(self):
		"""Test parsing FIPS code with leading zeros."""
		state_fips, county_fips = Location.parse_fips("35033")
		assert state_fips == "35"
		assert county_fips == "033"
	
	def test_parse_fips_short(self):
		"""Test parsing a short FIPS code (only state)."""
		state_fips, county_fips = Location.parse_fips("01")
		assert state_fips == "01"
		assert county_fips == "UNKNOWN"
	
	def test_parse_fips_none(self):
		"""Test parsing None FIPS code."""
		state_fips, county_fips = Location.parse_fips(None)
		assert state_fips == "UNKNOWN"
		assert county_fips == "UNKNOWN"
	
	def test_parse_fips_empty_string(self):
		"""Test parsing empty string FIPS code."""
		state_fips, county_fips = Location.parse_fips("")
		assert state_fips == "UNKNOWN"
		assert county_fips == "UNKNOWN"
	
	def test_parse_fips_single_char(self):
		"""Test parsing single character FIPS code."""
		state_fips, county_fips = Location.parse_fips("0")
		assert state_fips == "UNKNOWN"
		assert county_fips == "UNKNOWN"


class TestExtractCoordinatesFromGeometry:
	"""Test cases for Location.extract_coordinates_from_geometry."""
	
	def test_extract_polygon_coordinates(self):
		"""Test extracting coordinates from Polygon geometry."""
		geometry = {
			"type": "Polygon",
			"coordinates": [[
				[-97.5, 32.8],
				[-97.2, 32.8],
				[-97.2, 33.1],
				[-97.5, 33.1],
				[-97.5, 32.8]
			]]
		}
		result = Location.extract_coordinates_from_geometry(geometry)
		
		assert len(result) == 5
		assert isinstance(result[0], Coordinate)
		assert result[0].latitude == 32.8
		assert result[0].longitude == -97.5
		assert result[1].latitude == 32.8
		assert result[1].longitude == -97.2
	
	def test_extract_multipolygon_coordinates(self):
		"""Test extracting coordinates from MultiPolygon geometry."""
		geometry = {
			"type": "MultiPolygon",
			"coordinates": [[[
				[-97.5, 32.8],
				[-97.2, 32.8],
				[-97.2, 33.1],
				[-97.5, 33.1],
				[-97.5, 32.8]
			]]]
		}
		result = Location.extract_coordinates_from_geometry(geometry)
		
		assert len(result) == 5
		assert isinstance(result[0], Coordinate)
		assert result[0].latitude == 32.8
		assert result[0].longitude == -97.5
	
	def test_extract_empty_coordinates(self):
		"""Test extracting coordinates from empty geometry."""
		geometry = {
			"type": "Polygon",
			"coordinates": []
		}
		result = Location.extract_coordinates_from_geometry(geometry)
		assert result == []
	
	def test_extract_no_coordinates_key(self):
		"""Test extracting coordinates when coordinates key is missing."""
		geometry = {
			"type": "Polygon"
		}
		result = Location.extract_coordinates_from_geometry(geometry)
		assert result == []
	
	def test_extract_invalid_coordinate_pair(self):
		"""Test extracting coordinates with invalid coordinate pairs."""
		geometry = {
			"type": "Polygon",
			"coordinates": [[
				[-97.5, 32.8],
				[-97.2],  # Invalid - only one value
				[-97.2, 33.1]
			]]
		}
		result = Location.extract_coordinates_from_geometry(geometry)
		# Should only extract valid pairs
		assert len(result) == 2
		assert result[0].latitude == 32.8
		assert result[0].longitude == -97.5


class TestGetStateFips:
	"""Test cases for Location.get_state_fips."""
	
	def test_get_state_fips_valid(self):
		"""Test getting FIPS code for valid state abbreviations."""
		assert Location.get_state_fips("TX") == "48"
		assert Location.get_state_fips("CA") == "06"
		assert Location.get_state_fips("NY") == "36"
	
	def test_get_state_fips_case_insensitive(self):
		"""Test that state abbreviation is case insensitive."""
		assert Location.get_state_fips("tx") == "48"
		assert Location.get_state_fips("Tx") == "48"
		assert Location.get_state_fips("TX") == "48"
	
	def test_get_state_fips_with_whitespace(self):
		"""Test that whitespace is stripped."""
		assert Location.get_state_fips("  TX  ") == "48"
		assert Location.get_state_fips(" TX ") == "48"
	
	def test_get_state_fips_invalid(self):
		"""Test getting FIPS code for invalid state abbreviation."""
		assert Location.get_state_fips("XX") == "UNKNOWN"
		assert Location.get_state_fips("INVALID") == "UNKNOWN"
	
	def test_get_state_fips_all_states(self):
		"""Test a few more states to ensure mapping works."""
		assert Location.get_state_fips("AL") == "01"
		assert Location.get_state_fips("AK") == "02"
		assert Location.get_state_fips("FL") == "12"
		assert Location.get_state_fips("PR") == "72"
