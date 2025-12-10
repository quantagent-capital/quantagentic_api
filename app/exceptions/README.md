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

class EventService:
    @staticmethod
    def get_event(event_key: str) -> Optional[Event]:
        event = state.get_event(event_key)
        if event is None:
            raise NotFoundError("Event", event_key)
        return event
    
    @staticmethod
    def create_event(event: Event) -> Event:
        if not event.event_key:
            raise ValidationError("Event key is required")
        # ... create logic
        return event
```

## Usage in Controllers

Controllers use the `@handle_service_exceptions` decorator to automatically convert exceptions:

```python
from app.exceptions import handle_service_exceptions, NotFoundError

@router.get("/{event_key}")
@handle_service_exceptions
async def get_event(event_key: str):
    event = EventService.get_event(event_key)
    if event is None:
        raise NotFoundError("Event", event_key)
    return event
```

## Benefits

1. **Uniform**: All endpoints handle errors the same way
2. **Flexible**: Easy to add new exception types
3. **Clean**: Service layer doesn't need to know about HTTP status codes
4. **Expandable**: Can add custom exceptions for specific domains

