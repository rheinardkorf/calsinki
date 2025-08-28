"""Calendar synchronization logic for Calsinki."""

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from googleapiclient.discovery import build

from .auth import GoogleAuthenticator
from .config import Config, SyncRule


@dataclass
class CalendarEvent:
    """Represents a calendar event with Calsinki sync metadata."""

    event_id: str
    summary: str
    start: datetime
    end: datetime
    description: str | None = None
    location: str | None = None
    attendees: list[dict[str, str]] | None = None
    sync_metadata: dict[str, Any] = field(default_factory=dict)
    original_event: dict[str, Any] | None = None  # Store original Google event data
    google_event_id: str | None = None  # Store Google Calendar event ID for deletion

    @classmethod
    def from_google_event(
        cls, event: dict[str, Any], source_calendar_id: str
    ) -> "CalendarEvent":
        """Create CalendarEvent from Google Calendar API event."""
        # Parse start time
        start_data = event.get("start", {})
        if "dateTime" in start_data:
            start = datetime.fromisoformat(
                start_data["dateTime"].replace("Z", "+00:00")
            )
        else:
            start = datetime.fromisoformat(start_data["date"] + "T00:00:00+00:00")

        # Parse end time
        end_data = event.get("end", {})
        if "dateTime" in start_data:
            end = datetime.fromisoformat(end_data["dateTime"].replace("Z", "+00:00"))
        else:
            end = datetime.fromisoformat(end_data["date"] + "T23:59:59+00:00")

        # Check if this event already has Calsinki metadata (to prevent loops)
        sync_metadata = {}
        if "extendedProperties" in event and "private" in event["extendedProperties"]:
            # Event already has metadata, preserve it
            sync_metadata = event["extendedProperties"]["private"]
        else:
            # Event has no metadata, create new metadata for syncing
            sync_metadata = {
                "source_calendar_id": source_calendar_id,
                "source_event_id": event["id"],
                "last_synced": datetime.now(UTC).isoformat(),
                "sync_version": 1,
            }

        return cls(
            event_id=event["id"],
            summary=event.get("summary", "No Title"),
            description=event.get("description", ""),
            start=start,
            end=end,
            location=event.get("location"),
            attendees=event.get("attendees", []),
            sync_metadata=sync_metadata,
            original_event=event,  # Store the original event data
        )

    @classmethod
    def from_destination_event(
        cls, event: dict[str, Any], calendar_id: str
    ) -> "CalendarEvent":
        """Create CalendarEvent from a destination calendar event, preserving original source metadata."""
        # Parse start time
        start_data = event.get("start", {})
        if "dateTime" in start_data:
            start = datetime.fromisoformat(
                start_data["dateTime"].replace("Z", "+00:00")
            )
        else:
            start = datetime.fromisoformat(start_data["date"] + "T00:00:00+00:00")

        # Parse end time
        end_data = event.get("end", {})
        if "dateTime" in start_data:
            end = datetime.fromisoformat(end_data["dateTime"].replace("Z", "+00:00"))
        else:
            end = datetime.fromisoformat(end_data["date"] + "T23:59:59+00:00")

        # For destination events, preserve the original sync metadata
        sync_metadata = {}
        if "extendedProperties" in event and "private" in event["extendedProperties"]:
            sync_metadata = event["extendedProperties"]["private"]

        return cls(
            event_id=event["id"],  # This is the destination event ID
            summary=event.get("summary", "No Title"),
            description=event.get("description", ""),
            start=start,
            end=end,
            location=event.get("location"),
            attendees=event.get("attendees", []),
            sync_metadata=sync_metadata,  # Preserve original metadata
            original_event=event,  # Store the original event data
        )


class CalendarSynchronizer:
    """Handles synchronization between Google Calendar accounts."""

    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)

        # Initialize Google Calendar API services for each account
        self.calendar_services: dict[str, Any] = {}
        self._initialize_services()

    def _initialize_services(self):
        """Initialize Google Calendar API services for all accounts."""
        # Load OAuth2 config once
        from .auth import load_oauth2_config

        oauth2_config = load_oauth2_config()

        if not oauth2_config:
            self.logger.error("❌ OAuth2 configuration not found")
            return

        for account in self.config.accounts:
            try:
                # Load credentials for this account
                authenticator = GoogleAuthenticator(account.name, oauth2_config)
                credentials = authenticator._load_existing_credentials()

                if credentials:
                    # Build the Calendar API service
                    service = build("calendar", "v3", credentials=credentials)
                    self.calendar_services[account.name] = service
                    self.logger.info(
                        f"✅ Initialized Calendar API service for {account.name}"
                    )
                else:
                    self.logger.warning(
                        f"⚠️  No credentials found for account {account.name}"
                    )

            except Exception as e:
                self.logger.error(
                    f"❌ Failed to initialize service for {account.name}: {e}"
                )



    def sync_rule(self, sync_rule: SyncRule, dry_run: bool = False) -> bool:
        """Synchronize a single sync rule to all its enabled destinations."""
        try:
            # Get source calendar
            source_cal = self.config.get_calendar_by_id(sync_rule.source_calendar)

            if not source_cal:
                self.logger.error(f"❌ Source calendar not found for sync rule {sync_rule.id}")
                return False

            # Get calendar service for source
            source_service = self.calendar_services.get(source_cal.account_name)

            if not source_service:
                self.logger.error(
                    f"❌ Calendar service not available for source calendar in rule {sync_rule.id}"
                )
                return False

            # Get enabled destinations
            enabled_targets = [target for target in sync_rule.destination if target.enabled]
            
            if not enabled_targets:
                self.logger.info(f"ℹ️  No enabled destinations for sync rule {sync_rule.id}")
                return True

            if dry_run:
                self.logger.info(
                    f"🔍 DRY RUN: Would sync {source_cal.name} → {len(enabled_targets)} destination(s)"
                )
                print(f"🔍 DRY RUN: Would sync {source_cal.name} → {len(enabled_targets)} destination(s)")
            else:
                self.logger.info(
                    f"🔄 Starting sync rule: {source_cal.name} → {len(enabled_targets)} destination(s)"
                )

            # Fetch events from source calendar
            source_events = self._fetch_calendar_events(
                source_service, source_cal.calendar_id
            )
            self.logger.info(f"📅 Found {len(source_events)} events in source calendar")

            total_synced = 0
            total_deleted = 0

            # Process each enabled destination
            for target in enabled_targets:
                try:
                    # Get destination calendar
                    dest_cal = self.config.get_calendar_by_id(target.calendar_id)
                    if not dest_cal:
                        self.logger.error(f"❌ Destination calendar not found: {target.calendar_id}")
                        continue

                    # Get calendar service for destination
                    dest_service = self.calendar_services.get(dest_cal.account_name)
                    if not dest_service:
                        self.logger.error(f"❌ Calendar service not available for destination: {dest_cal.account_name}")
                        continue

                    if dry_run:
                        print(f"🔍 DRY RUN: Would sync to {dest_cal.name} ({target.privacy_mode})")
                    else:
                        print(f"🔄 Syncing to {dest_cal.name} ({target.privacy_mode})")

                    # Fetch existing synced events from destination calendar
                    effective_identifier = self.config.get_effective_identifier_for_rule(sync_rule, target.calendar_id)
                    existing_synced_events = self._find_synced_events_by_search(
                        dest_service,
                        dest_cal.calendar_id,
                        source_cal.calendar_id,
                        effective_identifier,
                    )

                    print(f"🔍 Found {len(existing_synced_events)} existing synced events in {dest_cal.name}")
                    self.logger.info(
                        f"📅 Found {len(existing_synced_events)} existing synced events in destination calendar {dest_cal.name}"
                    )

                    if dry_run:
                        # In dry-run mode, simulate the sync process
                        print(f"🔍 DRY RUN: Would sync {len(source_events)} events to {dest_cal.name}")
                        print(f"🔍 DRY RUN: Would check {len(existing_synced_events)} existing events for updates/deletions")
                        
                        # Simulate the loop prevention check
                        skipped_count = 0
                        events_to_sync = []
                        
                        for event in source_events:
                            if self._is_calsinki_synced_event(event, self.config.default_identifier):
                                print(f"🔍 DRY RUN: ⏭️  Would skip '{event.summary}' - already synced by Calsinki")
                                skipped_count += 1
                            else:
                                events_to_sync.append(event)

                        if events_to_sync:
                            print(f"🔍 DRY RUN: {len(events_to_sync)} events would be synced to {dest_cal.name}")
                        if skipped_count > 0:
                            print(f"🔍 DRY RUN: {skipped_count} events would be skipped due to loop prevention")
                        
                        continue

                    # Apply privacy rules and sync to destination
                    synced_count = self._sync_events_to_destination(
                        source_events,
                        dest_service,
                        dest_cal.calendar_id,
                        target.privacy_mode,
                        target.privacy_label,
                        sync_rule,   # Pass sync_rule
                        target,      # target
                    )

                    # Handle deletions - remove events that no longer exist in source
                    print(f"🔍 Starting deletion check for {dest_cal.name}...")
                    self.logger.info(f"🔍 Starting deletion check for {dest_cal.name}...")
                    deleted_count = self._handle_deletions(
                        source_events,
                        existing_synced_events,
                        dest_service,
                        dest_cal.calendar_id,
                    )
                    print(f"🔍 Deletion check completed for {dest_cal.name}: {deleted_count} deletions")
                    self.logger.info(
                        f"🔍 Deletion check completed for {dest_cal.name}: {deleted_count} deletions"
                    )

                    total_synced += synced_count
                    total_deleted += deleted_count

                    self.logger.info(
                        f"✅ Successfully synced {synced_count} events, deleted {deleted_count} events to {dest_cal.name}"
                    )

                except Exception as e:
                    self.logger.error(f"❌ Failed to sync to destination {target.calendar_id}: {e}")
                    continue

            if dry_run:
                print(f"🔍 DRY RUN COMPLETE: Would sync {len(source_events)} events to {len(enabled_targets)} destinations")
            else:
                self.logger.info(
                    f"✅ Sync rule {sync_rule.id} completed: {total_synced} events synced, {total_deleted} events deleted across {len(enabled_targets)} destinations"
                )
                print(f"✅ Sync rule {sync_rule.id} completed: {total_synced} events synced, {total_deleted} events deleted")

            return True

        except Exception as e:
            self.logger.error(f"❌ Sync failed for rule {sync_rule.id}: {e}")
            return False

    def _fetch_calendar_events(
        self, service: Any, calendar_id: str
    ) -> list[CalendarEvent]:
        """Fetch events from a Google Calendar."""
        try:
            # First, try to get calendar info to verify access
            try:
                calendar_info = (
                    service.calendars().get(calendarId=calendar_id).execute()
                )
                self.logger.info(
                    f"📅 Accessing calendar: {calendar_info.get('summary', 'Unknown')}"
                )
            except Exception as e:
                self.logger.error(f"❌ Cannot access calendar {calendar_id}: {e}")
                return []

            # Use 30-day time range (30 days ago to 30 days in future)
            try:
                now = datetime.now(UTC)
                time_min = (now - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S.%f")[
                    :-3
                ] + "Z"
                time_max = (now + timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S.%f")[
                    :-3
                ] + "Z"

                self.logger.debug(f"🔍 Fetching events from {time_min} to {time_max}")

                events_result = (
                    service.events()
                    .list(
                        calendarId=calendar_id,
                        timeMin=time_min,
                        timeMax=time_max,
                        maxResults=1000,
                        singleEvents=True,
                    )
                    .execute()
                )

                events = events_result.get("items", [])
                self.logger.info(
                    f"📅 Found {len(events)} events in calendar {calendar_id} (time-ranged)"
                )
                return [
                    CalendarEvent.from_google_event(event, calendar_id)
                    for event in events
                ]

            except Exception as e:
                self.logger.error(f"❌ Events request failed: {e}")

                # Fallback: try without time range but with higher limit
                try:
                    events_result = (
                        service.events()
                        .list(calendarId=calendar_id, maxResults=1000)
                        .execute()
                    )

                    events = events_result.get("items", [])
                    self.logger.info(f"📅 Found {len(events)} events (no time filter)")
                    return [
                        CalendarEvent.from_google_event(event, calendar_id)
                        for event in events
                    ]

                except Exception as e2:
                    self.logger.error(
                        f"❌ Events request with minimal parameters also failed: {e2}"
                    )
                    return []

        except Exception as e:
            self.logger.error(
                f"❌ Failed to fetch events from calendar {calendar_id}: {e}"
            )
            return []

    def _sync_events_to_destination(
        self,
        source_events: list[CalendarEvent],
        dest_service: Any,
        dest_calendar_id: str,
        privacy_mode: str,
        privacy_label: str = "Busy",
        sync_rule: SyncRule = None,
        target: Any = None,
    ) -> int:
        """Sync events to destination calendar with privacy rules."""
        synced_count = 0

        for event in source_events:
            try:
                # Check Google Calendar event visibility to override privacy mode
                effective_privacy_mode = self._get_effective_privacy_mode(
                    event, privacy_mode
                )

                # Apply privacy rules
                source_cal = self.config.get_calendar_by_id(
                    event.sync_metadata["source_calendar_id"]
                )
                source_cal_name = source_cal.name if source_cal else "Unknown Calendar"

                # Get the effective identifier for this sync operation
                if sync_rule and target:
                    effective_identifier = self.config.get_effective_identifier_for_rule(sync_rule, target.calendar_id)
                else:
                    effective_identifier = "calsinki_synced"
                
                # Get the instance-level identifier (without sync pair suffix)
                instance_identifier = getattr(self.config, "default_identifier", "calsinki") or "calsinki"

                # Check if this source event is already a Calsinki-synced event to prevent loops
                if self._is_calsinki_synced_event(event, instance_identifier):
                    skip_msg = f"⏭️  Skipping {event.summary} - already synced by Calsinki (prevents bi-directional sync loops)"
                    self.logger.info(skip_msg)
                    continue
                
                # Debug: Log what metadata the event has
                self.logger.debug(f"Event '{event.summary}' metadata: {event.sync_metadata}")

                # Update the last_synced timestamp for this sync operation
                event.sync_metadata["last_synced"] = datetime.now(UTC).isoformat()
                
                # Increment sync count
                current_sync_count = event.sync_metadata.get("sync_count", 0)
                event.sync_metadata["sync_count"] = current_sync_count + 1

                # Get privacy rule settings from target
                show_time = target.show_time if target else False
                title_prefix = target.title_prefix if target else ""
                title_suffix = target.title_suffix if target else ""
                event_color = target.event_color if target else ""

                synced_event = self._apply_privacy_rules(
                    event,
                    effective_privacy_mode,
                    source_cal_name,
                    privacy_label,
                    show_time,
                    effective_identifier,
                    instance_identifier,
                    title_prefix,
                    title_suffix,
                    event_color,
                )

                # Check if event already exists in destination
                existing_event = self._find_existing_event(
                    dest_service, dest_calendar_id, event
                )

                if existing_event:
                    # Update existing event
                    self._update_event(
                        dest_service,
                        dest_calendar_id,
                        existing_event["id"],
                        synced_event,
                    )
                    self.logger.debug(f"🔄 Updated event: {event.summary}")
                else:
                    # Create new event
                    self._create_event(dest_service, dest_calendar_id, synced_event)
                    self.logger.debug(f"➕ Created event: {event.summary}")

                synced_count += 1

            except Exception as e:
                self.logger.error(f"❌ Failed to sync event {event.summary}: {e}")

        return synced_count

    def _apply_privacy_rules(
        self,
        event: CalendarEvent,
        privacy_mode: str,
        source_calendar_name: str = None,
        privacy_label: str = "Busy",
        show_time: bool = False,
        identifier: str = "calsinki",
        instance_identifier: str = "calsinki",
        title_prefix: str = "",
        title_suffix: str = "",
        event_color: str = "",
    ) -> dict[str, Any]:
        """Apply privacy rules to an event."""
        # Format dates properly for Google Calendar API
        start_data = {}
        end_data = {}

        if (
            event.start.hour == 0
            and event.start.minute == 0
            and event.start.second == 0
        ):
            # All-day event
            start_data = {"date": event.start.date().isoformat()}
            end_data = {"date": event.end.date().isoformat()}
        else:
            # Timed event
            start_data = {"dateTime": event.start.isoformat()}
            end_data = {"dateTime": event.end.isoformat()}

        # Create Calsinki footer
        calsinki_footer = f"\n\n---\nEvent added by {instance_identifier.replace('_', ' ').title()} from {source_calendar_name or 'Unknown'} calendar."

        # Create summary with or without time
        if show_time:
            summary = f"{privacy_label} - {event.start.strftime('%H:%M')}"
        else:
            summary = privacy_label

        # Create extended properties with both identifier types
        extended_properties = {
            "private": {
                **event.sync_metadata,
                f"{instance_identifier}_synced": "true",  # Instance-level: "mybrand_synced=true"
                identifier: "true",  # Sync pair-level: "mybrand_demo_sync_synced=true"
                "last_sync_human": datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC"),  # Human-readable timestamp
                "sync_count": event.sync_metadata.get("sync_count", 1),  # Number of times this event has been synced
            }
        }

        if privacy_mode == "public":
            # Keep original event details
            description = (
                event.description + calsinki_footer
                if event.description
                else calsinki_footer
            )

            # Apply prefix and suffix to summary
            summary = event.summary
            if title_prefix:
                summary = f"{title_prefix} {summary}"
            if title_suffix:
                summary = f"{summary} {title_suffix}"

            # Build event data
            event_data = {
                "summary": summary,
                "description": description,
                "start": start_data,
                "end": end_data,
                "location": event.location,
                "attendees": event.attendees,
                "extendedProperties": extended_properties,
            }
            
            # Add color if specified
            if event_color:
                event_data["colorId"] = event_color
                
            return event_data
        elif privacy_mode == "private":
            # Remove ALL identifiable details - completely anonymous
            description = calsinki_footer

            # Apply prefix and suffix to summary
            if title_prefix:
                summary = f"{title_prefix} {summary}"
            if title_suffix:
                summary = f"{summary} {title_suffix}"

            # Build event data
            event_data = {
                "summary": summary,
                "description": description,
                "start": start_data,
                "end": end_data,
                "extendedProperties": extended_properties,
            }
            
            # Add color if specified
            if event_color:
                event_data["colorId"] = event_color
                
            return event_data
        else:
            # Default to public for unknown modes
            self.logger.warning(
                f"⚠️  Unknown privacy mode '{privacy_mode}', defaulting to 'public'"
            )
            return self._apply_privacy_rules(
                event,
                "public",
                source_calendar_name,
                privacy_label,
                show_time,
                identifier,
                instance_identifier,
                title_prefix,
                title_suffix,
                event_color,
            )

    def _find_existing_event(
        self, service: Any, calendar_id: str, source_event: CalendarEvent
    ) -> dict[str, Any] | None:
        """Find existing event in destination calendar by checking sync metadata."""
        try:
            # Search for events with the same source event ID, regardless of time
            # This allows us to find events even when the time has changed
            source_event_id = source_event.event_id
            source_calendar_id = source_event.sync_metadata["source_calendar_id"]
            
            # Search for events with the source event ID in their metadata
            # We'll search in a broader time range to catch events that may have moved
            # Search in a wider time range (e.g., ±24 hours) to catch moved events
            time_min = (source_event.start - timedelta(hours=24)).isoformat()
            time_max = (source_event.end + timedelta(hours=24)).isoformat()
            
            events_result = (
                service.events()
                .list(
                    calendarId=calendar_id,
                    timeMin=time_min,
                    timeMax=time_max,
                    singleEvents=True,
                    maxResults=100,  # Limit results to avoid performance issues
                )
                .execute()
            )

            events = events_result.get("items", [])

            # Check if any event has matching sync metadata
            for event in events:
                if (
                    "extendedProperties" in event
                    and "private" in event["extendedProperties"]
                ):
                    metadata = event["extendedProperties"]["private"]
                    if (
                        metadata.get("source_event_id") == source_event_id
                        and metadata.get("source_calendar_id") == source_calendar_id
                    ):
                        self.logger.info(f"✅ Found existing event to update: {event.get('summary', 'Unknown')} (ID: {event.get('id', 'Unknown')})")
                        return event

            self.logger.info(f"ℹ️  No existing event found for source event {source_event_id}")
            return None

        except Exception as e:
            self.logger.error(f"❌ Failed to search for existing event: {e}")
            return None

    def _create_event(self, service: Any, calendar_id: str, event_data: dict[str, Any]):
        """Create a new event in the destination calendar."""
        service.events().insert(calendarId=calendar_id, body=event_data).execute()

    def _update_event(
        self, service: Any, calendar_id: str, event_id: str, event_data: dict[str, Any]
    ):
        """Update an existing event in the destination calendar."""
        service.events().update(
            calendarId=calendar_id, eventId=event_id, body=event_data
        ).execute()

    def _get_effective_privacy_mode(
        self, event: CalendarEvent, configured_privacy_mode: str
    ) -> str:
        """Determine effective privacy mode based on Google Calendar event visibility."""
        # Check if the original Google event has visibility settings
        if hasattr(event, "original_event") and event.original_event:
            visibility = event.original_event.get("visibility", "default")

            if visibility == "public":
                # Public events should preserve details regardless of configured mode
                if configured_privacy_mode != "public":
                    self.logger.info(
                        f"🔓 Event '{event.summary}' is public - overriding privacy mode from '{configured_privacy_mode}' to 'public'"
                    )
                return "public"
            elif visibility == "private":
                # Private events should strip details regardless of configured mode
                if configured_privacy_mode != "private":
                    self.logger.info(
                        f"🔒 Event '{event.summary}' is private - overriding privacy mode from '{configured_privacy_mode}' to 'private'"
                    )
                return "private"
            elif visibility == "default":
                # Default visibility - use configured privacy mode
                return configured_privacy_mode
        else:
            # If we don't have the original event data, use configured mode
            return configured_privacy_mode

        return configured_privacy_mode

    def _is_calsinki_synced_event(self, event: CalendarEvent, instance_identifier: str) -> bool:
        """
        Check if an event is already a Calsinki-synced event to prevent bi-directional sync loops.
        
        Args:
            event: The CalendarEvent to check
            instance_identifier: The instance identifier (e.g., "calsinki", "my_brand")
            
        Returns:
            True if the event is already synced by Calsinki, False otherwise
        """
        # Check the original Google Calendar event's extended properties
        if hasattr(event, 'original_event') and event.original_event:
            original_event = event.original_event
            
            # Check if the event has extended properties with Calsinki identifiers
            if "extendedProperties" in original_event and "private" in original_event["extendedProperties"]:
                private_props = original_event["extendedProperties"]["private"]
                
                # Check for the instance-level identifier (e.g., "calsinki_synced=true")
                instance_synced_key = f"{instance_identifier}_synced"
                if instance_synced_key in private_props and private_props[instance_synced_key] == "true":
                    return True
                    
                # Check for any sync pair identifier (e.g., "calsinki_demo_to_personal_synced=true")
                for key in private_props.keys():
                    if key.endswith("_synced") and private_props[key] == "true":
                        return True
        
        return False

    def _fetch_synced_events(
        self, service: Any, calendar_id: str, source_calendar_id: str
    ) -> list[dict[str, Any]]:
        """Fetch existing synced events from destination calendar."""
        print(f"🔍 _fetch_synced_events called with calendar_id: {calendar_id}")
        print(f"🔍 Looking for events from source_calendar_id: {source_calendar_id}")

        try:
            self.logger.info(f"🔍 Fetching synced events from calendar {calendar_id}")
            self.logger.info(
                f"🔍 Looking for events synced from source calendar {source_calendar_id}"
            )

            # Try with time range first (same as sync functionality)
            try:
                from datetime import datetime, timedelta

                now = datetime.now(UTC)
                time_min = (now - timedelta(days=30)).isoformat() + "Z"
                time_max = (now + timedelta(days=30)).isoformat() + "Z"

                print(f"🔍 Approach 1: Searching events from {time_min} to {time_max}")

                events_result = (
                    service.events()
                    .list(
                        calendarId=calendar_id,
                        timeMin=time_min,
                        timeMax=time_max,
                        maxResults=100,
                        singleEvents=True,
                    )
                    .execute()
                )

                events = events_result.get("items", [])
                print(f"🔍 API returned {len(events)} total events in time range")

            except Exception as e:
                print(f"❌ Approach 1 failed: {e}")

                # Fallback: try without time range but with reasonable limit
                try:
                    print("🔍 Approach 2: Searching without time range")
                    events_result = (
                        service.events()
                        .list(
                            calendarId=calendar_id,
                            maxResults=500,  # Higher limit since no time filter
                            singleEvents=True,
                        )
                        .execute()
                    )

                    events = events_result.get("items", [])
                    print(
                        f"🔍 API returned {len(events)} total events without time range"
                    )

                except Exception as e2:
                    print(f"❌ Approach 2 failed: {e2}")
                    events = []

            if not events:
                print("❌ Could not fetch any events")
                return []

            self.logger.info(
                f"📅 Found {len(events)} total events in destination calendar"
            )

            # Filter for events that were synced from this source calendar
            synced_events = []
            for event in events:
                if (
                    "extendedProperties" in event
                    and "private" in event["extendedProperties"]
                ):
                    metadata = event["extendedProperties"]["private"]
                    event_source_cal = metadata.get("source_calendar_id")
                    if event_source_cal == source_calendar_id:
                        synced_events.append(event)
                        print(
                            f"✅ Found synced event: {event.get('summary', 'Unknown')} from {event_source_cal}"
                        )
                        self.logger.info(
                            f"✅ Found synced event: {event.get('summary', 'Unknown')} from {event_source_cal}"
                        )
                    else:
                        print(
                            f"🔍 Event {event.get('summary', 'Unknown')} has different source: {event_source_cal}"
                        )
                        self.logger.debug(
                            f"🔍 Event {event.get('summary', 'Unknown')} has different source: {event_source_cal}"
                        )
                else:
                    print(
                        f"🔍 Event {event.get('summary', 'Unknown')} has no extended properties"
                    )
                    self.logger.debug(
                        f"🔍 Event {event.get('summary', 'Unknown')} has no extended properties"
                    )

            print(f"🔍 Total synced events found: {len(synced_events)}")
            self.logger.info(
                f"📅 Found {len(synced_events)} synced events from source calendar {source_calendar_id}"
            )
            return synced_events

        except Exception as e:
            print(f"❌ Error in _fetch_synced_events: {e}")
            self.logger.error(
                f"❌ Failed to fetch synced events from calendar {calendar_id}: {e}"
            )
            # Return empty list on error - this means we won't be able to handle deletions
            # but the sync will still work for creating/updating events
            return []

    def _handle_deletions(
        self,
        source_events: list[CalendarEvent],
        existing_synced_events: list[CalendarEvent],
        dest_service: Any,
        dest_calendar_id: str,
    ) -> int:
        """Handle deletion of events that no longer exist in source calendar."""
        deleted_count = 0

        self.logger.info(
            f"🔍 Checking for deletions: {len(source_events)} source events, {len(existing_synced_events)} existing synced events"
        )

        # Create a set of source event IDs for fast lookup
        source_event_ids = {event.event_id for event in source_events}
        self.logger.info(f"📋 Source event IDs: {source_event_ids}")

        for synced_event in existing_synced_events:
            try:
                # Get the source event ID from sync metadata
                source_event_id = synced_event.sync_metadata.get("source_event_id")
                event_summary = synced_event.summary

                self.logger.info(
                    f"🔍 Checking synced event '{event_summary}' with source ID: {source_event_id}"
                )
                self.logger.info(
                    f"🔍 Source event ID '{source_event_id}' in source_event_ids: {source_event_id in source_event_ids}"
                )

                if source_event_id and source_event_id not in source_event_ids:
                    # This event no longer exists in source - delete it
                    self.logger.info(
                        f"🗑️  Deleting event '{event_summary}' - no longer exists in source"
                    )

                    # We need to get the Google Calendar event ID to delete it
                    # The CalendarEvent object should have the original event ID
                    if hasattr(synced_event, "google_event_id"):
                        event_id = synced_event.google_event_id
                    else:
                        # Fallback: try to get from sync metadata
                        event_id = synced_event.sync_metadata.get("source_event_id")

                    if event_id:
                        dest_service.events().delete(
                            calendarId=dest_calendar_id, eventId=event_id
                        ).execute()
                        print(f"🗑️  Successfully deleted event '{event_summary}'")
                        self.logger.info(
                            f"✅ Successfully deleted event '{event_summary}'"
                        )
                    else:
                        print(
                            f"⚠️  Could not delete event '{event_summary}' - missing event ID"
                        )
                        self.logger.warning(
                            f"⚠️  Could not delete event '{event_summary}' - missing event ID"
                        )

                    deleted_count += 1
                    self.logger.info(
                        f"✅ Successfully identified event '{event_summary}' for deletion"
                    )
                else:
                    self.logger.info(
                        f"✅ Event '{event_summary}' still exists in source, keeping it"
                    )

            except Exception as e:
                self.logger.error(
                    f"❌ Failed to process event {synced_event.summary}: {e}"
                )

        self.logger.info(
            f"🗑️  Deletion check complete: {deleted_count} events identified for deletion"
        )
        return deleted_count

    def _find_synced_events_by_search(
        self,
        service: Any,
        calendar_id: str,
        source_calendar_id: str,
        identifier: str = "calsinki",
    ) -> list[CalendarEvent]:
        """Find synced events by searching for the generated identifier and filtering by source_calendar_id."""
        try:
            self.logger.info(
                f"🔍 Searching for events synced from calendar {source_calendar_id} in calendar {calendar_id}"
            )

            # Search for events with the generated identifier (e.g., "calsinki_demo_to_personal_synced=true")
            search_property = f"{identifier}=true"

            events_result = (
                service.events()
                .list(
                    calendarId=calendar_id,
                    privateExtendedProperty=search_property,
                    maxResults=100,
                    singleEvents=True,
                )
                .execute()
            )

            events = events_result.get("items", [])
            self.logger.info(f"📅 Found {len(events)} events with {identifier}=true")

            # Filter for events from this specific source calendar
            synced_events = []
            for event in events:
                if (
                    "extendedProperties" in event
                    and "private" in event["extendedProperties"]
                ):
                    metadata = event["extendedProperties"]["private"]
                    if metadata.get("source_calendar_id") == source_calendar_id:
                        # Convert to CalendarEvent object using the destination event method
                        calendar_event = CalendarEvent.from_destination_event(
                            event, calendar_id
                        )
                        # Store the Google Calendar event ID for deletion
                        calendar_event.google_event_id = event["id"]
                        synced_events.append(calendar_event)
                        self.logger.info(
                            f"✅ Found synced event: {event.get('summary', 'Unknown')} from {source_calendar_id}"
                        )

            self.logger.info(
                f"📅 Found {len(synced_events)} synced events from source calendar {source_calendar_id}"
            )
            return synced_events

        except Exception as e:
            self.logger.error(
                f"❌ Failed to search for synced events in calendar {calendar_id}: {e}"
            )
            return []
