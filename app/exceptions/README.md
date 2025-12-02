# Exception Framework

This exception framework provides a clean, uniform way to handle errors across the application.

## Custom Exceptions

All custom exceptions inherit from `QuantAgentException`:

- **`NotFoundError`**: Resource not found (HTTP 404)
- **`ValidationError`**: Validation failed (HTTP 400)
- **`ServiceError`**: Service operation failed (HTTP 500, customizable)

## Usage in Service Layer

Service classes can raise custom exceptions that will be automatically converted to appropriate HTTP responses:

```python
from app.exceptions import NotFoundError, ValidationError, ServiceError

class EpisodeService:
    @staticmethod
    def get_episode(episode_id: int) -> Optional[Episode]:
        episode_dict = quantagent_redis.read(f"episode:{episode_id}")
        if episode_dict is None:
            raise NotFoundError("Episode", str(episode_id))
        return Episode.from_dict(episode_dict)
    
    @staticmethod
    def create_episode(episode: Episode) -> Episode:
        if episode.episode_id < 0:
            raise ValidationError("Episode ID must be positive")
        # ... create logic
        return episode
```

## Usage in Controllers

Controllers use the `@handle_service_exceptions` decorator to automatically convert exceptions:

```python
from app.exceptions import handle_service_exceptions, NotFoundError

@router.get("/{episode_id}")
@handle_service_exceptions
async def get_episode(episode_id: int):
    episode = EpisodeService.get_episode(episode_id)
    if episode is None:
        raise NotFoundError("Episode", str(episode_id))
    return episode
```

## Benefits

1. **Uniform**: All endpoints handle errors the same way
2. **Flexible**: Easy to add new exception types
3. **Clean**: Service layer doesn't need to know about HTTP status codes
4. **Expandable**: Can add custom exceptions for specific domains

