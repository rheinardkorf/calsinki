#!/usr/bin/env python3
"""
Script to purge all Reclaim events from Google Calendar.
Includes --dry-run option to preview deletions before executing.
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta, UTC

# Add the calsinki package to the path
sys.path.insert(0, str(Path(__file__).parent))

from calsinki.auth import GoogleAuthenticator, load_oauth2_config
from calsinki.config import Config, get_default_config_path
from googleapiclient.discovery import build


def purge_reclaim_events(dry_run: bool = True, force: bool = False):
    """Purge all events with reclaim.personalSync=true from all calendars."""
    
    if dry_run:
        print("🔍 DRY RUN MODE - No events will be deleted")
        print("Use --execute to actually delete events")
    else:
        if not force:
            print("⚠️  WARNING: This will permanently delete Reclaim events!")
            print("Use --force to confirm you want to proceed")
            return
        
        print("🗑️  EXECUTION MODE - Reclaim events will be deleted")
    
    print("=" * 80)
    
    try:
        # Load configuration
        config_path = get_default_config_path()
        if not config_path.exists():
            print(f"❌ Configuration file not found: {config_path}")
            print("Please run 'calsinki init' first to create configuration.")
            return
        
        config = Config.from_file(config_path)
        print(f"✅ Config loaded successfully from {config_path}")
        
        # Load OAuth2 config
        oauth2_config = load_oauth2_config()
        if not oauth2_config:
            print("❌ Failed to load OAuth2 configuration")
            print("Please run 'calsinki auth --setup' first.")
            return
        
        print(f"✅ OAuth2 config loaded successfully")
        
        total_reclaim_events = 0
        total_deleted = 0
        deletion_summary = []
        
        # Process each account
        for account in config.accounts:
            print(f"\n📅 Processing account: {account.name} ({account.email})")
            
            try:
                # Authenticate
                authenticator = GoogleAuthenticator(account.name, oauth2_config)
                credentials = authenticator.authenticate()
                
                if not credentials:
                    print(f"⚠️  No credentials for {account.name}")
                    continue
                
                # Build Calendar API service
                service = build("calendar", "v3", credentials=credentials)
                print(f"✅ Authenticated with Google Calendar API")
                
                # Check each calendar in this account
                for calendar in account.calendars:
                    
                    print(f"  📋 Calendar: {calendar.name} ({calendar.calendar_id})")
                    
                    try:
                        # Fetch all events to find Reclaim ones
                        now = datetime.now(UTC)
                        time_min = (now - timedelta(days=1095)).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"  # 3 years ago
                        time_max = (now + timedelta(days=365)).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"   # 1 year future
                        
                        print(f"    🔍 Fetching events from {time_min[:10]} to {time_max[:10]}")
                        
                        # Fetch events in batches
                        all_calendar_events = []
                        page_token = None
                        batch_size = 2500
                        
                        while True:
                            events_result = service.events().list(
                                calendarId=calendar.calendar_id,
                                timeMin=time_min,
                                timeMax=time_max,
                                maxResults=batch_size,
                                singleEvents=True,
                                orderBy='startTime',
                                pageToken=page_token
                            ).execute()
                            
                            events = events_result.get('items', [])
                            all_calendar_events.extend(events)
                            
                            page_token = events_result.get('nextPageToken')
                            if not page_token:
                                break
                        
                        print(f"    📊 Fetched {len(all_calendar_events)} total events")
                        
                        # Find Reclaim events
                        reclaim_events = []
                        for event in all_calendar_events:
                            if "extendedProperties" in event:
                                private_props = event.get("extendedProperties", {}).get("private", {})
                                if private_props.get("reclaim.personalSync") == "true":
                                    reclaim_events.append(event)
                        
                        if reclaim_events:
                            print(f"    🎯 Found {len(reclaim_events)} Reclaim events to purge")
                            total_reclaim_events += len(reclaim_events)
                            
                            # Group by recurring event series
                            recurring_groups = {}
                            single_events = []
                            
                            for event in reclaim_events:
                                recurring_event_id = event.get('recurringEventId')
                                if recurring_event_id:
                                    if recurring_event_id not in recurring_groups:
                                        recurring_groups[recurring_event_id] = []
                                    recurring_groups[recurring_event_id].append(event)
                                else:
                                    single_events.append(event)
                            
                            print(f"      📅 Single events: {len(single_events)}")
                            print(f"      🔄 Recurring series: {len(recurring_groups)}")
                            
                            # Process single events
                            for event in single_events:
                                event_summary = {
                                    'type': 'single',
                                    'id': event.get('id'),
                                    'summary': event.get('summary', 'No Title'),
                                    'start': event.get('start', {}).get('dateTime', event.get('start', {}).get('date', 'Unknown')),
                                    'calendar': calendar.name
                                }
                                
                                if dry_run:
                                    print(f"        🗑️  Would delete: {event.get('summary', 'No Title')} ({event.get('start', {}).get('dateTime', 'Unknown')[:10]})")
                                else:
                                    try:
                                        service.events().delete(
                                            calendarId=calendar.calendar_id,
                                            eventId=event.get('id')
                                        ).execute()
                                        print(f"        ✅ Deleted: {event.get('summary', 'No Title')}")
                                        total_deleted += 1
                                    except Exception as e:
                                        print(f"        ❌ Failed to delete: {event.get('summary', 'No Title')} - {e}")
                                        event_summary['error'] = str(e)
                                
                                deletion_summary.append(event_summary)
                            
                            # Process recurring events (delete master events to remove entire series)
                            for master_id, instances in recurring_groups.items():
                                if instances:
                                    master_event = instances[0]  # Use first instance to get master info
                                    event_summary = {
                                        'type': 'recurring_series',
                                        'id': master_id,
                                        'summary': master_event.get('summary', 'No Title'),
                                        'instances': len(instances),
                                        'calendar': calendar.name
                                    }
                                    
                                    if dry_run:
                                        print(f"        🔄 Would delete recurring series: {master_event.get('summary', 'No Title')} ({len(instances)} instances)")
                                    else:
                                        try:
                                            # Delete the master recurring event (this removes the entire series)
                                            service.events().delete(
                                                calendarId=calendar.calendar_id,
                                                eventId=master_id
                                            ).execute()
                                            print(f"        ✅ Deleted recurring series: {master_event.get('summary', 'No Title')} ({len(instances)} instances)")
                                            total_deleted += len(instances)
                                        except Exception as e:
                                            print(f"        ❌ Failed to delete recurring series: {master_event.get('summary', 'No Title')} - {e}")
                                            event_summary['error'] = str(e)
                                    
                                    deletion_summary.append(event_summary)
                        else:
                            print(f"    ✅ No Reclaim events found in this calendar")
                            
                    except Exception as e:
                        print(f"    ❌ Error processing calendar {calendar.name}: {e}")
                        continue
                        
            except Exception as e:
                print(f"❌ Failed to authenticate account {account.name}: {e}")
                continue
        
        # Final summary
        print("\n" + "=" * 80)
        if dry_run:
            print(f"🔍 DRY RUN SUMMARY:")
            print(f"   📊 Total Reclaim events found: {total_reclaim_events}")
            print(f"   🗑️  Events that would be deleted: {total_reclaim_events}")
            print(f"\n💡 To actually delete these events, run:")
            print(f"   python purge_reclaim_events.py --execute --force")
        else:
            print(f"🗑️  PURGE COMPLETED:")
            print(f"   📊 Total Reclaim events found: {total_reclaim_events}")
            print(f"   ✅ Successfully deleted: {total_deleted}")
            print(f"   ❌ Failed deletions: {len([s for s in deletion_summary if 'error' in s])}")
        
        # Save deletion summary to file
        summary_file = f"reclaim_purge_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(summary_file, 'w') as f:
            f.write(f"Reclaim Events Purge Summary - {datetime.now().isoformat()}\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"Total events found: {total_reclaim_events}\n")
            f.write(f"Total deleted: {total_deleted}\n")
            f.write(f"Dry run: {dry_run}\n\n")
            
            for summary in deletion_summary:
                f.write(f"Type: {summary['type']}\n")
                f.write(f"Summary: {summary['summary']}\n")
                f.write(f"Calendar: {summary['calendar']}\n")
                if 'error' in summary:
                    f.write(f"Error: {summary['error']}\n")
                f.write("-" * 40 + "\n")
        
        print(f"\n📄 Detailed summary saved to: {summary_file}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Main entry point with command line argument parsing."""
    parser = argparse.ArgumentParser(
        description="Purge all Reclaim events from Google Calendar",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python purge_reclaim_events.py                    # Dry run (default)
  python purge_reclaim_events.py --execute          # Preview deletions
  python purge_reclaim_events.py --execute --force  # Actually delete events
        """
    )
    
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute deletions (default is dry-run)"
    )
    
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force execution without additional confirmation"
    )
    
    args = parser.parse_args()
    
    # Set dry_run based on --execute flag
    dry_run = not args.execute
    
    if not dry_run and not args.force:
        print("⚠️  WARNING: You are about to permanently delete Reclaim events!")
        print("This action cannot be undone.")
        response = input("Type 'DELETE' to confirm: ")
        if response != "DELETE":
            print("❌ Cancelled by user")
            return
    
    purge_reclaim_events(dry_run=dry_run, force=args.force)


if __name__ == "__main__":
    main()
