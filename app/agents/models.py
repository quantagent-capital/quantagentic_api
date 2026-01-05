"""
Structured output models for agent tasks.
"""
from pydantic import BaseModel, Field


class WindValidationOutput(BaseModel):
	"""Structured output for wind validation task."""
	valid: bool = Field(description="Whether the wind warning references a wind speed of at least the threshold (default 65 MPH).")

