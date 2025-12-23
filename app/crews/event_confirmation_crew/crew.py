"""
Event Confirmation Crew for confirming whether disaster events occurred.
"""
from crewai import Agent, Task, Crew
from typing import Any, Dict
from app.config import settings
from app.crews.event_confirmation_crew.models import CoordinateExtractionOutput, EventConfirmationOutput
from app.crews.event_confirmation_crew.tools import ConfirmEventLocationTool


class EventLocationConfirmationCrew:
	"""
	Crew for confirming whether disaster events occurred via LSR coordinate extraction.
	"""
	
	def __init__(self):
		"""Initialize the event confirmation crew."""
		self.confirm_event_location_tool = ConfirmEventLocationTool()
		self.researcher = Agent(
			role='Senior Disaster Event Researcher',
			goal='Search the web for high-quality information and extract content.',
			backstory='You are an expert disaster researcher who is able to determine if an event occurred or not.',
			verbose=True,
			allow_delegation=False,
			llm=settings.default_llm
		)
		
		self.extract_coordinates_task = Task(
			description="""
			Analyze the LSR description and extract the latitude and longitude coordinates.
			Here is the description: {description}
			Look for coordinate patterns like "40.32N 121.00W" or "LAT.LON" format in the description text.
			Example: "1100 AM     Flood            Westwood                40.32N 121.00W" contains coordinates 40.32N, 121.00W.
			If you cannot find any valid coordinates, return latitude=0.0 and longitude=0.0.
			""",
			agent=self.researcher,
			expected_output="A structured output with latitude and longitude coordinates",
			output_json=CoordinateExtractionOutput
		)

		self.confirm_location_task = Task(
			description="""
			First, ensure you have the coordinates from the previous task and the event_key from the inputs.
			Next, call the confirm_event_location tool with:
			- event_key: {event_key} The event key from the inputs dictionary
			- latitude: The latitude from extract_coordinates_task.output.latitude
			- longitude: The longitude from extract_coordinates_task.output.longitude
			The tool will check if these coordinates are contained within the specified event's polygons.
			""",
			agent=self.researcher,
			expected_output="A structured EventConfirmationOutput",
			output_json=EventConfirmationOutput,
			tools=[self.confirm_event_location_tool],
			context=[self.extract_coordinates_task]
		)
		
		# Create the crew with both tasks
		self.crew = Crew(
			agents=[self.researcher],
			tasks=[self.extract_coordinates_task, self.confirm_location_task],
			verbose=True
		)
	
	def kickoff(self, inputs: Dict[str, Any]) -> Any:
		"""
		Execute the crew with given inputs.
		
		Args:
			inputs: Dictionary containing input data for the crew
				- event_key: The event key
				- description: LSR description text
				- issuing_office: NWS office code
		
		Returns:
			Result from crew execution
		"""
		return self.crew.kickoff(inputs=inputs)
