from fastapi import APIRouter, status, Query
from typing import List
from app.tasks.drought_sync_task import drought_sync_task
from app.exceptions import handle_service_exceptions
from app.schemas.drought import Drought
from app.state import state
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/drought", tags=["drought"])


@router.post("/sync", status_code=status.HTTP_202_ACCEPTED)
@handle_service_exceptions
async def sync_drought_data():
	"""
	Sync drought data by comparing current and previous week drought maps.
	Creates, updates, or completes drought events based on county intersections.
	
	This endpoint returns immediately and processes the sync asynchronously in the background.
	
	Returns:
		Dictionary with message and task ID
	"""
	task = drought_sync_task.delay()
	logger.info(f"Started drought sync task with ID: {task.id}")
	return {
		"message": "Drought sync task started",
		"task_id": task.id,
		"status": "processing"
	}


@router.get("/", response_model=List[Drought])
@handle_service_exceptions
async def get_droughts(
	active_only: bool = Query(default=True, description="If true, return only active droughts")
):
	"""
	Get droughts from state, optionally filtered by active_only.
	
	Args:
		active_only: If true, return only droughts from state.active_droughts. Default is True.
	
	Returns:
		List of Drought objects matching the filter criteria
	"""
	if active_only:
		droughts = state.active_droughts
	else:
		droughts = state.droughts
	return droughts
