from fastapi import status
from typing import Optional

class QuantAgentException(Exception):
	"""
	Base exception class for all QuantAgent custom exceptions.
	All service layer exceptions should inherit from this.
	"""
	def __init__(
		self,
		message: str,
		status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
		detail: Optional[str] = None
	):
		self.message = message
		self.status_code = status_code
		self.detail = detail or message
		super().__init__(self.message)

class NotFoundError(QuantAgentException):
	"""
	Exception raised when a resource is not found.
	Maps to HTTP 404.
	"""
	def __init__(self, resource_type: str, resource_id: str):
		message = f"{resource_type} '{resource_id}' not found"
		super().__init__(
			message=message,
			status_code=status.HTTP_404_NOT_FOUND,
			detail=message
		)

class ValidationError(QuantAgentException):
	"""
	Exception raised when validation fails.
	Maps to HTTP 400.
	"""
	def __init__(self, message: str, detail: Optional[str] = None):
		super().__init__(
			message=message,
			status_code=status.HTTP_400_BAD_REQUEST,
			detail=detail or message
		)

class ServiceError(QuantAgentException):
	"""
	Exception raised when a service operation fails.
	Maps to HTTP 500 by default, but can be customized.
	"""
	def __init__(self, message: str, status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR):
		super().__init__(
			message=message,
			status_code=status_code,
			detail=message
		)

