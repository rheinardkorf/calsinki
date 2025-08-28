#!/usr/bin/env python3
"""Command-line interface for Calsinki calendar synchronization service."""

import argparse
import sys
from pathlib import Path

from calsinki import __version__
from calsinki.auth import (
    GoogleAuthenticator,
    create_oauth2_config_file,
    load_oauth2_config,
)
from calsinki.config import (
    Config,
    create_example_config,
    ensure_directories,
    get_config_dir,
    get_credentials_dir,
    get_default_config_path,
)
from calsinki.purge import handle_purge_all_command, handle_purge_rules_command
from calsinki.sync import CalendarSynchronizer


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Calsinki - Self-hosted calendar synchronization service",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  calsinki init                    # Initialize configuration structure
  calsinki auth --setup            # Set up OAuth2 configuration
  calsinki auth                    # Authenticate all accounts
  calsinki auth personal           # Authenticate specific account
  calsinki auth xteam personal     # Authenticate multiple specific accounts
  calsinki sync                    # Run calendar synchronization
  calsinki sync --dry-run          # Preview sync without making changes
  calsinki sync demo_to_personal   # Sync specific sync rule
  calsinki sync --list             # List available sync rules
  calsinki purge demo_to_personal  # Remove events from specific sync rule
  calsinki purge --all             # Remove all synced events from all rules
  calsinki purge --dry-run         # Show what would be purged
  calsinki config                  # Show current configuration
  calsinki config --example        # Show example configuration
  calsinki --version               # Show version information
        """,
    )

    parser.add_argument(
        "--version", action="version", version=f"Calsinki {__version__}"
    )

    parser.add_argument(
        "--config",
        type=Path,
        default=get_default_config_path(),
        help=f"Path to configuration file (default: {get_default_config_path()})",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Sync command
    sync_parser = subparsers.add_parser("sync", help="Synchronize calendars")
    sync_parser.add_argument(
        "rules",
        nargs="*",
        help="Specific sync rule IDs to sync (default: all enabled rules)",
    )
    sync_parser.add_argument(
        "--list",
        action="store_true",
        help="List available sync rules instead of syncing",
    )
    sync_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be synced without actually modifying calendars",
    )

    # Purge command
    purge_parser = subparsers.add_parser(
        "purge",
        help="Purge synced events from calendars",
        description="Remove all events created by Calsinki synchronization. Use --all to purge all events, or specify sync rule IDs for targeted purging.",
    )
    purge_parser.add_argument(
        "--all",
        action="store_true",
        help="Purge ALL events from ALL calendars (REQUIRED for safety)",
    )
    purge_parser.add_argument(
        "rules",
        nargs="*",
        help="Specific sync rule IDs to purge (REQUIRED unless using --all)",
    )
    purge_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be purged without actually deleting events",
    )

    # Auth command
    auth_parser = subparsers.add_parser(
        "auth", help="Authenticate with Google accounts"
    )
    auth_parser.add_argument(
        "--setup",
        action="store_true",
        help="Set up OAuth2 configuration (create config file)",
    )
    auth_parser.add_argument(
        "accounts",
        nargs="*",
        help="Specific account names to authenticate (default: all accounts)",
    )

    # Config command
    config_parser = subparsers.add_parser("config", help="Show current configuration")
    config_parser.add_argument(
        "--example",
        action="store_true",
        help="Show example configuration instead of current config",
    )

    # Init command
    init_parser = subparsers.add_parser(
        "init",
        help="Initialize Calsinki configuration structure and create starter config",
    )
    init_parser.add_argument(
        "--force", action="store_true", help="Overwrite existing configuration files"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Handle commands
    if args.command == "sync":
        return handle_sync_command(args)
    elif args.command == "auth":
        return handle_auth_command(args)
    elif args.command == "config":
        return handle_config_command(args)
    elif args.command == "init":
        return handle_init_command(args)
    elif args.command == "purge":
        return handle_purge_command(args)

    return 0


def handle_config_command(args) -> int:
    """Handle the config command."""
    if args.example:
        print("📋 Example Configuration:")
        print("=" * 50)
        print(create_example_config())
        return 0

    # Try to load and display current configuration
    try:
        config = Config.from_file(args.config)
        print("⚙️ Current Configuration:")
        print("=" * 50)

        print(f"📊 Accounts ({len(config.accounts)}):")
        for account in config.accounts:
            print(f"  • {account.name} ({account.email}) - {account.auth_type}")
            if account.calendars:
                for calendar in account.calendars:
                    desc = f" - {calendar.description}" if calendar.description else ""
                    print(f"    └─ {calendar.name} ({calendar.calendar_id}){desc}")
            else:
                print("    └─ No calendars configured")

        # Display sync rules if any exist
        if config.sync_rules:
            print(f"\n📋 Sync Rules ({len(config.sync_rules)}):")
            for rule in config.sync_rules:
                source_cal = config.get_calendar_by_label(rule.source_calendar)
                source_name = source_cal.name if source_cal else rule.source_calendar

                print(
                    f"  • [{rule.id}] {source_name} → {len(rule.destination)} destination(s)"
                )

                for i, target in enumerate(rule.destination):
                    dest_cal = config.get_calendar_by_label(target.calendar)
                    dest_name = dest_cal.name if dest_cal else target.calendar
                    status = "✅ enabled" if target.enabled else "❌ disabled"

                    print(f"    {i+1}. {dest_name} ({target.privacy_mode}) - {status}")

                    # Show title customization if configured
                    title_custom = []
                    if target.title_prefix:
                        title_custom.append(f"prefix: '{target.title_prefix}'")
                    if target.title_suffix:
                        title_custom.append(f"suffix: '{target.title_suffix}'")
                    if title_custom:
                        print(f"       └─ Title: {', '.join(title_custom)}")

                    # Show event color if configured
                    if target.event_color:
                        print(f"       └─ Color: {target.event_color}")

                    print(f"       └─ {target.calendar}")

        print(f"\n📁 Data Directory: {config.data_dir}")
        print(f"📝 Log Level: {config.log_level}")
        if config.log_file:
            print(f"📄 Log File: {config.log_file}")

        # Validate configuration
        errors = config.validate()
        if errors:
            print(f"\n⚠️  Configuration Issues ({len(errors)}):")
            for error in errors:
                print(f"  • {error}")
        else:
            print("\n✅ Configuration is valid!")

        return 0

    except FileNotFoundError:
        print(f"❌ Configuration file not found: {args.config}")
        print("\n💡 Use 'calsinki init' to create a new configuration")
        return 1
    except Exception as e:
        print(f"❌ Error loading configuration: {e}")
        return 1


def handle_sync_command(args) -> int:
    """Handle the sync command."""
    try:
        config = Config.from_file(args.config)

        if args.list:
            print("🔄 Available Sync Rules:")
            print("=" * 50)

            # Show sync rules
            if config.sync_rules:
                for rule in config.sync_rules:
                    source_cal = config.get_calendar_by_label(rule.source_calendar)
                    enabled_targets = [t for t in rule.destination if t.enabled]
                    total_targets = len(rule.destination)

                    if source_cal:
                        print(
                            f"  [{rule.id}] {source_cal.name} → {len(enabled_targets)}/{total_targets} destination(s)"
                        )
                        for i, target in enumerate(rule.destination):
                            dest_cal = config.get_calendar_by_label(target.calendar)
                            dest_name = dest_cal.name if dest_cal else target.calendar
                            status = "✅ enabled" if target.enabled else "❌ disabled"
                            print(
                                f"    {i+1}. {dest_name} ({target.privacy_mode}) - {status}"
                            )
                    else:
                        print(
                            f"  [{rule.id}] {rule.source_calendar} → {len(enabled_targets)}/{total_targets} destination(s)"
                        )
            else:
                print("  No sync rules configured")

            return 0

        # Determine which sync operations to perform
        if args.rules:
            # Sync specific rules by ID
            rules_to_sync = []

            for rule_id in args.rules:
                rule = next((r for r in config.sync_rules if r.id == rule_id), None)
                if rule:
                    enabled_targets = [t for t in rule.destination if t.enabled]
                    if enabled_targets:
                        rules_to_sync.append(rule)
                    else:
                        print(
                            f"⚠️  Sync rule '{rule_id}' has no enabled destinations, skipping"
                        )
                else:
                    print(f"❌ Sync rule '{rule_id}' not found")
                    return 1

            if not rules_to_sync:
                print("❌ No valid sync rules to process")
                return 1

            print(
                f"🔄 Syncing {len(rules_to_sync)} specific rule(s): {', '.join(args.rules)}"
            )
        else:
            # Sync all enabled rules
            rules_to_sync = config.get_enabled_sync_rules()

            if not rules_to_sync:
                print("❌ No enabled sync rules found")
                return 1

            print(f"🔄 Syncing all {len(rules_to_sync)} enabled rule(s)")

        # Perform actual synchronization
        if args.dry_run:
            print("🔍 DRY RUN MODE - No calendars will be modified")
            print("🚀 Starting calendar synchronization preview...")
        else:
            print("🚀 Starting calendar synchronization...")

        # Initialize the synchronizer
        synchronizer = CalendarSynchronizer(config)

        # Sync each rule
        for rule in rules_to_sync:
            source_cal = config.get_calendar_by_label(rule.source_calendar)
            enabled_targets = [t for t in rule.destination if t.enabled]

            if source_cal and enabled_targets:
                if args.dry_run:
                    print(
                        f"\n🔍 DRY RUN: Would sync rule [{rule.id}] {source_cal.name} → {len(enabled_targets)} destination(s)"
                    )
                else:
                    print(
                        f"\n🔄 Syncing rule [{rule.id}] {source_cal.name} → {len(enabled_targets)} destination(s)"
                    )

                # Perform the sync (with dry-run support)
                success = synchronizer.sync_rule(rule, dry_run=args.dry_run)

                if success:
                    if args.dry_run:
                        print("  🔍 DRY RUN: Sync preview completed successfully")
                    else:
                        print("  ✅ Sync completed successfully")
                else:
                    print("  ❌ Sync failed")
            else:
                print(
                    f"  ❌ [{rule.id}] Calendar details not found or no enabled destinations"
                )

        if args.dry_run:
            print("\n🔍 DRY RUN COMPLETE - No changes were made to calendars")
        else:
            print("\n🎉 Synchronization complete!")
        return 0

    except FileNotFoundError:
        print(f"❌ Configuration file not found: {args.config}")
        return 1
    except Exception as e:
        print(f"❌ Error during sync: {e}")
        return 1


def handle_auth_command(args) -> int:
    """Handle the auth command."""
    try:
        if args.setup:
            # Create OAuth2 config file
            print("🔧 Setting up OAuth2 configuration...")
            oauth2_config_path = create_oauth2_config_file()
            print(f"✅ OAuth2 config file created at: {oauth2_config_path}")
            print("\n💡 Next steps:")
            print("   1. Go to Google Cloud Console: https://console.cloud.google.com/")
            print("   2. Create a new project or select existing one")
            print("   3. Enable Google Calendar API")
            print("   4. Create OAuth 2.0 credentials")
            print("   5. Edit the config file with your client_id and client_secret")
            print("   6. Run 'calsinki auth' to authenticate")
            return 0

        # Load OAuth2 configuration
        oauth2_config = load_oauth2_config()
        if not oauth2_config:
            print("❌ OAuth2 configuration not found")
            print("💡 Run 'calsinki auth --setup' to create the configuration file")
            return 1

        # Load main configuration to get accounts
        config = Config.from_file(args.config)

        # Determine which accounts to authenticate
        if args.accounts:
            # Authenticate specific accounts
            accounts_to_auth = []
            for account_name in args.accounts:
                account = next(
                    (acc for acc in config.accounts if acc.name == account_name), None
                )
                if account:
                    if account.auth_type == "oauth2":
                        accounts_to_auth.append(account)
                    else:
                        print(
                            f"⚠️  Skipping {account_name} - auth_type '{account.auth_type}' not supported"
                        )
                else:
                    print(f"❌ Account '{account_name}' not found in configuration")
                    return 1

            if not accounts_to_auth:
                print("❌ No valid accounts to authenticate")
                return 1

            print(
                f"🔐 Authenticating {len(accounts_to_auth)} specific account(s): {', '.join(acc.name for acc in accounts_to_auth)}"
            )
        else:
            # Authenticate all OAuth2 accounts
            accounts_to_auth = [
                acc for acc in config.accounts if acc.auth_type == "oauth2"
            ]
            if not accounts_to_auth:
                print("❌ No OAuth2 accounts found in configuration")
                return 1

            print(f"🔐 Authenticating all {len(accounts_to_auth)} OAuth2 account(s)")

        # Authenticate selected accounts
        for account in accounts_to_auth:
            print(f"\n🔐 Authenticating account: {account.name} ({account.email})")
            try:
                authenticator = GoogleAuthenticator(account.name, oauth2_config)
                authenticator.authenticate()
                print(f"✅ Successfully authenticated {account.name}")
            except Exception as e:
                print(f"❌ Failed to authenticate {account.name}: {e}")
                return 1

        print("\n🎉 All accounts authenticated successfully!")
        print("💡 You can now run 'calsinki sync' to start synchronization")
        return 0

    except Exception as e:
        print(f"❌ Error during authentication: {e}")
        return 1


def handle_purge_command(args) -> int:
    """Handle the purge command."""
    try:
        print("🗑️  Starting event purge operation...")

        # Safety check: require explicit --all or specific sync rule IDs
        if not args.all and not args.rules:
            print("❌ SAFETY ERROR: No purge target specified!")
            print("💡 You must either:")
            print("   • Use --all to purge ALL events from ALL calendars")
            print("   • Specify sync rule IDs: calsinki purge sync_rule_1 sync_rule_2")
            print("💡 This prevents accidental deletion of all synced events.")
            return 1

        # Load configuration
        config = Config.from_file(args.config)

        # Load OAuth2 configuration
        oauth2_config = load_oauth2_config()
        if not oauth2_config:
            print("❌ OAuth2 configuration not found")
            print("💡 Run 'calsinki auth --setup' to create the configuration file")
            return 1

        # Initialize synchronizer for API access
        synchronizer = CalendarSynchronizer(config)

        if args.all:
            # Purge all events using default identifier
            return handle_purge_all_command(args, config, synchronizer)
        else:
            # Purge specific sync rules
            return handle_purge_rules_command(args, config, synchronizer)

    except Exception as e:
        print(f"❌ Error during purge operation: {e}")
        return 1


def handle_init_command(args) -> int:
    """Handle the init command."""
    try:
        print("🚀 Initializing Calsinki configuration structure...")

        # Ensure directories exist
        ensure_directories()

        config_path = get_default_config_path()
        example_config = create_example_config()

        # Check if config already exists
        if config_path.exists() and not args.force:
            print(f"⚠️  Configuration already exists at: {config_path}")
            print("   Use --force to overwrite existing configuration")
            return 1

        # Write configuration file
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(example_config)

        print(f"✅ Configuration initialized at: {config_path}")
        print(f"📁 Credentials directory: {get_credentials_dir()}")
        print(f"📁 Config directory: {get_config_dir()}")
        print("\n💡 Next steps:")
        print("   1. Edit the configuration file with your calendar details")
        print("   2. Run 'calsinki auth' to authenticate with Google")
        print("   3. Run 'calsinki sync' to start synchronization")

        return 0

    except Exception as e:
        print(f"❌ Error during initialization: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
