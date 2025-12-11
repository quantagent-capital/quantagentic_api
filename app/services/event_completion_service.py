from datetime import datetime, timezone, timedelta
from typing import List
from app.schemas.event import Event
from app.state import state
from app.http_client.nws_client import NWSClient
from app.utils import vtec
from app.config import settings
from app.utils.nws_alert_parser import NWSAlertParser
import asyncio
import logging

logger = logging.getLogger(__name__)


class EventCompletionService:
	"""Service for checking and marking completed events."""

	@staticmethod
	def check_completed_events():
		"""
		Check for completed events that should be marked as inactive.
		
		Algorithm:
		1. Get all active events from state
		2. Filter events where expected_end_date <= current time
		3. For each filtered event:
		   a. Get most recent alert from NWS API (following replacedBy links)
		   b. Check message type - if CAN or EXP, mark as inactive
		   c. If message type is NOT CAN/EXP but current time is past expected_end_date by timeout, also mark inactive
		   d. Set actual_end_time based on fallback chain
		"""
		try:
			# Get all active events
			active_events = state.active_events
			logger.info(f"Found {len(active_events)} active events")
			
			# Filter events where expected_end_date <= current time
			current_time = datetime.now(timezone.utc)
			events_to_check = [
				event for event in active_events
				if event.expected_end_date is not None and event.expected_end_date <= current_time
			]
			logger.info(f"Found {len(events_to_check)} events past expected end date")
			
			if not events_to_check:
				return
			
			# Process events asynchronously
			asyncio.run(EventCompletionService._async_check_completed_events(events_to_check))
			
		except Exception as e:
			logger.error(f"Error checking completed events: {str(e)}")
			import traceback
			logger.error(traceback.format_exc())

	@staticmethod
	async def _async_check_completed_events(events_to_check: List[Event]):
		"""
		Async implementation of checking completed events.
		
		Args:
			events_to_check: List of events to check
		"""
		client = NWSClient()
		
		try:
			for event in events_to_check:
				try:
					logger.info(f"Checking completed status for event {event.event_key} (alert_id: {event.nws_alert_id})")
					
					# Get the most recent alert by following replacedBy links
					most_recent_alert = await NWSAlertParser.get_most_recent_alert(client, event.nws_alert_id)
					
					if most_recent_alert is None:
						logger.warning(f"Could not retrieve alert {event.nws_alert_id} for event {event.event_key}")
						continue
					
					# Extract properties from alert
					properties = NWSAlertParser.extract_properties_from_alert(most_recent_alert, event.nws_alert_id)
					if properties is None:
						continue
					
					# Get message type from VTEC
					message_type = vtec.get_message_type(properties)
					message_type_upper = message_type.upper() if message_type else None
					
					# Check if we should mark as inactive
					should_deactivate = False
					
					# Case 1: Message type is CAN or EXP
					if message_type_upper in ["CAN", "EXP"]:
						logger.info(f"Event {event.event_key} has message type {message_type_upper} - marking as inactive")
						should_deactivate = True
					
					# Case 2: Message type is NOT CAN/EXP but current time is past expected_end_date by timeout
					else:
						current_time = datetime.now(timezone.utc)
						timeout_minutes = settings.event_completion_timeout_minutes
						timeout_threshold = event.expected_end_date + timedelta(minutes=timeout_minutes)
						
						if current_time >= timeout_threshold:
							logger.info(
								f"Event {event.event_key} is past expected end date by {timeout_minutes} minutes "
								f"(expected: {event.expected_end_date}, threshold: {timeout_threshold}) - marking as inactive"
							)
							should_deactivate = True
					
					# If we should deactivate, update the event
					if should_deactivate:
						actual_end_time = NWSAlertParser.extract_actual_end_time(most_recent_alert)
						
						# Create updated event with is_active=False and actual_end_date set
						updated_event = Event(
							event_key=event.event_key,
							nws_alert_id=event.nws_alert_id,
							episode_key=event.episode_key,
							event_type=event.event_type,
							hr_event_type=event.hr_event_type,
							locations=event.locations,
							start_date=event.start_date,
							expected_end_date=event.expected_end_date,
							actual_end_date=actual_end_time,
							updated_at=datetime.now(timezone.utc),
							description=event.description,
							is_active=False,
							confirmed=event.confirmed,  # Preserve confirmed status
							raw_vtec=event.raw_vtec,
							property_damage=event.property_damage,
							crops_damage=event.crops_damage,
							range_miles=event.range_miles,
							previous_ids=event.previous_ids
						)
						
						# Update the event in state
						state.update_event(updated_event)
						logger.info(f"Marked event {event.event_key} as inactive with actual_end_date={actual_end_time}")
				
				except Exception as e:
					# Log error but continue processing remaining events
					logger.error(f"Error processing event {event.event_key}: {str(e)}")
					import traceback
					logger.error(traceback.format_exc())
					continue
		
		finally:
			# Close the client
			await client.close()

