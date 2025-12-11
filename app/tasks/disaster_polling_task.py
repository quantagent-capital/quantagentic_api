"""
Celery task for disaster polling agent.
"""
from typing import Any, List, Tuple
from datetime import datetime, timezone
from app.celery_app import celery_app
from app.schemas.location import Location
from app.shared_models.nws_poller_models import ClassifiedAlertsOutput, FilteredNWSAlert
from app.pollers.nws_polling_tool import NWSConfirmedEventsPoller
from app.state import state
from app.services.event_service import EventService
import logging

logger = logging.getLogger(__name__)



@celery_app.task(name="app.tasks.disaster_polling_task", bind=True, max_retries=3)
def disaster_polling_task(self):
	"""
	Celery task that runs the disaster polling agent every 5 minutes.
	
	Returns:
		Execution result
	"""
	logger.info("=" * 80)
	logger.info("DISASTER POLLING TASK STARTED")
	logger.info("=" * 80)
	
	try:
		logger.info("Polling NWS API for active alerts...")
		polling_tool = NWSConfirmedEventsPoller()
		filtered_alerts = polling_tool.poll()
		logger.info(f"Retrieved {len(filtered_alerts)} filtered alerts")

		# We are looking for observed events, thus, these typically come in as "updates" from the NWS API.
		# Thus, if we don't have the event, then it is new to us.
		alerts_for_non_existing_events, alerts_for_existing_events = _separate_alerts_for_existing_events(filtered_alerts)

		# For alerts that link to existing events, check if they need updates or are duplicates
		alerts_for_updateable_events = _filter_out_preprocessed_alerts(alerts_for_existing_events)
	
		_process_new_events(alerts_for_non_existing_events)
		_process_updateable_events(alerts_for_updateable_events)
		_check_completed_events()
	
	except Exception as e:
		logger.error("=" * 80)
		logger.error(f"Disaster polling task FAILED: {str(e)}")
		logger.error(f"Exception type: {type(e).__name__}")
		logger.error("Full traceback:")
		import traceback
		logger.error(traceback.format_exc())
		logger.error("=" * 80)
		# Retry with exponential backoff
		raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))

@staticmethod
def _separate_alerts_for_existing_events(alerts: List[FilteredNWSAlert]) -> Tuple[List[FilteredNWSAlert], List[FilteredNWSAlert]]:
	"""
	Filter alerts into non-existing and existing event alerts.
	Args:
		alerts: List of FilteredNWSAlert objects to filter
	Returns:
		Tuple of lists: (non-existing event alerts, existing event alerts)
	"""
	non_existing_alerts_for_events = []
	existing_alerts_for_events = []
	for alert in alerts:
		if not state.event_exists(alert.key):
			non_existing_alerts_for_events.append(alert)
		else:
			existing_alerts_for_events.append(alert)
		
	return (non_existing_alerts_for_events, existing_alerts_for_events)

@staticmethod
def _filter_out_preprocessed_alerts(alerts_for_existing_events: List[FilteredNWSAlert]) -> List[FilteredNWSAlert]:
	"""
	Identify which existing events need to be updated vs which are duplicates.
	
	For each alert that matches an existing event key:
	- Get the matching event from state
	- Check if alert.alert_id matches matching_event.nws_alert_id (duplicate)
	- Check if alert.alert_id is in matching_event.previous_ids (duplicate)
	- If neither match, the alert needs to be updated (add to updateable list)
	- If either matches, it's a duplicate (discard)
	
	Args:
		alerts_for_existing_events: List of FilteredNWSAlert objects that match existing event keys
		
	Returns:
		List of FilteredNWSAlert objects that are useable for updating existing events (not duplicates)
	"""
	useable_alerts = []
	
	for alert in alerts_for_existing_events:
		matching_event = state.get_event(alert.key)
		if matching_event is None:
			# This shouldn't happen if event_exists returned True, but handle gracefully
			logger.warning(f"Event with key {alert.key} was marked as existing but couldn't be retrieved from state")
			continue
		
		# Check if this alert_id is a duplicate
		is_duplicate = (
			matching_event.nws_alert_id == alert.alert_id or
			alert.alert_id in matching_event.previous_ids
		)
		
		if is_duplicate:
			# Same alert ID or in previous_ids means this is a duplicate, discard it
			logger.debug(f"Discarding duplicate alert {alert.alert_id} for event key {alert.key}")
		else:
			# Different alert ID and not in previous_ids means this is an update
			useable_alerts.append(alert)
	
	return useable_alerts

@staticmethod
def _process_new_events(new_events: List[FilteredNWSAlert]):
	"""
	Process new events: iterate through and create events one by one.
	
	For each new event, calls EventService.create_event_from_alert.
	If one fails, logs the error and continues processing the remaining events.
	
	Args:
		new_events: List of FilteredNWSAlert objects for new events
	"""
	if not new_events:
		logger.info("No new events to process")
		return
	
	logger.info(f"Processing {len(new_events)} new events")

	# Iterate through events one by one, creating each event
	for alert in new_events:
		try:
			created_event = EventService.create_event_from_alert(alert)
			logger.debug(f"Created event: `{created_event.event_key}` via service layer")
		except Exception as e:
			# Log error but continue processing remaining events
			logger.error(f"Error creating event from alert: {alert.alert_id} via service layer: {str(e)}")
			import traceback
			logger.error(traceback.format_exc())
	
	logger.info(f"Finished processing {len(new_events)} new events")

@staticmethod
def _process_updateable_events(updateable_events: List[FilteredNWSAlert]):
	"""
	Process updateable events: iterate through and update events one by one.
	
	Args:
		updateable_events: List of FilteredNWSAlert objects for updateable events
	"""
	if not updateable_events:
		logger.info("No updateable events to process")
		return

	logger.info(f"Processing {len(updateable_events)} updateable events")

	# Iterate through events one by one, updating each event
	for alert in updateable_events:
		try:
			updated_event = EventService.update_event_from_alert(alert)
			logger.debug(f"Updated event: `{updated_event.event_key}` via service layer")
		except Exception as e:
			# Log error but continue processing remaining events
			logger.error(f"Error updating event from alert: {alert.alert_id} via service layer: {str(e)}")
			import traceback
			logger.error(traceback.format_exc())

@staticmethod
def _check_completed_events():
	"""
	Check for completed events that should be marked as inactive.
	
	Calls EventService.check_completed_events to perform the check.
	"""
	try:
		logger.info("Checking for completed events...")
		EventService.check_completed_events()
		logger.info("Finished checking for completed events")
	except Exception as e:
		# Log error but don't fail the entire task
		logger.error(f"Error checking completed events: {str(e)}")
		import traceback
		logger.error(traceback.format_exc())