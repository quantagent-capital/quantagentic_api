"""
Disaster Polling Agent Crew using CrewAI @CrewBase pattern.
"""
from typing import Any
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, crew, agent, task
from crewai import LLM
from app.config import settings
from app.crews.tools.nws_polling_tool import NWSPollingTool
from app.crews.tools.get_active_events_and_episodes_tool import GetActiveEpisodesAndEventsTool
from app.crews.tools.forecast_zone_tool import GetForecastZoneTool
from app.crews.disaster_polling_agent.models import (
	PolledNWSAlertsOutput,
	ClassifiedAlertsOutput
)

@CrewBase
class DisasterPollingCrew:
	"""Disaster Polling Agent Crew for processing NWS alerts."""
	
	agents_config = 'config/agents.yaml'
	tasks_config = 'config/tasks.yaml'
	
	def __init__(self):
		"""Initialize the crew with Gemini LLM."""
		self.LLM = LLM(
			model=settings.gemini_model,
			api_key=settings.gemini_api_key
		)
	
	@agent
	def disaster_spotter(self) -> Agent:
		"""Create the disaster spotter agent."""
		return Agent(
			config=self.agents_config['disaster_spotter'],
			verbose=True,
			allow_delegation=False,
			llm=self.LLM
		)
	
	@task
	def poll_nws_alerts_task(self) -> Task:
		"""Task to poll NWS API for active alerts."""
		return Task(
			config=self.tasks_config['poll_nws_alerts'],
			agent=self.disaster_spotter(),
			output_pydantic=PolledNWSAlertsOutput,
			tools=[NWSPollingTool()]
		)
	
	@task
	def classify_alerts_task(self) -> Task:
		"""Task to classify alerts into new/updated events/episodes."""
		return Task(
			config=self.tasks_config['classify_alerts'],
			agent=self.disaster_spotter(),
			context=[
				self.poll_nws_alerts_task()
			],
			output_pydantic=ClassifiedAlertsOutput
		)
	
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
	
	@staticmethod
	def run_disaster_polling() -> Any:
		"""
		Run the disaster polling crew and return results.
		
		Returns:
			Crew execution result
		"""
		crew_instance = DisasterPollingCrew()
		result = crew_instance.crew().kickoff()
		return result
