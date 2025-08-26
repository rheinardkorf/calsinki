"""Calendar synchronization logic for Calsinki."""

import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

from .config import Config, SyncPair, Calendar
from .auth import GoogleAuthenticator


@dataclass
class CalendarEvent:
    """Represents a calendar event with sync metadata."""
    event_id: str
    summary: str
    description: str
    start: datetime
    end: datetime
    location: Optional[str]
    attendees: List[Dict[str, str]]
    sync_metadata: Dict[str, Any]
    original_event: Optional[Dict[str, Any]] = None  # Store original Google event data
    
    @classmethod
    def from_google_event(cls, event: Dict[str, Any], source_calendar_id: str) -> 'CalendarEvent':
        """Create CalendarEvent from Google Calendar API event."""
        # Parse start time
        start_data = event.get('start', {})
        if 'dateTime' in start_data:
            start = datetime.fromisoformat(start_data['dateTime'].replace('Z', '+00:00'))
        else:
            start = datetime.fromisoformat(start_data['date'] + 'T00:00:00+00:00')
        
        # Parse end time
        end_data = event.get('end', {})
        if 'dateTime' in end_data:
            end = datetime.fromisoformat(end_data['dateTime'].replace('Z', '+00:00'))
        else:
            end = datetime.fromisoformat(end_data['date'] + 'T23:59:59+00:00')
        
        # Extract sync metadata
        sync_metadata = {
            'source_calendar_id': source_calendar_id,
            'source_event_id': event['id'],
            'last_synced': datetime.now(timezone.utc).isoformat(),
            'sync_version': 1
        }
        
        return cls(
            event_id=event['id'],
            summary=event.get('summary', 'No Title'),
            description=event.get('description', ''),
            start=start,
            end=end,
            location=event.get('location'),
            attendees=event.get('attendees', []),
            sync_metadata=sync_metadata,
            original_event=event  # Store the original event data
        )


class CalendarSynchronizer:
    """Handles synchronization between Google Calendar accounts."""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize Google Calendar API services for each account
        self.calendar_services: Dict[str, Any] = {}
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
                    service = build('calendar', 'v3', credentials=credentials)
                    self.calendar_services[account.name] = service
                    self.logger.info(f"✅ Initialized Calendar API service for {account.name}")
                else:
                    self.logger.warning(f"⚠️  No credentials found for account {account.name}")
                    
            except Exception as e:
                self.logger.error(f"❌ Failed to initialize service for {account.name}: {e}")
    
    def sync_pair(self, sync_pair: SyncPair) -> bool:
        """Synchronize a single sync pair."""
        try:
            # Get source and destination calendars
            source_cal = self.config.get_calendar_by_id(sync_pair.source_calendar)
            dest_cal = self.config.get_calendar_by_id(sync_pair.destination_calendar)
            
            if not source_cal or not dest_cal:
                self.logger.error(f"❌ Calendar not found for sync pair {sync_pair.id}")
                return False
            
            # Get calendar services
            source_service = self.calendar_services.get(source_cal.account_name)
            dest_service = self.calendar_services.get(dest_cal.account_name)
            
            if not source_service or not dest_service:
                self.logger.error(f"❌ Calendar service not available for sync pair {sync_pair.id}")
                return False
            
            self.logger.info(f"🔄 Starting sync: {source_cal.name} → {dest_cal.name}")
            
            # Fetch events from source calendar
            source_events = self._fetch_calendar_events(source_service, source_cal.calendar_id)
            self.logger.info(f"📅 Found {len(source_events)} events in source calendar")
            
            # Apply privacy rules and sync to destination
            synced_count = self._sync_events_to_destination(
                source_events, dest_service, dest_cal.calendar_id, sync_pair.privacy_mode, sync_pair.privacy_label, sync_pair
            )
            
            self.logger.info(f"✅ Successfully synced {synced_count} events")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Sync failed for pair {sync_pair.id}: {e}")
            return False
    
    def _fetch_calendar_events(self, service: Any, calendar_id: str) -> List[CalendarEvent]:
        """Fetch events from a Google Calendar."""
        try:
            # First, try to get calendar info to verify access
            try:
                calendar_info = service.calendars().get(calendarId=calendar_id).execute()
                self.logger.info(f"📅 Accessing calendar: {calendar_info.get('summary', 'Unknown')}")
            except Exception as e:
                self.logger.error(f"❌ Cannot access calendar {calendar_id}: {e}")
                return []
            
            # Get events from the last 30 days and next 30 days
            now = datetime.now(timezone.utc)
            time_min = (now - timedelta(days=30)).isoformat() + 'Z'
            time_max = (now + timedelta(days=30)).isoformat() + 'Z'
            
            self.logger.debug(f"🔍 Fetching events from {time_min} to {time_max}")
            
            # Try a simpler events request first
            try:
                events_result = service.events().list(
                    calendarId=calendar_id,
                    maxResults=10,  # Limit results for testing
                    singleEvents=True
                ).execute()
                
                events = events_result.get('items', [])
                self.logger.info(f"📅 Found {len(events)} events in calendar {calendar_id}")
                return [CalendarEvent.from_google_event(event, calendar_id) for event in events]
                
            except Exception as e:
                self.logger.error(f"❌ Simple events request failed: {e}")
                
                # Try without any time parameters
                try:
                    events_result = service.events().list(
                        calendarId=calendar_id,
                        maxResults=5
                    ).execute()
                    
                    events = events_result.get('items', [])
                    self.logger.info(f"📅 Found {len(events)} events (no time filter)")
                    return [CalendarEvent.from_google_event(event, calendar_id) for event in events]
                    
                except Exception as e2:
                    self.logger.error(f"❌ Events request without time filter also failed: {e2}")
                    return []
            
        except Exception as e:
            self.logger.error(f"❌ Failed to fetch events from calendar {calendar_id}: {e}")
            return []
    
    def _sync_events_to_destination(
        self, 
        source_events: List[CalendarEvent], 
        dest_service: Any, 
        dest_calendar_id: str, 
        privacy_mode: str,
        privacy_label: str = "Busy",
        sync_pair: SyncPair = None
    ) -> int:
        """Sync events to destination calendar with privacy rules."""
        synced_count = 0
        
        for event in source_events:
            try:
                # Check Google Calendar event visibility to override privacy mode
                effective_privacy_mode = self._get_effective_privacy_mode(event, privacy_mode)
                
                # Apply privacy rules
                source_cal = self.config.get_calendar_by_id(event.sync_metadata['source_calendar_id'])
                source_cal_name = source_cal.name if source_cal else "Unknown Calendar"
                synced_event = self._apply_privacy_rules(event, effective_privacy_mode, source_cal_name, privacy_label, sync_pair.show_time)
                
                # Check if event already exists in destination
                existing_event = self._find_existing_event(dest_service, dest_calendar_id, event)
                
                if existing_event:
                    # Update existing event
                    self._update_event(dest_service, dest_calendar_id, existing_event['id'], synced_event)
                    self.logger.debug(f"🔄 Updated event: {event.summary}")
                else:
                    # Create new event
                    self._create_event(dest_service, dest_calendar_id, synced_event)
                    self.logger.debug(f"➕ Created event: {event.summary}")
                
                synced_count += 1
                
            except Exception as e:
                self.logger.error(f"❌ Failed to sync event {event.summary}: {e}")
        
        return synced_count
    
    def _apply_privacy_rules(self, event: CalendarEvent, privacy_mode: str, source_calendar_name: str = None, privacy_label: str = "Busy", show_time: bool = False) -> Dict[str, Any]:
        """Apply privacy rules to an event."""
        # Format dates properly for Google Calendar API
        start_data = {}
        end_data = {}
        
        if event.start.hour == 0 and event.start.minute == 0 and event.start.second == 0:
            # All-day event
            start_data = {'date': event.start.date().isoformat()}
            end_data = {'date': event.end.date().isoformat()}
        else:
            # Timed event
            start_data = {'dateTime': event.start.isoformat()}
            end_data = {'dateTime': event.end.isoformat()}
        
        # Create Calsinki footer
        calsinki_footer = f"\n\n---\nEvent added by Calsinki from {source_calendar_name or 'Unknown'} calendar."
        
        # Create summary with or without time
        if show_time:
            summary = f"{privacy_label} - {event.start.strftime('%H:%M')}"
        else:
            summary = privacy_label
        
        if privacy_mode == "public":
            # Keep original event details
            description = event.description + calsinki_footer if event.description else calsinki_footer
            
            return {
                'summary': event.summary,
                'description': description,
                'start': start_data,
                'end': end_data,
                'location': event.location,
                'attendees': event.attendees,
                'extendedProperties': {
                    'private': event.sync_metadata
                }
            }
        elif privacy_mode == "private":
            # Remove ALL identifiable details - completely anonymous
            description = calsinki_footer
            
            return {
                'summary': summary,
                'description': description,
                'start': start_data,
                'end': end_data,
                'extendedProperties': {
                    'private': event.sync_metadata
                }
            }
        else:
            # Default to public for unknown modes
            self.logger.warning(f"⚠️  Unknown privacy mode '{privacy_mode}', defaulting to 'public'")
            return self._apply_privacy_rules(event, "public", source_calendar_name, privacy_label, show_time)
    
    def _find_existing_event(self, service: Any, calendar_id: str, source_event: CalendarEvent) -> Optional[Dict[str, Any]]:
        """Find existing event in destination calendar by checking sync metadata."""
        try:
            # Search for events in the same time window
            events_result = service.events().list(
                calendarId=calendar_id,
                timeMin=source_event.start.isoformat(),
                timeMax=source_event.end.isoformat(),
                singleEvents=True
            ).execute()
            
            events = events_result.get('items', [])
            
            # Check if any event has matching sync metadata
            for event in events:
                if 'extendedProperties' in event and 'private' in event['extendedProperties']:
                    metadata = event['extendedProperties']['private']
                    if (metadata.get('source_event_id') == source_event.event_id and 
                        metadata.get('source_calendar_id') == source_event.sync_metadata['source_calendar_id']):
                        return event
            
            return None
            
        except Exception as e:
            self.logger.error(f"❌ Failed to search for existing event: {e}")
            return None
    
    def _create_event(self, service: Any, calendar_id: str, event_data: Dict[str, Any]):
        """Create a new event in the destination calendar."""
        service.events().insert(
            calendarId=calendar_id,
            body=event_data
        ).execute()
    
    def _update_event(self, service: Any, calendar_id: str, event_id: str, event_data: Dict[str, Any]):
        """Update an existing event in the destination calendar."""
        service.events().update(
            calendarId=calendar_id,
            eventId=event_id,
            body=event_data
        ).execute()

    def _get_effective_privacy_mode(self, event: CalendarEvent, configured_privacy_mode: str) -> str:
        """Determine effective privacy mode based on Google Calendar event visibility."""
        # Check if the original Google event has visibility settings
        if hasattr(event, 'original_event') and event.original_event:
            visibility = event.original_event.get('visibility', 'default')
            
            if visibility == 'public':
                # Public events should preserve details regardless of configured mode
                if configured_privacy_mode != "public":
                    self.logger.info(f"🔓 Event '{event.summary}' is public - overriding privacy mode from '{configured_privacy_mode}' to 'public'")
                return "public"
            elif visibility == 'private':
                # Private events should strip details regardless of configured mode
                if configured_privacy_mode != "private":
                    self.logger.info(f"🔒 Event '{event.summary}' is private - overriding privacy mode from '{configured_privacy_mode}' to 'private'")
                return "private"
            elif visibility == 'default':
                # Default visibility - use configured privacy mode
                return configured_privacy_mode
        else:
            # If we don't have the original event data, use configured mode
            return configured_privacy_mode
        
        return configured_privacy_mode
