"""Purge functionality for Calsinki calendar synchronization service."""

from calsinki.config import Config
from calsinki.sync import CalendarSynchronizer


def handle_purge_all_command(
    args, config: Config, synchronizer: CalendarSynchronizer
) -> int:
    """Handle purging all events using the default identifier."""
    try:
        default_identifier = (
            getattr(config, "default_identifier", "calsinki") or "calsinki"
        )
        instance_property = f"{default_identifier}_synced=true"

        print(f"🧹 Purging all events with '{instance_property}' from all calendars...")

        if args.dry_run:
            print("🔍 DRY RUN MODE - No events will be deleted")

        total_deleted = 0

        # Get all destination calendars from sync rules
        dest_calendars = set()

        for rule in config.sync_rules:
            enabled_targets = config.get_enabled_targets_for_rule(rule)
            for target in enabled_targets:
                dest_cal = config.get_calendar_by_label(target.calendar)
                if dest_cal:
                    account_name = config.get_account_name_for_calendar(
                        dest_cal.calendar_id
                    )
                    if account_name:
                        dest_calendars.add(
                            (account_name, dest_cal.calendar_id, dest_cal.name)
                        )

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
                    service,
                    calendar_id,
                    instance_property,
                    dry_run=args.dry_run,
                    calendar_name=calendar_name,
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


def handle_purge_rules_command(
    args, config: Config, synchronizer: CalendarSynchronizer
) -> int:
    """Handle purging events from specific sync rules."""
    try:
        # Require explicit sync rule IDs
        if not args.rules:
            print("❌ SAFETY ERROR: No sync rule IDs specified!")
            print("💡 You must specify which sync rules to purge:")
            print("   • calsinki purge sync_rule_1 sync_rule_2")
            print("   • Or use --all to purge all events from all calendars")
            return 1

        rules_to_purge = []
        for rule_id in args.rules:
            rule = next((r for r in config.sync_rules if r.id == rule_id), None)
            if rule:
                enabled_targets = config.get_enabled_targets_for_rule(rule)
                if enabled_targets:
                    rules_to_purge.append(rule)
                else:
                    print(f"⚠️  Sync rule '{rule_id}' has no enabled targets - skipping")
            else:
                print(f"❌ Sync rule '{rule_id}' not found")
                return 1

        if not rules_to_purge:
            print("❌ No valid sync rules to purge")
            return 1

        print(f"🧹 Purging events from {len(rules_to_purge)} sync rule(s)...")

        if args.dry_run:
            print("🔍 DRY RUN MODE - No events will be deleted")

        total_deleted = 0

        for rule in rules_to_purge:
            print(f"\n🔄 Processing sync rule: [{rule.id}]")

            try:
                # Get source calendar
                source_cal = config.get_calendar_by_label(rule.source_calendar)
                if not source_cal:
                    print(f"❌ Source calendar not found for sync rule {rule.id}")
                    continue

                # Get enabled targets for this rule
                enabled_targets = config.get_enabled_targets_for_rule(rule)
                if not enabled_targets:
                    print(f"⚠️  No enabled targets for sync rule {rule.id}")
                    continue

                print(f"   📅 Source: {source_cal.name} ({source_cal.calendar_id})")
                print(f"   🎯 Targets: {len(enabled_targets)} enabled destination(s)")

                # Process each target
                for target in enabled_targets:
                    try:
                        # Get destination calendar
                        dest_cal = config.get_calendar_by_label(target.calendar)
                        if not dest_cal:
                            print(
                                f"      ❌ Destination calendar not found: {target.calendar}"
                            )
                            continue

                        # Get service for destination account
                        dest_account_name = config.get_account_name_for_calendar(
                            dest_cal.calendar_id
                        )
                        if not dest_account_name:
                            print(
                                f"      ❌ Could not determine account for destination calendar: {dest_cal.calendar_id}"
                            )
                            continue

                        dest_service = synchronizer.calendar_services.get(
                            dest_account_name
                        )
                        if not dest_service:
                            print(
                                f"      ⚠️  No service available for destination account {dest_account_name}"
                            )
                            continue

                        # Generate the sync rule identifier for this target
                        rule_identifier = config.get_effective_identifier_for_rule(
                            rule, target.calendar
                        )
                        search_property = f"{rule_identifier}=true"

                        print(
                            f"      📅 Target: {dest_cal.name} ({dest_cal.calendar_id})"
                        )
                        print(f"      🔍 Searching for: {search_property}")

                        # Purge events from this calendar
                        deleted_count = purge_events_from_calendar(
                            dest_service,
                            dest_cal.calendar_id,
                            search_property,
                            dry_run=args.dry_run,
                            calendar_name=dest_cal.name,
                        )
                        total_deleted += deleted_count

                    except Exception as e:
                        print(
                            f"      ❌ Error processing target {target.calendar}: {e}"
                        )
                        continue

            except Exception as e:
                print(f"❌ Error processing sync rule {rule.id}: {e}")
                continue

        if args.dry_run:
            print(f"\n🔍 DRY RUN COMPLETE - Would delete {total_deleted} events")
        else:
            print(f"\n✅ PURGE COMPLETE - Deleted {total_deleted} events")

        return 0

    except Exception as e:
        print(f"❌ Error during purge items operation: {e}")
        return 1


def purge_events_from_calendar(
    service,
    calendar_id: str,
    search_property: str,
    dry_run: bool = False,
    calendar_name: str = "Unknown",
) -> int:
    """Purge events from a specific calendar using the search property."""
    try:
        deleted_count = 0
        page_token = None

        while True:
            # Search for events with the property (with pagination)
            events_result = (
                service.events()
                .list(
                    calendarId=calendar_id,
                    privateExtendedProperty=search_property,
                    maxResults=250,  # Use reasonable page size
                    pageToken=page_token,
                )
                .execute()
            )

            events = events_result.get("items", [])
            if not events:
                break

            print(f"      📋 Found {len(events)} events to purge")

            for event in events:
                event_summary = event.get("summary", "No Summary")
                event_id = event.get("id")

                if dry_run:
                    print(f"         🔍 Would delete: {event_summary}")
                else:
                    try:
                        service.events().delete(
                            calendarId=calendar_id, eventId=event_id
                        ).execute()
                        print(f"         🗑️  Deleted: {event_summary}")
                        deleted_count += 1
                    except Exception as e:
                        print(f"         ❌ Failed to delete {event_summary}: {e}")

            # Check if there are more pages
            page_token = events_result.get("nextPageToken")
            if not page_token:
                break

        return deleted_count

    except Exception as e:
        print(f"         ❌ Error purging events from {calendar_name}: {e}")
        return 0
