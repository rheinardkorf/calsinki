#!/usr/bin/env python3
"""Command-line interface for Calsinki calendar synchronization service."""

import argparse
import sys
from pathlib import Path

from calsinki import __version__


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
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # TODO: Implement command handlers
    if args.command == "sync":
        print("🔄 Calendar synchronization not yet implemented")
        return 0
    elif args.command == "auth":
        print("🔐 Authentication not yet implemented")
        return 0
    elif args.command == "config":
        print("⚙️ Configuration display not yet implemented")
        return 0
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
