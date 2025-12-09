"""
Pytest configuration and fixtures.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from app.state import State


@pytest.fixture
def mock_state():
	"""Mock state object."""
	state = Mock(spec=State)
	state.active_events = []
	state.active_episodes = []
	return state


@pytest.fixture
def mock_nws_client():
	"""Mock NWS client."""
	client = AsyncMock()
	client.get = AsyncMock()
	client.close = AsyncMock()
	return client


@pytest.fixture
def sample_nws_alert():
	"""Sample NWS alert data."""
	return {
		"id": "https://api.weather.gov/alerts/urn:oid:2.49.0.1.840.0.1234567890",
		"type": "Feature",
		"properties": {
			"@id": "https://api.weather.gov/alerts/urn:oid:2.49.0.1.840.0.1234567890",
			"@type": "wx:Alert",
			"id": "urn:oid:2.49.0.1.840.0.1234567890",
			"areaDesc": "Test County, TX",
			"geocode": {
				"SAME": ["048113"],
				"UGC": ["TXC113"],
				"eventTrackingNumber": ["0015"]
			},
			"affectedZones": [
				"https://api.weather.gov/zones/forecast/TXC113"
			],
			"references": [],
			"sent": "2024-01-15T10:30:00-06:00",
			"effective": "2024-01-15T10:30:00-06:00",
			"onset": "2024-01-15T10:30:00-06:00",
			"expires": "2024-01-15T18:00:00-06:00",
			"ends": None,
			"status": "Actual",
			"messageType": "Alert",
			"category": "Met",
			"severity": "Extreme",
			"certainty": "Observed",
			"urgency": "Immediate",
			"event": "Tornado Warning",
			"sender": "w-nws.webmaster@noaa.gov",
			"senderName": "NWS Fort Worth",
			"headline": "Tornado Warning issued January 15 at 10:30AM CST",
			"description": "Test tornado warning description",
			"instruction": "Take shelter immediately",
			"response": "Shelter",
			"parameters": {
				"AWIPSidentifier": ["TO.W"],
				"WMOidentifier": ["WWUS54 KFWD 151630"],
				"VTEC": ["/O.NEW.KFWD.TO.W.0015.240115T1630Z-240115T2400Z/"]
			}
		},
		"geometry": {
			"type": "Polygon",
			"coordinates": [[
				[-97.5, 32.8],
				[-97.2, 32.8],
				[-97.2, 33.1],
				[-97.5, 33.1],
				[-97.5, 32.8]
			]]
		}
	}

