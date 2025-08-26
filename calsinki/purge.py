"""Purge functionality for Calsinki calendar synchronization service."""

from typing import List
from calsinki.config import Config
from calsinki.sync import CalendarSynchronizer


def handle_purge_all_command(args, config: Config, synchronizer: CalendarSynchronizer) -> int:
    """Handle purging all events using the default identifier."""
    try:
        default_identifier = getattr(config, 'default_identifier', 'calsinki') or 'calsinki'
        instance_property = f"{default_identifier}_synced=true"
        
        print(f"🧹 Purging all events with '{instance_property}' from all calendars...")
        
        if args.dry_run:
            print("🔍 DRY RUN MODE - No events will be deleted")
        
        total_deleted = 0
        
        # Get all destination calendars
        dest_calendars = set()
        for pair in config.sync_pairs:
            if pair.enabled:
                dest_cal = config.get_calendar_by_id(pair.destination_calendar)
                if dest_cal:
                    dest_calendars.add((dest_cal.account_name, dest_cal.calendar_id, dest_cal.name))
        
        for account_name, calendar_id, calendar_name in dest_calendars:
            print(f"\n📅 Processing calendar: {calendar_name} ({calendar_id})")
            
            try:
                # Get service for this account
                service = synchronizer.calendar_services.get(account_name)
                if not service:
                    print(f"⚠️  No service available for account {account_name}")
                    continue
                
                # Search for events with the instance identifier
                deleted_count = purge_events_from_calendar(
                    service, calendar_id, instance_property, 
                    dry_run=args.dry_run, calendar_name=calendar_name
                )
                total_deleted += deleted_count
                
            except Exception as e:
                print(f"❌ Error processing calendar {calendar_name}: {e}")
                continue
        
        if args.dry_run:
            print(f"\n🔍 DRY RUN COMPLETE - Would delete {total_deleted} events")
        else:
            print(f"\n✅ PURGE COMPLETE - Deleted {total_deleted} events")
        
        return 0
        
    except Exception as e:
        print(f"❌ Error during purge all operation: {e}")
        return 1


def handle_purge_pairs_command(args, config: Config, synchronizer: CalendarSynchronizer) -> int:
    """Handle purging events from specific sync pairs."""
    try:
        # Require explicit sync pair IDs
        if not args.pairs:
            print("❌ SAFETY ERROR: No sync pair IDs specified!")
            print("💡 You must specify which sync pairs to purge:")
            print("   • calsinki purge sync_pair_1 sync_pair_2")
            print("   • Or use --all to purge all events from all calendars")
            return 1
        
        pairs_to_purge = []
        for pair_id in args.pairs:
            pair = next((p for p in config.sync_pairs if p.id == pair_id), None)
            if pair and pair.enabled:
                pairs_to_purge.append(pair)
            elif pair and not pair.enabled:
                print(f"⚠️  Sync pair '{pair_id}' is disabled - skipping")
            else:
                print(f"❌ Sync pair '{pair_id}' not found")
                return 1
        
        if not pairs_to_purge:
            print("❌ No valid sync pairs to purge")
            return 1
        
        print(f"🧹 Purging events from {len(pairs_to_purge)} sync pair(s)...")
        
        if args.dry_run:
            print("🔍 DRY RUN MODE - No events will be deleted")
        
        total_deleted = 0
        
        for pair in pairs_to_purge:
            print(f"\n🔄 Processing sync pair: [{pair.id}]")
            
            try:
                # Get source and destination calendars
                source_cal = config.get_calendar_by_id(pair.source_calendar)
                dest_cal = config.get_calendar_by_id(pair.destination_calendar)
                
                if not source_cal or not dest_cal:
                    print(f"❌ Calendar not found for sync pair {pair.id}")
                    continue
                
                # Get service for destination account
                dest_service = synchronizer.calendar_services.get(dest_cal.account_name)
                if not dest_service:
                    print(f"⚠️  No service available for destination account {dest_cal.account_name}")
                    continue
                
                # Generate the sync pair identifier
                pair_identifier = config.get_effective_identifier(pair)
                search_property = f"{pair_identifier}=true"
                
                print(f"   📅 Destination: {dest_cal.name} ({dest_cal.calendar_id})")
                print(f"   🔍 Searching for: {search_property}")
                
                # Purge events from this calendar
                deleted_count = purge_events_from_calendar(
                    dest_service, dest_cal.calendar_id, search_property,
                    dry_run=args.dry_run, calendar_name=dest_cal.name
                )
                total_deleted += deleted_count
                
            except Exception as e:
                print(f"❌ Error processing sync pair {pair.id}: {e}")
                continue
        
        if args.dry_run:
            print(f"\n🔍 DRY RUN COMPLETE - Would delete {total_deleted} events")
        else:
            print(f"\n✅ PURGE COMPLETE - Deleted {total_deleted} events")
        
        return 0
        
    except Exception as e:
        print(f"❌ Error during purge pairs operation: {e}")
        return 1


def purge_events_from_calendar(service, calendar_id: str, search_property: str, dry_run: bool = False, calendar_name: str = "Unknown") -> int:
    """Purge events from a specific calendar using the search property."""
    try:
        deleted_count = 0
        page_token = None
        
        while True:
            # Search for events with the property (with pagination)
            events_result = service.events().list(
                calendarId=calendar_id,
                privateExtendedProperty=search_property,
                maxResults=250,  # Use reasonable page size
                pageToken=page_token
            ).execute()
            
            events = events_result.get('items', [])
            if not events:
                break
            
            print(f"      📋 Found {len(events)} events to purge")
            
            for event in events:
                event_summary = event.get('summary', 'No Summary')
                event_id = event.get('id')
                
                if dry_run:
                    print(f"         🔍 Would delete: {event_summary}")
                else:
                    try:
                        service.events().delete(
                            calendarId=calendar_id,
                            eventId=event_id
                        ).execute()
                        print(f"         🗑️  Deleted: {event_summary}")
                        deleted_count += 1
                    except Exception as e:
                        print(f"         ❌ Failed to delete {event_summary}: {e}")
            
            # Check if there are more pages
            page_token = events_result.get('nextPageToken')
            if not page_token:
                break
        
        return deleted_count
        
    except Exception as e:
        print(f"         ❌ Error purging events from {calendar_name}: {e}")
        return 0
