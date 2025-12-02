from typing import Optional
from datetime import datetime
from app.schemas.base import BaseSchema
from app.schemas.location import Location

class Event(BaseSchema):
    event_key: str
    episode_id: Optional[int] = None
    event_type: str
    location: Location
    start_date: datetime
    end_date: Optional[datetime] = None
    property_damage: Optional[int] = None
    crops_damage: Optional[int] = None
    range_miles: Optional[float] = None
    description: str
    is_active: bool = True

