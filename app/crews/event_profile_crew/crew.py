"""
Event Profile Crew using CrewAI @CrewBase pattern.
"""
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, crew, agent, task
from crewai import LLM
from app.config import settings
from app.crews.event_profile_crew.models import HumanReadableEvent, ConstructedEventModel, Locations, VerifiedEventModel
from app.schemas.location import Location


@CrewBase
class EventProfileCrew:
	"""Event Profile Crew for creating Event models from FilteredNWSAlerts."""
	
	agents_config = 'config/agents.yaml'
	tasks_config = 'config/tasks.yaml'
	
	def __init__(self):
		"""Initialize the crew with Gemini LLM."""
		self.LLM = LLM(
			model=settings.gemini_model,
			api_key=settings.gemini_api_key
		)
	
	@agent
	def expert_gis_mapping_specialist(self) -> Agent:
		"""Create the event profiler agent."""
		return Agent(
			config=self.agents_config['expert_gis_mapping_specialist'],
			verbose=True,
			allow_delegation=False,
			llm=self.LLM
		)

	@agent
	def senior_quality_assurance_specialist(self) -> Agent:
		"""Create the senior quality assurance specialist agent."""
		return Agent(
			config=self.agents_config['senior_quality_assurance_specialist'],
			verbose=True,
			allow_delegation=False,
			llm=self.LLM
		)
	
	@task
	def map_location_from_endpoints_task(self) -> Task:
		"""Task to map locations from endpoints to Location objects."""
		return Task(
			config=self.tasks_config['map_location_from_endpoints'],
			agent=self.expert_gis_mapping_specialist(),
			output_pydantic=Locations
		)

	@task 
	def map_event_type_task(self) -> Task:
		"""Task to map event type to a HumanReadableEvent object."""
		return Task(
			config=self.tasks_config['map_event_type'],
			agent=self.expert_gis_mapping_specialist(),
			output_pydantic=HumanReadableEvent
		)

	@task
	def construct_event_model_task(self) -> Task:
		"""Task to map event to locations."""
		return Task(
			config=self.tasks_config['construct_event_model'],
			agent=self.expert_gis_mapping_specialist(),
			context=[
				self.map_location_from_endpoints_task(),
				self.map_event_type_task()
			],
			output_pydantic=ConstructedEventModel
		)

	@task
	def ensure_event_model_is_sound_task(self) -> Task:
		"""Task to ensure the event model is sound."""
		return Task(
			config=self.tasks_config['ensure_event_model_is_sound'],
			agent=self.senior_quality_assurance_specialist(),
			context=[
				self.map_location_from_endpoints_task(),
				self.map_event_type_task(),
				self.construct_event_model_task()
			],
			output_pydantic=VerifiedEventModel
		)

	# TODO: Once, episodes exist.
	# @task
	# def map_event_to_episode_task(self) -> Task:
	# 	"""Task to map event to episode."""
	
	@crew
	def crew(self) -> Crew:
		"""Create and return the crew."""
		return Crew(
			agents=self.agents,
			tasks=self.tasks,
			memory=False,
			process=Process.sequential,
			verbose=True
		)

