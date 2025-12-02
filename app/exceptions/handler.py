from functools import wraps
from fastapi import HTTPException, status
from app.exceptions.base import QuantAgentException

def handle_service_exceptions(func):
    """
    Decorator to handle service layer exceptions uniformly.
    Converts QuantAgentException to HTTPException with appropriate status codes.
    
    Usage:
        @handle_service_exceptions
        async def my_endpoint():
            # Service calls that may raise QuantAgentException
            result = SomeService.do_something()
            return result
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except QuantAgentException as e:
            # Convert our custom exceptions to HTTPException
            raise HTTPException(
                status_code=e.status_code,
                detail=e.detail
            )
        except HTTPException:
            # Re-raise HTTPExceptions (like 404 from controllers)
            raise
        except Exception as e:
            # Catch-all for unexpected errors
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Internal server error: {str(e)}"
            )
    return wrapper

