"""
Service for event confirmation operations.
"""
from datetime import datetime, timezone
from typing import Any, Dict, Optional
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.schemas.event import Event
from app.http_client.nws_client import NWSClient
from app.crews.event_confirmation_crew.executor import EventConfirmationExecutor
from app.state import state
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class EventConfirmationService:
	"""Service for Event confirmation operations."""
	
	@staticmethod
	async def confirm_event(event: Event) -> Any:
		"""
		Confirm whether an event occurred by running the confirmation crew.

		Algorithm:
		1. Get the LSRs for the event's office
		2. Process each LSR to collect observed coordinates
		3. If any observed coordinates are found, confirm the event and save all the observed locations
		
		Args:
			event: The Event object to confirm
		
		Returns:
			Result from the confirmation crew execution
		"""
		event_key = event.event_key
		
		# Check if event is already confirmed
		if event.confirmed:
			logger.info(f"Event {event_key} is already confirmed, skipping confirmation")
			return {"message": "Event already confirmed", "lsrs_processed": 0}

		# Extract office from event
		office = event.office
		if not office:
			raise ValueError(f"Event {event_key} does not have an office code")

		# Fetch LSRs asynchronously
		nws_client = NWSClient()
		all_lsrs = await nws_client.get_lsr(office, event.start_date)
		
		# If no LSRs found, return early
		if not all_lsrs:
			logger.info(f"No LSRs found for office {office}, skipping confirmation")
			return {"message": "No LSRs found", "lsrs_processed": 0}
		
		# Filter to only process new LSRs (smart polling)
		new_lsrs = [lsr for lsr in all_lsrs if not state.is_lsr_polled(lsr.lsr_id)]
		
		if len(new_lsrs) < len(all_lsrs):
			logger.info(f"Filtered {len(all_lsrs)} LSRs to {len(new_lsrs)} new LSRs (skipped {len(all_lsrs) - len(new_lsrs)} already polled)")
		
		if not new_lsrs:
			logger.info(f"All LSRs for office {office} have already been polled, skipping confirmation")
			return {"message": "All LSRs already polled", "lsrs_processed": 0}
		
		logger.info(f"Found {len(new_lsrs)} new LSRs for office {office}, starting confirmation for event {event_key}")
		
		# Process all LSRs (no short-circuit)
		lsrs_processed = 0
		confirmed_count = 0
		last_confirmed_coordinate = None
		
		for lsr in new_lsrs:
			try:
				# Create executor and run the crew for each LSR
				executor = EventConfirmationExecutor()
				result = executor.execute(
					event_key,
					description=lsr.description,
					issuing_office=lsr.office
				)

				# Check if we got a confirmation
				if result.pydantic and result.pydantic.confirmed:
					confirmed_coordinate = result.pydantic.observed_coordinate
					confirmed_location_index = result.pydantic.location_index
					confirmed_count += 1
					last_confirmed_coordinate = confirmed_coordinate
					
					logger.info(f"Event {event_key} confirmed with coordinate ({confirmed_coordinate.latitude}, {confirmed_coordinate.longitude}) at location index {confirmed_location_index}")
					
					# Set observed_coordinate for the specific location where confirmation occurred
					if confirmed_location_index is not None and 0 <= confirmed_location_index < len(event.locations):
						event.locations[confirmed_location_index].observed_coordinate = confirmed_coordinate
						logger.info(f"Set observed_coordinate on location index {confirmed_location_index} (ugc_code: {event.locations[confirmed_location_index].ugc_code})")
					else:
						logger.warning(f"Invalid location_index {confirmed_location_index} for event {event_key} with {len(event.locations)} locations")
					
					# Mark event as confirmed and update (update after each confirmation to persist all coordinates)
					event.confirmed = True
					event.updated_at = datetime.now(timezone.utc)
					state.update_event(event)
				
				# Mark LSR as polled after successful processing (only if no exception occurred)
				state.add_polled_lsr_id(lsr.lsr_id)
				lsrs_processed += 1
				
			except Exception as e:
				# Log error but continue processing remaining LSRs
				logger.error(f"Error processing LSR {lsr.lsr_id} for event {event_key}: {str(e)}")
				import traceback
				logger.error(traceback.format_exc())
				# Don't mark as polled if processing failed
				continue
		
		if confirmed_count > 0:
			logger.info(f"Confirmation completed for event {event_key}, processed {lsrs_processed} LSRs, found {confirmed_count} confirmation(s)")
		else:
			logger.info(f"Confirmation completed for event {event_key}, processed {lsrs_processed} LSRs, no confirmation found")

		return {
			"lsrs_processed": lsrs_processed,
			"confirmed": confirmed_count > 0,
			"observed_coordinate": last_confirmed_coordinate,
			"confirmations_count": confirmed_count
		}
	
	@staticmethod
	async def confirm_events(max_concurrent: Optional[int] = None) -> Dict[str, Any]:
		"""
		Confirm all active and unconfirmed events in parallel using ThreadPoolExecutor.
		
		Algorithm:
		1. Get all active and unconfirmed events from state
		2. Process events in parallel with configurable concurrency limit using ThreadPoolExecutor
		3. Return summary of results
		
		Args:
			max_concurrent: Maximum number of concurrent confirmations (defaults to settings value)
		
		Returns:
			Dictionary with summary of confirmation results
		"""
		# Get all active and unconfirmed events
		events_to_confirm = state.active_and_unconfirmed_events
		
		if not events_to_confirm:
			logger.info("No active and unconfirmed events to process")
			return {
				"events_processed": 0,
				"events_confirmed": 0,
				"events_failed": 0,
				"message": "No events to confirm"
			}
		
		# Use provided max_concurrent or default from settings
		concurrency_limit = max_concurrent or settings.event_confirmation_max_concurrent
		
		logger.info(f"Starting parallel confirmation for {len(events_to_confirm)} active and unconfirmed events (max concurrent: {concurrency_limit})")
		
		def confirm_event_sync(event: Event) -> Dict[str, Any]:
			"""
			Synchronous wrapper function that runs the async confirm_event in a new event loop.
			
			Args:
				event: Event to confirm
			
			Returns:
				Dictionary with event_key and result/error information
			"""
			try:
				# Create a new event loop for this thread
				loop = asyncio.new_event_loop()
				asyncio.set_event_loop(loop)
				try:
					result = loop.run_until_complete(EventConfirmationService.confirm_event(event))
					return {
						"event_key": event.event_key,
						"confirmed": result.get("confirmed", False),
						"lsrs_processed": result.get("lsrs_processed", 0),
						"error": None
					}
				finally:
					loop.close()
			except Exception as e:
				logger.error(f"Error confirming event {event.event_key}: {str(e)}")
				return {
					"event_key": event.event_key,
					"confirmed": False,
					"lsrs_processed": 0,
					"error": str(e)
				}
		
		# Use ThreadPoolExecutor to run confirmations in parallel
		results = []
		total_events = len(events_to_confirm)
		completed_count = 0
		
		with ThreadPoolExecutor(max_workers=concurrency_limit) as executor:
			# Submit all tasks to the executor
			future_to_event = {
				executor.submit(confirm_event_sync, event): event 
				for event in events_to_confirm
			}
			
			# Collect results as they complete
			for future in as_completed(future_to_event):
				completed_count += 1
				try:
					result = future.result()
					results.append(result)
					
					# Log progress
					status = "confirmed" if result.get("confirmed", False) else "not confirmed"
					logger.info(f"Thread progress: {completed_count}/{total_events} completed - Event {result.get('event_key')} {status}")
				except Exception as e:
					event = future_to_event[future]
					logger.error(f"Unexpected error in thread for event {event.event_key}: {str(e)}")
					results.append({
						"event_key": event.event_key,
						"confirmed": False,
						"lsrs_processed": 0,
						"error": str(e)
					})
					logger.info(f"Thread progress: {completed_count}/{total_events} completed - Event {event.event_key} failed")
		
		# Calculate summary statistics
		events_confirmed = sum(1 for r in results if r.get("confirmed", False))
		events_failed = sum(1 for r in results if r.get("error") is not None)
		
		logger.info(f"Confirmation batch completed: {events_confirmed} confirmed, {events_failed} failed out of {len(events_to_confirm)} total")
		
		return {
			"events_processed": len(events_to_confirm),
			"events_confirmed": events_confirmed,
			"events_failed": events_failed,
			"max_concurrent": concurrency_limit,
			"results": results
		}
