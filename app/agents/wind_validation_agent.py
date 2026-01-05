"""
Wind Validation Agent for validating High Wind Warnings.
"""
from crewai import Agent, Task, Crew
from app.config import settings
from app.agents.models import WindValidationOutput
import logging

logger = logging.getLogger(__name__)


class WindValidationAgent:
	"""
	Agent for validating whether a High Wind Warning meets the wind speed threshold.
	"""
	
	def __init__(self):
		"""Initialize the wind validation agent."""
		self.validator = Agent(
			role='Meteorological Wind Speed Validator',
			goal='Determine if a High Wind Warning references wind speeds of at least the specified threshold.',
			backstory='You are an expert meteorologist specializing in wind warnings. You carefully analyze weather alert text to extract wind speed information and determine if warnings meet severity thresholds.',
			allow_delegation=False,
			llm=settings.default_llm
		)
		
		self.validation_task = Task(
			description="""
			Analyze the provided headline and description from a High Wind Warning alert.
			
			Headline: {headline}
			Description: {description}
			
			Determine if the warning references wind speeds of at least {threshold_mph} MPH.
			Look for explicit wind speed mentions in the text (e.g., "65 mph", "70 miles per hour", "sustained winds of 65").
			Consider variations in how wind speeds are expressed (mph, miles per hour, knots converted to mph, etc.).
			
			A warning is VALID ONLY IF the warning explicitly mentions or implies wind speeds meeting or exceeding {threshold_mph} MPH.
			A warning is INVALID IF the warning does not mention wind speeds, or mentions speeds below {threshold_mph} MPH.
			""",
			agent=self.validator,
			output_pydantic=WindValidationOutput,
			expected_output="A WindValidationOutput with a valid boolean indicating if wind speeds meet the threshold",
		)
		
		# Create the crew with the single task
		self.crew = Crew(
			agents=[self.validator],
			tasks=[self.validation_task],
			verbose=True
		)
	
	def validate(self, headline: str, description: str) -> WindValidationOutput:
		"""
		Validate a High Wind Warning to determine if it meets the wind speed threshold.
		
		Args:
			headline: The alert headline
			description: The alert description
		
		Returns:
			WindValidationOutput with valid boolean
		
		Raises:
			ValueError: If headline, description, or config threshold is None/empty
		"""
		# Validate inputs
		if not headline:
			raise ValueError("headline cannot be None or empty")
		if not description:
			raise ValueError("description cannot be None or empty")
		
		threshold_mph = settings.wind_speed_threshold_mph
		if not threshold_mph or threshold_mph <= 0:
			raise ValueError(f"wind_speed_threshold_mph config value must be a positive integer, got: {threshold_mph}")
		
		inputs = {
			"headline": headline,
			"description": description,
			"threshold_mph": threshold_mph
		}
		result = self.crew.kickoff(inputs=inputs)
		return result.pydantic

