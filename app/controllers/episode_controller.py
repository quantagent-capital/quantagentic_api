from fastapi import APIRouter, HTTPException, status
from typing import Optional
from app.schemas.episode import Episode
from app.services.episode_service import EpisodeService
from app.exceptions import handle_service_exceptions, NotFoundError

router = APIRouter(prefix="/episodes", tags=["episodes"])

@router.post("/", response_model=Episode, status_code=status.HTTP_201_CREATED)
@handle_service_exceptions
async def create_episode(episode: Episode):
	"""
	Create a new episode.
	"""
	created_episode = EpisodeService.create_episode(episode)
	return created_episode

@router.put("/{episode_id}", response_model=Episode)
@handle_service_exceptions
async def update_episode(episode_id: int, episode: Episode):
	"""
	Update an existing episode.
	"""
	updated_episode = EpisodeService.update_episode(episode_id, episode)
	if updated_episode is None:
		raise NotFoundError("Episode", str(episode_id))
	return updated_episode

@router.get("/{episode_id}", response_model=Episode)
@handle_service_exceptions
async def get_episode(episode_id: int):
	"""
	Get an episode by ID.
	"""
	episode = EpisodeService.get_episode(episode_id)
	if episode is None:
		raise NotFoundError("Episode", str(episode_id))
	return episode

