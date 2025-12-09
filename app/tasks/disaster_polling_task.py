"""
Celery task for disaster polling agent.
"""
from typing import List
from datetime import datetime, timezone
from app.celery_app import celery_app
from app.schemas.location import Location
from app.shared_models.nws_poller_models import ClassifiedAlertsOutput, FilteredNWSAlert
from app.crews.tools.nws_polling_tool import NWSPollingTool
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
		polling_tool = NWSPollingTool()
		filtered_alerts = polling_tool.poll()
		logger.info(f"Retrieved {len(filtered_alerts)} filtered alerts")

		# Filter out duplicate alerts (alerts that already exist in state)
		non_existing_events = _filter_existing_events(filtered_alerts)
		non_existing_episodes = []
		logger.info(f"Found {len(non_existing_events)} non-existing EVENTS")

		# Classify alerts into new/updated events/episodes
		classified_output = _classify_message_type(non_existing_events, non_existing_episodes)
		logger.info(f"Classified alerts: {classified_output.total_classified} total")
		logger.info(f"  - New events: {len(classified_output.new_events)}")
		logger.info(f"  - Updated events: {len(classified_output.updated_events)}")
		logger.info(f"  - New episodes: {len(classified_output.new_episodes)}")
		logger.info(f"  - Updated episodes: {len(classified_output.updated_episodes)}")

		# Process new events - check for duplicates and make non-blocking calls
		_process_new_events(classified_output.new_events)

		logger.info("=" * 80)
		logger.info("DISASTER POLLING TASK STARTED")
		logger.info("=" * 80)
		
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
def _filter_existing_events(alerts: List[FilteredNWSAlert]) -> List[FilteredNWSAlert]:
	"""
	Filter out alerts that already exist in state.
	"""
	# Use the state.event_exists for each alert.key
	non_existing_events = []
	for alert in alerts:
		if not state.event_exists(alert.key):
			non_existing_events.append(alert)
		
	return non_existing_events

@staticmethod
def _filter_existing_episodes(alerts: List[FilteredNWSAlert]) -> List[FilteredNWSAlert]:
	"""
	Filter out alerts that already exist in state.
	"""
	existing_episode_keys = {episode.episode_key for episode in state.active_episodes}
	return [alert for alert in alerts if alert.key not in existing_episode_keys and alert.is_watch]

@staticmethod
def _classify_message_type(non_existing_events: List[FilteredNWSAlert], non_existing_episodes: List[FilteredNWSAlert]) -> ClassifiedAlertsOutput:
	"""
	Classify alerts into new/updated events/episodes based on message type and watch/warning status.
	Duplicate alerts are skipped in this method.
	
	Classification rules:
	- UPDATE message types: ['CON', 'EXT', 'EXA', 'EXB']
	- CREATE message types: ['NEW', 'UPG']
	- WATCHES = EPISODES
	- WARNINGS = EVENTS
	
	Args:
		alerts: List of FilteredNWSAlert objects to classify
		
	Returns:
		ClassifiedAlertsOutput with alerts categorized into four groups
	"""
	UPDATE_MESSAGE_TYPES = ['CON', 'EXT', 'EXA', 'EXB']
	CREATE_MESSAGE_TYPES = ['NEW', 'UPG']
	
	new_events = []
	updated_events = []
	new_episodes = []
	updated_episodes = []
	
	for alert in non_existing_events:
		if alert.message_type in CREATE_MESSAGE_TYPES:
			new_events.append(alert)
		elif alert.message_type in UPDATE_MESSAGE_TYPES:
			updated_events.append(alert)
	for alert in non_existing_episodes:
		if alert.message_type in CREATE_MESSAGE_TYPES:
			new_episodes.append(alert)
		elif alert.message_type in UPDATE_MESSAGE_TYPES:
			updated_episodes.append(alert)
	
	total_classified = len(new_events) + len(updated_events) + len(new_episodes) + len(updated_episodes)
	
	return ClassifiedAlertsOutput(
		new_events=new_events,
		updated_events=updated_events,
		new_episodes=new_episodes,
		updated_episodes=updated_episodes,
		total_classified=total_classified
	)

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

