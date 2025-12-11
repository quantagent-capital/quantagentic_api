from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from app.utils.nws_event_types import NWS_WARNING_CODES
from app.exceptions import NotFoundError
from app.exceptions.base import ConflictError
from app.schemas.event import Event
from app.schemas.location import Location
from app.shared_models.nws_poller_models import FilteredNWSAlert
from app.state import state
from app.utils.datetime_utils import parse_datetime_to_utc
from app.http_client.nws_client import NWSClient
from app.utils import vtec
from app.config import settings
import asyncio
import logging

logger = logging.getLogger(__name__)


class EventService:
	"""Service layer for Event operations."""

	@staticmethod
	def create_event_from_alert(alert: FilteredNWSAlert) -> Event:
		"""
		Create an event from a FilteredNWSAlert.
		
		Args:
			alert: FilteredNWSAlert object
		
		Returns:
			Created Event object
		"""
		try:
			logger.info(f"Processing alert {alert.alert_id} with key {alert.key}")
			if state.event_exists(alert.key):
				raise ConflictError(f"Event with key: `{alert.key}` already exists, did we misclassify the alert?")
			# Set confirmed=True if certainty is "observed" (case-insensitive)
			confirmed = alert.certainty.lower() == "observed" if alert.certainty else False
			event = Event(
				event_key=alert.key,
				nws_alert_id=alert.alert_id,
				episode_key=None,
				event_type=alert.event_type,
				hr_event_type=NWS_WARNING_CODES.get(alert.event_type, "UNKNOWN"),
				locations=alert.locations,
				start_date=parse_datetime_to_utc(alert.effective) or datetime.now(timezone.utc),
				expected_end_date=parse_datetime_to_utc(alert.expected_end),
				updated_at=datetime.now(timezone.utc),
				description=f"{alert.headline or ''}\n\n{alert.description or ''}",
				is_active=True,
				confirmed=confirmed,
				raw_vtec=alert.raw_vtec,
				previous_ids=[]
			)
			state.add_event(event)
			return event
		except ConflictError as e:
			# Re - raise as callers will handle logging for this case.
			raise
		except Exception as e:
			logger.error(f"Error processing alert {alert.alert_id}: {str(e)}")
			import traceback
			logger.error(traceback.format_exc())
			raise

	@staticmethod
	def update_event_from_alert(updateable_alert: FilteredNWSAlert) -> Event:
		"""
		Update an existing event from an updateable alert.
		
		Update logic:
		- If message_type is "COR" or "UPG": Replace entire event with updateable alert metadata
		- If message_type is "CAN" or "EXP": Mark event as inactive and set actual_end_date
		- Otherwise: Merge locations, update description, update expected_end_date
		
		Args:
			existing_event: Existing Event object to update
			updateable_alert: FilteredNWSAlert with update information
		
		Returns:
			Updated Event object
		"""
		try:
			existing_event = EventService.get_event(updateable_alert.key)
			logger.info(f"Updating event {existing_event.event_key} from alert {updateable_alert.alert_id}")
			
			message_type = updateable_alert.message_type.upper()
			previous_ids = existing_event.previous_ids
			if existing_event.nws_alert_id not in previous_ids:
				previous_ids.append(existing_event.nws_alert_id)
			
			# Handle COR and UPG message types - replace entire event
			if message_type in ["COR", "UPG"]:
				logger.info(f"Message type {message_type} detected - replacing entire event")
				updated_event = EventService._replace_event_with_alert(existing_event, updateable_alert, previous_ids)
			
			# Handle CAN and EXP message types - mark as inactive
			elif message_type in ["CAN", "EXP"]:
				logger.info(f"Message type {message_type} detected, updates for this are handled via checking for completed events")
				return
			
			# Default update behavior - merge locations, update description and expected_end_date
			else:
				logger.info(f"Standard update for message type {message_type} - merging locations and updating fields")
				updated_event = EventService._merge_update_event_from_alert(existing_event, updateable_alert, previous_ids)
			
			# Update the event in state
			state.update_event(updated_event)
			logger.info(f"Successfully updated event {updated_event.event_key}")
			return updated_event
			
		except NotFoundError:
			# Re-raise NotFoundError as-is (callers will handle logging)
			raise
		except Exception as e:
			# Use alert key instead of existing_event.event_key in case get_event failed
			event_key = updateable_alert.key if 'existing_event' not in locals() else existing_event.event_key
			logger.error(f"Error updating event {event_key} from alert {updateable_alert.alert_id}: {str(e)}")
			import traceback
			logger.error(traceback.format_exc())
			raise
	
	@staticmethod
	def get_event(event_key: str) -> Optional[Event]:
		"""
		Get an event by key.
		
		Args:
			event_key: Key of event to retrieve
		
		Returns:
			Event object or None if not found
		"""

		event = state.get_event(event_key)
		if event is None:
			raise NotFoundError("Event", event_key)
		return event
	
	@staticmethod
	def has_episode(event_key: str) -> bool:
		"""
		Check if an event has an associated episode.
		
		Args:
			event_key: Key of event to check
		
		Returns:
			True if event has an episode_key, False otherwise
		"""
		# TODO: Implement has_episode logic
		event = EventService.get_event(event_key)
		if event is None:
			return False
		return event.episode_key is not None
	
	@staticmethod
	def get_events(hour_offset: Optional[int] = 72) -> List[Event]:
		"""
		Get events from state, optionally filtered by hour_offset.
		
		Filtering logic:
		- Calculate the time point: now - hour_offset hours
		- Include events where the time point falls between start_date and actual_end_date
		- If either actual_end_date or start_date is null, automatically include the event
		
		Args:
			hour_offset: Hours to look back from now. Default is 72 hours.
		
		Returns:
			List of Event objects matching the filter criteria
		"""
		all_events = state.events
		
		# If hour_offset is None or 0, return all events
		if hour_offset is None or hour_offset <= 0:
			return all_events
		
		# Calculate the time point exactly hour_offset hours ago
		current_time = datetime.now(timezone.utc)
		time_point = current_time - timedelta(hours=hour_offset)
		
		filtered_events = []
		for event in all_events:
			# If actual_end_date is null, automatically include the event
			# (start_date is required in schema, but check for safety)
			if event.actual_end_date is None or event.start_date is None:
				filtered_events.append(event)
				continue
			
			# Check if time_point falls between start_date and actual_end_date (inclusive)
			if event.start_date <= time_point <= event.actual_end_date:
				filtered_events.append(event)
		
		return filtered_events
	
	@staticmethod
	def get_active_event_counts_by_type() -> Dict[str, int]:
		"""
		Get count of active events grouped by event type.
		
		Returns:
			Dictionary mapping event_type to count of active events
		"""
		active_events = state.active_events
		counts: Dict[str, int] = {}
		
		for event in active_events:
			event_type = event.event_type
			counts[event_type] = counts.get(event_type, 0) + 1
		
		return counts
	
	@staticmethod
	def _merge_locations(existing_locations: List[Location], new_locations: List[Location]) -> List[Location]:
		"""
		Merge existing and new locations, avoiding duplicates based on ugc_code.
		
		Args:
			existing_locations: List of existing Location objects
			new_locations: List of new Location objects from updateable alert
		
		Returns:
			Combined list of locations with no duplicates
		"""
		# Get set of existing ugc_codes for quick lookup
		existing_ugc_codes = {loc.ugc_code for loc in existing_locations}
		
		# Start with existing locations
		merged_locations = list(existing_locations)
		
		# Add new locations that don't already exist
		for new_loc in new_locations:
			if new_loc.ugc_code not in existing_ugc_codes:
				merged_locations.append(new_loc)
				existing_ugc_codes.add(new_loc.ugc_code)  # Track to avoid duplicates within new_locations
		
		return merged_locations
	
	@staticmethod
	def _replace_event_with_alert(existing_event: Event, updateable_alert: FilteredNWSAlert, previous_ids: List[str]) -> Event:
		"""
		Replace entire event with updateable alert metadata.
		Used for COR and UPG message types.
		
		Args:
			existing_event: Existing Event object
			updateable_alert: FilteredNWSAlert with replacement information
			previous_ids: List of previous alert IDs
		
		Returns:
			Event object with replaced metadata
		"""
		# Set confirmed=True if certainty is "observed", otherwise preserve existing confirmed status
		confirmed = existing_event.confirmed
		if updateable_alert.certainty and updateable_alert.certainty.lower() == "observed":
			confirmed = True
		return Event(
			event_key=updateable_alert.key,
			nws_alert_id=updateable_alert.alert_id,  # Always use new alert_id
			episode_key=existing_event.episode_key,  # Preserve episode_key
			event_type=updateable_alert.event_type,
			hr_event_type=NWS_WARNING_CODES.get(updateable_alert.event_type, "UNKNOWN"),
			locations=updateable_alert.locations,
			start_date=parse_datetime_to_utc(updateable_alert.effective) or existing_event.start_date,
			expected_end_date=parse_datetime_to_utc(updateable_alert.expected_end),
			actual_end_date=existing_event.actual_end_date,  # Preserve actual_end_date unless explicitly set
			updated_at=datetime.now(timezone.utc),
			description=f"{updateable_alert.headline or ''}\n\n{updateable_alert.description or ''}",
			is_active=existing_event.is_active,  # Preserve is_active status
			confirmed=confirmed,
			raw_vtec=updateable_alert.raw_vtec,
			property_damage=existing_event.property_damage,  # Preserve these fields
			crops_damage=existing_event.crops_damage,
			range_miles=existing_event.range_miles,
			previous_ids=previous_ids
		)
	
	@staticmethod
	def _merge_update_event_from_alert(existing_event: Event, updateable_alert: FilteredNWSAlert, previous_ids: List[str]) -> Event:
		"""
		Merge locations and update description and expected_end_date.
		Default update behavior for standard message types.
		
		Args:
			existing_event: Existing Event object
			updateable_alert: FilteredNWSAlert with update information
			previous_ids: List of previous alert IDs
		
		Returns:
			Event object with merged updates
		"""
		merged_locations = EventService._merge_locations(existing_event.locations, updateable_alert.locations)
		
		# Build description from alert
		new_description = f"{updateable_alert.headline or ''}\n\n{updateable_alert.description or ''}"
		
		# Set confirmed=True if certainty is "observed", otherwise preserve existing confirmed status
		confirmed = existing_event.confirmed
		if updateable_alert.certainty and updateable_alert.certainty.lower() == "observed":
			confirmed = True
		
		return Event(
			event_key=existing_event.event_key,
			nws_alert_id=updateable_alert.alert_id,  # Always use new alert_id
			episode_key=existing_event.episode_key,
			event_type=existing_event.event_type,
			hr_event_type=existing_event.hr_event_type,
			locations=merged_locations,
			start_date=existing_event.start_date,  # Keep original start_date
			expected_end_date=parse_datetime_to_utc(updateable_alert.expected_end),
			actual_end_date=existing_event.actual_end_date,
			updated_at=datetime.now(timezone.utc),
			description=new_description,
			is_active=existing_event.is_active,
			confirmed=confirmed,
			raw_vtec=updateable_alert.raw_vtec,  # Update raw_vtec
			property_damage=existing_event.property_damage,
			crops_damage=existing_event.crops_damage,
			range_miles=existing_event.range_miles,
			previous_ids=previous_ids
		)

	@staticmethod
	def _extract_properties_from_alert(alert_data: Dict[str, Any], alert_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
		"""
		Extract properties from NWS alert response data.
		
		Handles different response formats:
		- Response with "features" array (GeoJSON FeatureCollection)
		- Response with direct "properties" (single alert)
		
		Args:
			alert_data: Alert data dictionary from NWS API
			alert_id: Optional alert ID for logging purposes
		
		Returns:
			Properties dictionary or None if not found
		"""
		# Check if this is a feature collection (features array)
		if "features" in alert_data and len(alert_data["features"]) > 0:
			feature = alert_data["features"][0]
			properties = feature.get("properties", {})
			return properties if properties else None
		
		# Check if properties are directly in the response
		elif "properties" in alert_data:
			properties = alert_data["properties"]
			return properties if properties else None
		
		# Properties not found
		else:
			alert_id_str = f" {alert_id}" if alert_id else ""
			logger.warning(f"Could not find properties in alert{alert_id_str}")
			return None

	@staticmethod
	async def _get_most_recent_alert(client: NWSClient, alert_id: str) -> Optional[Dict[str, Any]]:
		"""
		Get the most recent alert by following replacedBy links.
		
		Args:
			client: NWSClient instance
			alert_id: Initial alert ID
		
		Returns:
			Most recent alert data or None if not found
		"""
		try:
			current_alert_id = alert_id
			max_iterations = 10  # Prevent infinite loops
			iteration = 0
			
			while iteration < max_iterations:
				# Get alert by ID
				alert_data = await client.get_alert_by_id(current_alert_id)
				
				# Extract properties from alert response
				properties = EventService._extract_properties_from_alert(alert_data, current_alert_id)
				if properties is None:
					logger.warning(f"Unexpected alert structure for {current_alert_id}")
					return alert_data
				
				# Check for replacedBy property
				replaced_by = properties.get("replacedBy")
				if not replaced_by:
					# This is the most recent alert
					return alert_data
				
				# Extract alert ID from the replacedBy URL
				# Format: https://api.weather.gov/alerts/{alert_id}
				if isinstance(replaced_by, str):
					# Extract the alert ID from the URL
					if "/alerts/" in replaced_by:
						# Get everything after "/alerts/" and before any query params or fragments
						alert_id_part = replaced_by.split("/alerts/")[-1]
						# Remove query parameters and fragments if present
						current_alert_id = alert_id_part.split("?")[0].split("#")[0]
					else:
						logger.warning(f"Unexpected replacedBy format: {replaced_by}")
						return alert_data
				else:
					logger.warning(f"replacedBy is not a string: {replaced_by}")
					return alert_data
				
				iteration += 1
			
			logger.warning(f"Reached max iterations following replacedBy links for {alert_id}")
			return alert_data
			
		except Exception as e:
			logger.error(f"Error getting most recent alert for {alert_id}: {str(e)}")
			import traceback
			logger.error(traceback.format_exc())
			return None

	@staticmethod
	def _extract_actual_end_time(alert_data: Dict[str, Any]) -> Optional[datetime]:
		"""
		Extract actual end time from alert data with fallback chain:
		1. Try eventEndingTime from parameters
		2. Fallback to ends property
		3. Fallback to expires property
		4. Fallback to datetime.utcnow
		
		Args:
			alert_data: Alert data dictionary from NWS API
		
		Returns:
			datetime object in UTC or None
		"""
		try:
			# Get properties from alert data
			properties = EventService._extract_properties_from_alert(alert_data)
			if properties is None:
				logger.warning("Could not find properties in alert data")
				return datetime.now(timezone.utc)
			
			# Try eventEndingTime from parameters
			event_ending_time_list = properties.get("parameters", {}).get("eventEndingTime")
			if event_ending_time_list and len(event_ending_time_list) > 0:
				event_ending_time = parse_datetime_to_utc(event_ending_time_list[0])
				if event_ending_time:
					return event_ending_time
			
			# Fallback to ends property
			ends = properties.get("ends")
			if ends:
				ends_dt = parse_datetime_to_utc(ends)
				if ends_dt:
					return ends_dt
			
			# Fallback to expires property
			expires = properties.get("expires")
			if expires:
				expires_dt = parse_datetime_to_utc(expires)
				if expires_dt:
					return expires_dt
			
			# Final fallback to current time
			return datetime.now(timezone.utc)
			
		except Exception as e:
			logger.error(f"Error extracting actual end time: {str(e)}")
			import traceback
			logger.error(traceback.format_exc())
			return datetime.now(timezone.utc)

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
			asyncio.run(EventService._async_check_completed_events(events_to_check))
			
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
					most_recent_alert = await EventService._get_most_recent_alert(client, event.nws_alert_id)
					
					if most_recent_alert is None:
						logger.warning(f"Could not retrieve alert {event.nws_alert_id} for event {event.event_key}")
						continue
					
					# Extract properties from alert
					properties = EventService._extract_properties_from_alert(most_recent_alert, event.nws_alert_id)
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
						actual_end_time = EventService._extract_actual_end_time(most_recent_alert)
						
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


