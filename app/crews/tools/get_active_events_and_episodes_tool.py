"""
Custom CrewAI tool for accessing active episodes and events from state.
"""
import json
from typing import Type
from pydantic import BaseModel, Field
from crewai.tools import BaseTool
from app.state import state


class GetActiveEpisodesAndEventsInput(BaseModel):
	"""Input schema for state tool."""
	include_metadata: bool = Field(
		default=True,
		description="Whether to include full metadata or just keys"
	)


class GetActiveEpisodesAndEventsTool(BaseTool):
	"""
	Tool to get active episodes and events from the shared state object.
	"""
	name: str = "GetActiveEpisodesAndEventsTool"
	description: str = (
		"Use this tool to retrieve active episodes and events from the shared state. "
		"Returns metadata about currently active disaster episodes and events. "
		"Use this to check if an event or episode already exists before creating/updating."
	)
	args_schema: Type[BaseModel] = GetActiveEpisodesAndEventsInput
	
	def _run(self, include_metadata: bool = True) -> str:
		"""
		Get active episodes and events from state.
		
		Args:
			include_metadata: Whether to include full metadata or just keys
		
		Returns:
			JSON string with active episodes and events
		"""
		try:
			active_episodes = state.active_episodes
			active_events = state.active_events
			
			if include_metadata:
				# Return full metadata
				episodes_data = [
					{
						"episode_id": ep.episode_id,
						"episode_key": ep.episode_key,
						"start_date": ep.start_date.isoformat() if ep.start_date else None,
						"is_active": ep.is_active,
						"locations": [
							{
								"ugc_code": loc.ugc_code,
								"shape": loc.shape
							}
							for loc in ep.locations
						]
					}
					for ep in active_episodes
				]
				
				events_data = [
					{
						"event_key": ev.event_key,
						"episode_id": ev.episode_id,
						"event_type": ev.event_type,
						"is_active": ev.is_active,
						"location": {
							"ugc_code": ev.location.ugc_code,
							"shape": ev.location.shape
						}
					}
					for ev in active_events
				]
			else:
				# Return just keys
				episodes_data = [
					{
						"episode_key": ep.episode_key
					}
					for ep in active_episodes
				]
				
				events_data = [
					{
						"event_key": ev.event_key
					}
					for ev in active_events
				]
			
			result = {
				"active_episodes": episodes_data,
				"active_events": events_data,
			}
			
			return json.dumps(result, indent=2)
			
		except Exception as e:
			return f"Error accessing state: {str(e)}"

