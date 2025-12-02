import json
import redis
from typing import Optional, Any, Dict
from app.config import settings

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

