from typing import Optional, Dict, Any
import httpx
from abc import ABC, abstractmethod

class BaseHTTPClient(ABC):
	"""
	Base HTTP client class for scalable and robust API interactions.
	Can be extended for different API clients.
	"""
	
	def __init__(
		self,
		base_url: str,
		default_headers: Optional[Dict[str, str]] = None,
		timeout: float = 30.0,
		max_retries: int = 3
	):
		self.base_url = base_url.rstrip('/')
		self.default_headers = default_headers or {}
		self.timeout = timeout
		self.max_retries = max_retries
		self.client = httpx.AsyncClient(
			base_url=self.base_url,
			headers=self.default_headers,
			timeout=self.timeout
		)
	
	async def get(
		self,
		endpoint: str,
		params: Optional[Dict[str, Any]] = None,
		headers: Optional[Dict[str, str]] = None
	) -> Dict[str, Any]:
		"""
		Perform a GET request.
		
		Args:
			endpoint: API endpoint (relative to base_url)
			params: Query parameters
			headers: Additional headers (merged with default_headers)
		
		Returns:
			Response JSON as dictionary
		"""
		merged_headers = {**self.default_headers, **(headers or {})}
		
		for attempt in range(self.max_retries):
			try:
				response = await self.client.get(
					endpoint,
					params=params,
					headers=merged_headers
				)
				response.raise_for_status()
				return response.json()
			except httpx.HTTPStatusError as e:
				if attempt == self.max_retries - 1:
					raise
				# Could add exponential backoff here
			except Exception as e:
				if attempt == self.max_retries - 1:
					raise
				# Could add exponential backoff here
	
	async def post(
		self,
		endpoint: str,
		data: Optional[Dict[str, Any]] = None,
		json: Optional[Dict[str, Any]] = None,
		headers: Optional[Dict[str, str]] = None
	) -> Dict[str, Any]:
		"""
		Perform a POST request.
		
		Args:
			endpoint: API endpoint (relative to base_url)
			data: Form data
			json: JSON body
			headers: Additional headers (merged with default_headers)
		
		Returns:
			Response JSON as dictionary
		"""
		merged_headers = {**self.default_headers, **(headers or {})}
		
		for attempt in range(self.max_retries):
			try:
				response = await self.client.post(
					endpoint,
					data=data,
					json=json,
					headers=merged_headers
				)
				response.raise_for_status()
				return response.json()
			except httpx.HTTPStatusError as e:
				if attempt == self.max_retries - 1:
					raise
			except Exception as e:
				if attempt == self.max_retries - 1:
					raise
	
	async def put(
		self,
		endpoint: str,
		data: Optional[Dict[str, Any]] = None,
		json: Optional[Dict[str, Any]] = None,
		headers: Optional[Dict[str, str]] = None
	) -> Dict[str, Any]:
		"""
		Perform a PUT request.
		"""
		merged_headers = {**self.default_headers, **(headers or {})}
		
		for attempt in range(self.max_retries):
			try:
				response = await self.client.put(
					endpoint,
					data=data,
					json=json,
					headers=merged_headers
				)
				response.raise_for_status()
				return response.json()
			except httpx.HTTPStatusError as e:
				if attempt == self.max_retries - 1:
					raise
			except Exception as e:
				if attempt == self.max_retries - 1:
					raise
	
	async def delete(
		self,
		endpoint: str,
		headers: Optional[Dict[str, str]] = None
	) -> Dict[str, Any]:
		"""
		Perform a DELETE request.
		"""
		merged_headers = {**self.default_headers, **(headers or {})}
		
		for attempt in range(self.max_retries):
			try:
				response = await self.client.delete(
					endpoint,
					headers=merged_headers
				)
				response.raise_for_status()
				return response.json() if response.content else {}
			except httpx.HTTPStatusError as e:
				if attempt == self.max_retries - 1:
					raise
			except Exception as e:
				if attempt == self.max_retries - 1:
					raise
	
	async def close(self):
		"""Close the HTTP client."""
		await self.client.aclose()
	
	async def __aenter__(self):
		return self
	
	async def __aexit__(self, exc_type, exc_val, exc_tb):
		await self.close()

