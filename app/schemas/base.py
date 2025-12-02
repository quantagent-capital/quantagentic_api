from typing import Any, Dict
import json
import pandas as pd
from datetime import datetime
from pydantic import BaseModel, ConfigDict, field_serializer

class BaseSchema(BaseModel):
	"""
	Base schema class with robust serialization/deserialization
	that handles advanced types like pandas DataFrames and datetime objects.
	"""
	
	model_config = ConfigDict(arbitrary_types_allowed=True)
	
	def to_dict(self) -> Dict[str, Any]:
		"""Convert model to dictionary with proper serialization."""
		return json.loads(self.model_dump_json())
	
	@classmethod
	def from_dict(cls, data: Dict[str, Any]) -> "BaseSchema":
		"""Create model instance from dictionary with proper deserialization."""
		# Handle datetime strings
		for key, value in data.items():
			if isinstance(value, str):
				# Try to parse as datetime
				try:
					data[key] = datetime.fromisoformat(value.replace('Z', '+00:00'))
				except (ValueError, AttributeError):
					pass
		
		# Handle pandas DataFrame reconstruction if needed
		# (This would be handled by specific schema classes if needed)
		
		return cls(**data)
	
	def to_redis_json(self) -> str:
		"""
		Serialize the schema object to a JSON string for Redis storage.
		
		WHY THIS EXISTS:
		----------------
		Redis stores data as strings. When we want to store complex objects (like
		our Episode, Event, or Location schemas), we need to convert them to JSON strings.
		
		This method:
		1. Converts the Pydantic model to a dictionary (handles nested objects)
		2. Serializes datetime objects to ISO format strings
		3. Serializes pandas DataFrames to list of records
		4. Returns a JSON string ready for Redis storage
		
		Usage:
			episode = Episode(...)
			json_str = episode.to_redis_json()  # Returns: '{"episode_id": 1, ...}'
			redis_client.create("episode:1", json_str)
		
		Note: The quantagent_redis client actually handles this automatically via
		json.dumps(), but this method provides explicit control and handles
		advanced types like DataFrames that standard JSON can't serialize.
		"""
		# Custom serialization for advanced types
		def default_serializer(obj):
			if isinstance(obj, datetime):
				return obj.isoformat()
			elif isinstance(obj, pd.DataFrame):
				return obj.to_dict('records')
			raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
		
		return json.dumps(self.to_dict(), default=default_serializer)
	
	@classmethod
	def from_redis_json(cls, json_str: str) -> "BaseSchema":
		"""
		Deserialize a JSON string from Redis back into a schema object.
		
		WHY THIS EXISTS:
		----------------
		When we retrieve data from Redis, it comes back as a JSON string.
		We need to convert it back into our typed Pydantic model objects.
		
		This method:
		1. Parses the JSON string into a Python dictionary
		2. Converts ISO format datetime strings back to datetime objects
		3. Reconstructs nested objects (like Location within Episode)
		4. Returns a fully-typed schema instance
		
		Usage:
			json_str = redis_client.read("episode:1")  # Returns: '{"episode_id": 1, ...}'
			episode = Episode.from_redis_json(json_str)  # Returns: Episode object
		
		Note: The quantagent_redis client returns dictionaries, so we typically
		use from_dict() instead. But this method is useful if you're working
		directly with JSON strings from Redis.
		"""
		data = json.loads(json_str)
		return cls.from_dict(data)

