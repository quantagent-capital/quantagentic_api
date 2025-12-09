from typing import Optional, List
from datetime import datetime
from app.schemas.base import BaseSchema
from app.schemas.location import Location

class Event(BaseSchema):
    event_key: str
    nws_alert_id: str
    episode_key: Optional[str] = None
    event_type: str
    hr_event_type: Optional[str] = None
    locations: List[Location] = []
    start_date: datetime
    expected_end_date: Optional[datetime] = None
    actual_end_date: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    property_damage: Optional[int] = None
    crops_damage: Optional[int] = None
    range_miles: Optional[float] = None
    description: str
    is_active: bool = True
    raw_vtec: str
    previous_ids: List[str] = []