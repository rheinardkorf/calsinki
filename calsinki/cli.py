#!/usr/bin/env python3
"""Command-line interface for Calsinki calendar synchronization service."""

import argparse
import sys
from pathlib import Path

from calsinki import __version__
from calsinki.config import Config, create_example_config


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Calsinki - Self-hosted calendar synchronization service",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  calsinki sync                    # Run calendar synchronization
  calsinki auth                    # Authenticate with Google accounts
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
        default=Path("config.yaml"),
        help="Path to configuration file (default: config.yaml)"
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
    
    # Auth command
    auth_parser = subparsers.add_parser(
        "auth", 
        help="Authenticate with Google accounts"
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
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Handle commands
    if args.command == "sync":
        print("🔄 Calendar synchronization not yet implemented")
        return 0
    elif args.command == "auth":
        print("🔐 Authentication not yet implemented")
        return 0
    elif args.command == "config":
        return handle_config_command(args)
    
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
            role = "source" if account.is_source else "destination" if account.is_destination else "none"
            print(f"  • {account.name} ({account.email}) - {role}")
        
        print(f"\n🔄 Sync Pairs ({len(config.sync_pairs)}):")
        for pair in config.sync_pairs:
            status = "✅ enabled" if pair.enabled else "❌ disabled"
            print(f"  • {pair.source_account} → {pair.destination_account} ({pair.privacy_mode}) - {status}")
        
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
        print("\n💡 Use 'calsinki config --example' to see an example configuration")
        return 1
    except Exception as e:
        print(f"❌ Error loading configuration: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
