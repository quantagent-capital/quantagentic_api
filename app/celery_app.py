"""
Celery application configuration for background tasks.
"""
from celery import Celery
from celery.schedules import crontab
from app.config import settings

# Create Celery app
celery_app = Celery(
	"quantagentic_api",
	broker=settings.celery_broker_url,
	backend=settings.celery_result_backend
)

# Celery configuration
celery_app.conf.update(
	task_serializer="json",
	accept_content=["json"],
	result_serializer="json",
	timezone="UTC",
	enable_utc=True,
)

# CeleryBeat schedule
celery_app.conf.beat_schedule = {
	"disaster-polling-agent": {
		"task": "app.tasks.disaster_polling_task",
		"schedule": crontab(minute="*/5"),  # Every 5 minutes
	},
}

celery_app.conf.timezone = "UTC"

