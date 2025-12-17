from fastapi import APIRouter, status, Query
from typing import List
from app.tasks.wildfire_sync_task import wildfire_sync_task
from app.exceptions import handle_service_exceptions
from app.schemas.wildfire import Wildfire
from app.state import state
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/wildfire", tags=["wildfire"])


@router.post("/sync", status_code=status.HTTP_202_ACCEPTED)
@handle_service_exceptions
async def sync_wildfire_data():
	"""
	Sync wildfire data by polling ArcGIS API.
	Creates, updates, or completes wildfire events based on API responses.
	
	This endpoint returns immediately and processes the sync asynchronously in the background.
	
	Returns:
		Dictionary with message and task ID
	"""
	task = wildfire_sync_task.delay()
	logger.info(f"Started wildfire sync task with ID: {task.id}")
	return {
		"message": "Wildfire sync task started",
		"task_id": task.id,
		"status": "processing"
	}


@router.get("/", response_model=List[Wildfire])
@handle_service_exceptions
async def get_wildfires(
	active_only: bool = Query(default=True, description="If true, return only active wildfires")
):
	"""
	Get wildfires from state, optionally filtered by active_only.
	
	Args:
		active_only: If true, return only wildfires from state.active_wildfires. Default is True.
	
	Returns:
		List of Wildfire objects matching the filter criteria
	"""
	if active_only:
		wildfires = state.active_wildfires
	else:
		wildfires = state.wildfires
	return wildfires
