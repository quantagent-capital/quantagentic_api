import os
from typing import Optional

class Settings:
	# Redis configuration
	redis_host: str = os.getenv("REDIS_HOST", "localhost")
	redis_port: int = int(os.getenv("REDIS_PORT", "6379"))
	redis_db: int = int(os.getenv("REDIS_DB", "0"))
	redis_password: Optional[str] = os.getenv("REDIS_PASSWORD", None)
	
	# NWS API configuration
	nws_user_agent_name: str = os.getenv("NWS_USER_AGENT_NAME", "quantagent_capital")
	nws_user_agent_email: str = os.getenv("NWS_USER_AGENT_EMAIL", "jacob@quantagent_capital.ai")
	
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

