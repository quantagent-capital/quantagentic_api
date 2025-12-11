"""
Processor for creating events from new alerts.
"""
from typing import List, Dict
from app.shared_models.nws_poller_models import FilteredNWSAlert
from app.state import state
from app.services.event_service import EventService
from app.exceptions.base import ConflictError
from app.utils.datetime_utils import parse_datetime_to_utc
import logging

logger = logging.getLogger(__name__)


class EventCreationProcessor:
	"""
	Processor for handling creation of new events from alerts.
	
	Handles deduplication by selecting the most recent alert by sent_at timestamp
	and processes event creation with conflict resolution.
	"""
	
	def process(self, new_events: List[FilteredNWSAlert]) -> None:
		"""
		Process new events: deduplicate and create events.
		
		For each new event, calls EventService.create_event_from_alert.
		If one fails, logs the error and continues processing the remaining events.
		
		Handles edge case where multiple alerts with the same key exist in the batch:
		- Deduplicates by selecting most recent alert by sent_at timestamp
		- If ConflictError occurs (event already exists), check if it's a duplicate alert_id
		- If duplicate alert_id, skip it (already processed)
		- If different alert_id, treat as update (should have been caught earlier, but handle gracefully)
		
		Args:
			new_events: List of FilteredNWSAlert objects for new events
		"""
		if not new_events:
			logger.info("No new events to process")
			return
		
		logger.info(f"Processing {len(new_events)} new events")
		
		# Deduplicate alerts by key - keep the most recent one by sent_at timestamp
		deduplicated_events = self._deduplicate_by_key(new_events)
		
		if len(deduplicated_events) < len(new_events):
			logger.info(f"Deduplicated {len(new_events)} alerts to {len(deduplicated_events)} unique events by key (selected most recent by sent_at)")
		
		# Iterate through events one by one, creating each event
		for alert in deduplicated_events:
			self._create_event_from_alert(alert)
		
		logger.info(f"Finished processing {len(deduplicated_events)} new events")
	
	def _deduplicate_by_key(self, alerts: List[FilteredNWSAlert]) -> List[FilteredNWSAlert]:
		"""
		Deduplicate alerts by key, selecting the most recent by sent_at timestamp.
		
		Args:
			alerts: List of FilteredNWSAlert objects to deduplicate
			
		Returns:
			List of deduplicated FilteredNWSAlert objects
		"""
		# Group alerts by key
		alerts_by_key: Dict[str, List[FilteredNWSAlert]] = {}
		for alert in alerts:
			if alert.key not in alerts_by_key:
				alerts_by_key[alert.key] = []
			alerts_by_key[alert.key].append(alert)
		
		# For each key, choose the alert with the most recent sent_at timestamp
		deduplicated_events = []
		for key, alerts_group in alerts_by_key.items():
			if len(alerts_group) == 1:
				# Only one alert for this key, use it
				deduplicated_events.append(alerts_group[0])
			else:
				# Multiple alerts with same key - choose the most recent by sent_at
				selected_alert = self._select_most_recent_alert(alerts_group, key)
				deduplicated_events.append(selected_alert)
		
		return deduplicated_events
	
	def _select_most_recent_alert(self, alerts_group: List[FilteredNWSAlert], key: str) -> FilteredNWSAlert:
		"""
		Select the most recent alert from a group by sent_at timestamp.
		
		Args:
			alerts_group: List of alerts with the same key
			key: The event key (for logging purposes)
			
		Returns:
			The most recent FilteredNWSAlert by sent_at, or first alert if all have invalid sent_at
		"""
		most_recent_alert = None
		most_recent_sent_at = None
		
		for alert in alerts_group:
			# Parse sent_at to datetime for comparison
			sent_at_dt = None
			if alert.sent_at:
				sent_at_dt = parse_datetime_to_utc(alert.sent_at)
			
			# If sent_at is None or can't be parsed, skip this alert in favor of ones with valid sent_at
			if sent_at_dt is None:
				logger.debug(f"Alert {alert.alert_id} with key {key} has invalid/missing sent_at, skipping in favor of alerts with valid sent_at")
				continue
			
			# Compare with current most recent
			if most_recent_sent_at is None or sent_at_dt > most_recent_sent_at:
				most_recent_alert = alert
				most_recent_sent_at = sent_at_dt
		
		# If we found a valid alert with sent_at, use it
		# Otherwise, fall back to first alert (all had None/invalid sent_at)
		if most_recent_alert is not None:
			if len(alerts_group) > 1:
				logger.debug(f"Selected most recent alert {most_recent_alert.alert_id} (sent_at: {most_recent_alert.sent_at}) from {len(alerts_group)} alerts with key {key}")
			return most_recent_alert
		else:
			# All alerts had None/invalid sent_at, use first one
			logger.debug(f"All {len(alerts_group)} alerts with key {key} have invalid/missing sent_at, using first alert {alerts_group[0].alert_id}")
			return alerts_group[0]
	
	def _create_event_from_alert(self, alert: FilteredNWSAlert) -> None:
		"""
		Create an event from an alert, handling conflicts gracefully.
		
		Args:
			alert: FilteredNWSAlert to create event from
		"""
		try:
			created_event = EventService.create_event_from_alert(alert)
			logger.debug(f"Created event: `{created_event.event_key}` via service layer")
		except ConflictError as e:
			# Handle case where event was created between initial check and processing
			# This can happen when multiple alerts with same key exist in the batch
			logger.warning(f"Event with key {alert.key} already exists (likely created by duplicate alert in batch)")
			self._try_fallback_to_update(alert)
		except Exception as e:
			# Log error but continue processing remaining events
			logger.error(f"Error creating event from alert: {alert.alert_id} via service layer: {str(e)}")
			import traceback
			logger.error(traceback.format_exc())
	
	def _try_fallback_to_update(self, alert: FilteredNWSAlert) -> None:
		"""
		Attempt to fall back to updating an existing event when creation fails due to conflict.
		
		When a ConflictError occurs during event creation, this method checks if the alert
		should be treated as an update to an existing event. It handles several scenarios:
		- Event was deleted between conflict check and retrieval (skip)
		- Alert ID matches existing event or is in previous_ids (duplicate, skip)
		- Alert ID is different (treat as update)
		
		Args:
			alert: FilteredNWSAlert that caused the conflict
		"""
		# Check if this is a duplicate alert_id or should be treated as update
		existing_event = state.get_event(alert.key)
		if existing_event is None:
			# Event was deleted between check and now - log and skip
			logger.warning(f"Event {alert.key} was deleted between conflict check and retrieval, skipping")
			return
		
		# Check if this alert_id is a duplicate
		is_duplicate = (
			existing_event.nws_alert_id == alert.alert_id or
			alert.alert_id in existing_event.previous_ids
		)
		
		if is_duplicate:
			logger.debug(f"Alert {alert.alert_id} is duplicate for event {alert.key}, skipping")
		else:
			# Different alert_id - should be treated as update
			logger.info(f"Alert {alert.alert_id} for existing event {alert.key} has different alert_id, treating as update")
			try:
				updated_event = EventService.update_event_from_alert(alert)
				logger.debug(f"Updated event: `{updated_event.event_key}` via service layer")
			except Exception as update_error:
				logger.error(f"Error updating event from alert: {alert.alert_id} via service layer: {str(update_error)}")
				import traceback
				logger.error(traceback.format_exc())
