"""
Service for event confirmation operations.
"""
from typing import Any
from app.services.event_crud_service import EventCRUDService
from app.http_client.nws_client import NWSClient
from app.crews.event_confirmation_crew.executor import EventConfirmationExecutor
from app.state import state
import logging

logger = logging.getLogger(__name__)


class EventConfirmationService:
	"""Service for Event confirmation operations."""
	
	@staticmethod
	async def confirm_event(event_key: str) -> Any:
		"""
		Confirm whether an event occurred by running the confirmation crew.

		Algorithm:
		1. Get the event from the database
		2. Get the LSRs for the event's office
		3. Process each LSR to collect observed coordinates
		4. If any observed coordinates are found, confirm the event and save all the observed locations
		
		Args:
			event_key: The event key to confirm
		
		Returns:
			Result from the confirmation crew execution
		"""
		# Verify event exists
		event = EventCRUDService.get_event(event_key)
		if event is None:
			raise ValueError(f"Event with key {event_key} not found")
		
		# Extract office from event
		office = event.office
		if not office:
			raise ValueError(f"Event {event_key} does not have an office code")

		# Fetch LSRs asynchronously
		nws_client = NWSClient()
		lsrs = await nws_client.get_lsr_by_office(office)
		
		# If no LSRs found, return early
		if not lsrs:
			logger.info(f"No LSRs found for office {office}, skipping confirmation")
			return {"message": "No LSRs found", "lsrs_processed": 0}
		
		logger.info(f"Found {len(lsrs)} LSRs for office {office}, starting confirmation for event {event_key}")
		
		# Process all LSRs to collect observed coordinates
		results = []
		all_observed_locations = []
		event_confirmed = False
		
		for lsr in lsrs:
			# Create executor and run the crew for each LSR
			executor = EventConfirmationExecutor()
			result = executor.execute(
				event_key,
				description=lsr.description,
				issuing_office=lsr.office
			)

			# Collect results and observed locations
			if result.pydantic:
				results.append(result)
				if result.pydantic.confirmed:
					event_confirmed = True
				if result.pydantic.observed_locations:
					all_observed_locations.extend(result.pydantic.observed_locations)
		
		if event_confirmed:
			event.confirmed = True
			event.observed_coordinates = all_observed_locations
			state.update_event(event)

		logger.info(f"Confirmation completed for event {event_key}, processed {len(lsrs)} LSRs, found {len(all_observed_locations)} observed coordinates")
		return {
			"lsrs_processed": len(lsrs),
			"confirmed": event_confirmed,
			"num_observed_locations": len(all_observed_locations),
			"observed_locations": all_observed_locations
		}


# TODO, we are here. 
# We need to test the confirmation stack (service, crew, tool).
# We need to save all observed locations for the event based on this stack.
# From there, if all checks out, for events that are not confirmed, we should spawn another crew
# The new crew will use serper dev and other tools to find the event in the news, and confirm the event based on the event.dsecriptions vs newssight.description. 
# From there, ensure that updates dont override the confirmed status. 
# Also, the FE should account for observed locations by placing something on the map exactly where they are. 
# We should consider parallelizing the confirmation stack. It doesnt seem necessary honestly. But consider it again.