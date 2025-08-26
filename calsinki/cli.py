#!/usr/bin/env python3
"""Command-line interface for Calsinki calendar synchronization service."""

import argparse
import sys
from pathlib import Path

from calsinki import __version__
from calsinki.config import Config, create_example_config, get_default_config_path, ensure_directories, get_credentials_dir, get_config_dir
from calsinki.auth import create_oauth2_config_file, load_oauth2_config, GoogleAuthenticator
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
  calsinki config                  # Show current configuration
  calsinki config --example        # Show example configuration
  calsinki --version              # Show version information
        """,
    )
    
    parser.add_argument(
        "--version", 
        action="version", 
        version=f"Calsinki {__version__}"
    )
    
    parser.add_argument(
        "--config", 
        type=Path, 
        default=get_default_config_path(),
        help=f"Path to configuration file (default: {get_default_config_path()})"
    )
    
    subparsers = parser.add_subparsers(
        dest="command", 
        help="Available commands"
    )
    
    # Sync command
    sync_parser = subparsers.add_parser(
        "sync", 
        help="Synchronize calendars"
    )
    sync_parser.add_argument(
        "pairs",
        nargs="*",
        help="Specific sync pair IDs to sync (default: all enabled pairs)"
    )
    sync_parser.add_argument(
        "--list",
        action="store_true",
        help="List available sync pairs instead of syncing"
    )
    
    # Auth command
    auth_parser = subparsers.add_parser(
        "auth", 
        help="Authenticate with Google accounts"
    )
    auth_parser.add_argument(
        "--setup",
        action="store_true",
        help="Set up OAuth2 configuration (create config file)"
    )
    auth_parser.add_argument(
        "accounts",
        nargs="*",
        help="Specific account names to authenticate (default: all accounts)"
    )
    
    # Config command
    config_parser = subparsers.add_parser(
        "config", 
        help="Show current configuration"
    )
    config_parser.add_argument(
        "--example",
        action="store_true",
        help="Show example configuration instead of current config"
    )
    
    # Init command
    init_parser = subparsers.add_parser(
        "init",
        help="Initialize Calsinki configuration structure and create starter config"
    )
    init_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing configuration files"
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
        
        print(f"\n📅 Calendars ({len(config.calendars)}):")
        for calendar in config.calendars:
            desc = f" - {calendar.description}" if calendar.description else ""
            print(f"  • {calendar.name} ({calendar.calendar_id}) in account '{calendar.account_name}'{desc}")
        
        print(f"\n🔄 Sync Pairs ({len(config.sync_pairs)}):")
        for pair in config.sync_pairs:
            status = "✅ enabled" if pair.enabled else "❌ disabled"
            source_cal = config.get_calendar_by_id(pair.source_calendar)
            dest_cal = config.get_calendar_by_id(pair.destination_calendar)
            
            if source_cal and dest_cal:
                print(f"  • [{pair.id}] {source_cal.name} → {dest_cal.name} ({pair.privacy_mode}) - {status}")
                print(f"    └─ {source_cal.account_name}:{pair.source_calendar} → {dest_cal.account_name}:{pair.destination_calendar}")
            else:
                print(f"  • [{pair.id}] {pair.source_calendar} → {pair.destination_calendar} ({pair.privacy_mode}) - {status}")
                print(f"    └─ [Calendar details not found]")
        
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
            print("🔄 Available Sync Pairs:")
            print("=" * 50)
            for pair in config.sync_pairs:
                status = "✅ enabled" if pair.enabled else "❌ disabled"
                source_cal = config.get_calendar_by_id(pair.source_calendar)
                dest_cal = config.get_calendar_by_id(pair.destination_calendar)
                
                if source_cal and dest_cal:
                    print(f"  [{pair.id}] {source_cal.name} → {dest_cal.name} ({pair.privacy_mode}) - {status}")
                else:
                    print(f"  [{pair.id}] {pair.source_calendar} → {pair.destination_calendar} ({pair.privacy_mode}) - {status}")
            return 0
        
        # Determine which pairs to sync
        if args.pairs:
            # Sync specific pairs by ID
            pairs_to_sync = []
            for pair_id in args.pairs:
                pair = next((p for p in config.sync_pairs if p.id == pair_id), None)
                if pair:
                    if pair.enabled:
                        pairs_to_sync.append(pair)
                    else:
                        print(f"⚠️  Sync pair '{pair_id}' is disabled, skipping")
                else:
                    print(f"❌ Sync pair '{pair_id}' not found")
                    return 1
            
            if not pairs_to_sync:
                print("❌ No valid sync pairs to process")
                return 1
                
            print(f"🔄 Syncing {len(pairs_to_sync)} specific pair(s): {', '.join(p.id for p in pairs_to_sync)}")
        else:
            # Sync all enabled pairs
            pairs_to_sync = [p for p in config.sync_pairs if p.enabled]
            if not pairs_to_sync:
                print("❌ No enabled sync pairs found")
                return 1
                
            print(f"🔄 Syncing all {len(pairs_to_sync)} enabled pair(s)")
        
        # Perform actual synchronization
        print("🚀 Starting calendar synchronization...")
        
        # Initialize the synchronizer
        synchronizer = CalendarSynchronizer(config)
        
        # Sync each pair
        for pair in pairs_to_sync:
            source_cal = config.get_calendar_by_id(pair.source_calendar)
            dest_cal = config.get_calendar_by_id(pair.destination_calendar)
            
            if source_cal and dest_cal:
                print(f"\n🔄 Syncing [{pair.id}] {source_cal.name} → {dest_cal.name} ({pair.privacy_mode})")
                
                # Perform the sync
                success = synchronizer.sync_pair(pair)
                
                if success:
                    print(f"  ✅ Sync completed successfully")
                else:
                    print(f"  ❌ Sync failed")
            else:
                print(f"  ❌ [{pair.id}] Calendar details not found")
        
        print(f"\n🎉 Synchronization complete!")
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
                account = next((acc for acc in config.accounts if acc.name == account_name), None)
                if account:
                    if account.auth_type == "oauth2":
                        accounts_to_auth.append(account)
                    else:
                        print(f"⚠️  Skipping {account_name} - auth_type '{account.auth_type}' not supported")
                else:
                    print(f"❌ Account '{account_name}' not found in configuration")
                    return 1
            
            if not accounts_to_auth:
                print("❌ No valid accounts to authenticate")
                return 1
                
            print(f"🔐 Authenticating {len(accounts_to_auth)} specific account(s): {', '.join(acc.name for acc in accounts_to_auth)}")
        else:
            # Authenticate all OAuth2 accounts
            accounts_to_auth = [acc for acc in config.accounts if acc.auth_type == "oauth2"]
            if not accounts_to_auth:
                print("❌ No OAuth2 accounts found in configuration")
                return 1
                
            print(f"🔐 Authenticating all {len(accounts_to_auth)} OAuth2 account(s)")
        
        # Authenticate selected accounts
        for account in accounts_to_auth:
            print(f"\n🔐 Authenticating account: {account.name} ({account.email})")
            try:
                authenticator = GoogleAuthenticator(account.name, oauth2_config)
                credentials = authenticator.authenticate()
                print(f"✅ Successfully authenticated {account.name}")
            except Exception as e:
                print(f"❌ Failed to authenticate {account.name}: {e}")
                return 1
        
        print(f"\n🎉 All accounts authenticated successfully!")
        print("💡 You can now run 'calsinki sync' to start synchronization")
        return 0
        
    except Exception as e:
        print(f"❌ Error during authentication: {e}")
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
        with open(config_path, 'w', encoding='utf-8') as f:
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
