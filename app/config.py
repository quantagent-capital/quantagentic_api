import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings:
	# Redis configuration
	redis_host: str = os.getenv("REDIS_HOST", "localhost")
	redis_port: int = int(os.getenv("REDIS_PORT", "6379"))
	redis_db: int = int(os.getenv("REDIS_DB", "0"))
	redis_password: Optional[str] = os.getenv("REDIS_PASSWORD", None)
	
	# NWS API configuration
	nws_user_agent_name: str = os.getenv("NWS_USER_AGENT_NAME", "quantagent_capital")
	nws_user_agent_email: str = os.getenv("NWS_USER_AGENT_EMAIL", "jacob@quantagent_capital.ai")
	
	# CrewAI / Gemini configuration
	gemini_model: str = os.getenv("GEMINI_MODEL", "gemini/gemini-3-pro-preview")
	gemini_api_key: str = os.getenv("GEMINI_API_KEY", "test")
	
	# Celery configuration
	executor_max_retries: int = int(os.getenv("EXECUTOR_MAX_RETRIES", "5"))
	
	# QuantAgentic API configuration
	quantagentic_api_base_url: str = os.getenv("QUANTAGENTIC_API_BASE_URL", "http://localhost")
	quantagent_api_port: int = int(os.getenv("QUANTAGENT_API_PORT", "8000"))

	ugc_zone_base_url: str = os.getenv("UGC_ZONE_BASE_URL", "https://api.weather.gov/zones/county/")

	@property
	def quantagentic_api_url(self) -> str:
		"""Full QuantAgentic API URL."""
		return f"{self.quantagentic_api_base_url}:{self.quantagent_api_port}"
	
	@property
	def celery_broker_url(self) -> str:
		"""Celery broker URL - uses same Redis as application."""
		return self.redis_url
	
	@property
	def celery_result_backend(self) -> str:
		"""Celery result backend - uses same Redis as application."""
		return self.redis_url
	
	@property
	def redis_url(self) -> str:
		if self.redis_password:
			return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
		return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"
	
	@property
	def nws_user_agent(self) -> str:
		"""Format NWS User-Agent header as required by NWS API."""
		return f"( {self.nws_user_agent_name}, {self.nws_user_agent_email} )"

settings = Settings()

