import json
import redis
import logging
from typing import Optional, Any, Dict, TypeVar, Type
from app.config import settings

logger = logging.getLogger(__name__)

T = TypeVar('T')

class QuantAgentRedis:
	"""
	Generalized Redis client wrapper for basic CRUD operations.
	Handles JSON serialization/deserialization automatically.
	"""
	
	def __init__(self):
		self.client = redis.Redis(
			host=settings.redis_host,
			port=settings.redis_port,
			db=settings.redis_db,
			password=settings.redis_password,
			decode_responses=True,
			socket_connect_timeout=5,
			socket_timeout=5
		)
	
	def create(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
		"""
		Create or update a key-value pair in Redis.
		
		Args:
			key: Redis key
			value: Value to store (will be JSON serialized)
			ttl: Optional time-to-live in seconds
		
		Returns:
			True if successful
		"""
		try:
			serialized = json.dumps(value, default=str)
			if ttl:
				return self.client.setex(key, ttl, serialized)
			return self.client.set(key, serialized)
		except Exception as e:
			raise ValueError(f"Failed to create key {key}: {str(e)}")
	
	def read(self, key: str) -> Optional[Any]:
		"""
		Read a value from Redis by key.
		
		Args:
			key: Redis key
		
		Returns:
			Deserialized value or None if key doesn't exist
		"""
		try:
			value = self.client.get(key)
			if value is None:
				return None
			return json.loads(value)
		except json.JSONDecodeError:
			# If it's not JSON, return as string
			return value
		except Exception as e:
			raise ValueError(f"Failed to read key {key}: {str(e)}")
	
	def _normalize_to_dict(self, data: Any, key: str, entity_type: str) -> Optional[Dict]:
		"""
		Normalize Redis data to a dictionary, handling edge cases.
		
		Args:
			data: Raw data from Redis (could be None, str, or dict)
			key: Redis key (for logging)
			entity_type: Type of entity (for logging, e.g., "event", "drought")
		
		Returns:
			Dictionary if successful, None otherwise
		"""
		if data is None:
			return None
		
		# Handle case where Redis returns a string instead of dict
		# (can happen if JSON parsing failed in read method)
		if isinstance(data, str):
			try:
				data = json.loads(data)
			except json.JSONDecodeError:
				logger.warning(f"Failed to parse {entity_type} JSON string from Redis key {key}")
				return None
		
		# Ensure we have a dictionary
		if not isinstance(data, dict):
			logger.warning(f"{entity_type.capitalize()} data from Redis key {key} is not a dictionary: {type(data)}")
			return None
		
		return data
	
	def read_as_dict(self, key: str, entity_type: str = "entity") -> Optional[Dict]:
		"""
		Read a value from Redis and normalize it to a dictionary.
		Handles edge cases like string values and type checking.
		
		Args:
			key: Redis key
			entity_type: Type of entity (for logging)
		
		Returns:
			Dictionary if successful, None otherwise
		"""
		try:
			raw_data = self.read(key)
			return self._normalize_to_dict(raw_data, key, entity_type)
		except Exception as e:
			logger.warning(f"Failed to read {entity_type} from Redis key {key}: {str(e)}")
			return None
	
	def read_as_schema(self, key: str, schema_class: Type[T], entity_type: str = "entity") -> Optional[T]:
		"""
		Read a value from Redis and deserialize it to a schema object.
		Handles all edge cases: None values, string conversion, type checking, and errors.
		
		Args:
			key: Redis key
			schema_class: Schema class with from_dict method (e.g., Event, Drought)
			entity_type: Type of entity (for logging)
		
		Returns:
			Schema object if successful, None otherwise
		"""
		try:
			raw_data = self.read(key)
			normalized_data = self._normalize_to_dict(raw_data, key, entity_type)
			
			if normalized_data is None:
				return None
			
			# Convert dictionary to schema object
			return schema_class.from_dict(normalized_data)
		except Exception as e:
			logger.warning(f"Failed to load {entity_type} from Redis key {key}: {str(e)}")
			return None
	
	def read_all_as_schema(self, keys: list[str], schema_class: Type[T], entity_type: str = "entity") -> list[T]:
		"""
		Read multiple values from Redis and deserialize them to schema objects.
		Handles all edge cases and continues processing even if some fail.
		
		Args:
			keys: List of Redis keys
			schema_class: Schema class with from_dict method
			entity_type: Type of entity (for logging)
		
		Returns:
			List of schema objects (only successful deserializations)
		"""
		results = []
		for key in keys:
			schema_obj = self.read_as_schema(key, schema_class, entity_type)
			if schema_obj is not None:
				results.append(schema_obj)
		return results
	
	def update(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
		"""
		Update an existing key-value pair in Redis.
		Same as create, but semantically indicates an update operation.
		
		Args:
			key: Redis key
			value: Value to store (will be JSON serialized)
			ttl: Optional time-to-live in seconds
		
		Returns:
			True if successful
		"""
		return self.create(key, value, ttl)
	
	def delete(self, key: str) -> bool:
		"""
		Delete a key from Redis.
		
		Args:
			key: Redis key
		
		Returns:
			True if key was deleted, False if key didn't exist
		"""
		try:
			return bool(self.client.delete(key))
		except Exception as e:
			raise ValueError(f"Failed to delete key {key}: {str(e)}")
	
	def exists(self, key: str) -> bool:
		"""
		Check if a key exists in Redis.
		
		Args:
			key: Redis key
		
		Returns:
			True if key exists, False otherwise
		"""
		try:
			return bool(self.client.exists(key))
		except Exception as e:
			raise ValueError(f"Failed to check existence of key {key}: {str(e)}")
	
	def get_all_keys(self, pattern: str = "*") -> list[str]:
		"""
		Get all keys matching a pattern.
		
		Args:
			pattern: Redis key pattern (default: "*" for all keys)
		
		Returns:
			List of matching keys
		"""
		try:
			return list(self.client.keys(pattern))
		except Exception as e:
			raise ValueError(f"Failed to get keys with pattern {pattern}: {str(e)}")
	
	def ping(self) -> bool:
		"""
		Test Redis connection.
		
		Returns:
			True if connection is alive
		"""
		try:
			return self.client.ping()
		except Exception as e:
			raise ConnectionError(f"Redis connection failed: {str(e)}")

# Global instance
quantagent_redis = QuantAgentRedis()

