from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.controllers import episode_controller, event_controller
from app.logging_config import setup_logging
import os

# Setup structured JSON logging to stdout (for Railway)
log_level = os.getenv("LOG_LEVEL", "INFO")
setup_logging(level=log_level)

app = FastAPI(
	title="QuantAgentic API",
	description="API for managing disaster episodes and events with AI agents",
	version="1.0.0"
)

# --- CORS CONFIGURATION START ---
# This allows Google AI Studio (and everyone else) to access your API
app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],  # Allows all origins
	allow_credentials=False,
	allow_methods=["*"],  # Allows all methods (GET, POST, etc.)
	allow_headers=["*"],  # Allows all headers (Authorization, etc.)
)
# --- CORS CONFIGURATION END ---

# Include routers
app.include_router(episode_controller.router)
app.include_router(event_controller.router)

@app.get("/")
async def root():
	return {
		"greeting": "Hello, World!",
		"message": "Welcome to QuantAgentic API!",
		"endpoints": {
			"episodes": "/episodes",
			"events": "/events"
		}
	}

@app.get("/health")
async def health():
	"""Health check endpoint."""
	from app.redis_client import quantagent_redis
	try:
		redis_healthy = quantagent_redis.ping()
		return {
			"status": "healthy",
			"redis": "connected" if redis_healthy else "disconnected"
		}
	except Exception as e:
		return {
			"status": "unhealthy",
			"redis": "error",
			"error": str(e)
		}