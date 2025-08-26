"""Configuration management for Calsinki calendar synchronization service."""

import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class CalendarAccount:
    """Configuration for a single Google Calendar account."""
    
    name: str
    email: str
    auth_type: str = "oauth2"  # "oauth2" or "service_account"
    credentials_file: Optional[str] = None


@dataclass
class Calendar:
    """Configuration for a specific calendar within an account."""
    
    account_name: str  # Reference to the account
    calendar_id: str   # Google Calendar ID (can be email, calendar ID, or resource ID)
    name: str          # Human-readable name for this calendar
    description: Optional[str] = None  # Optional description of the calendar


@dataclass
class SyncPair:
    """Configuration for a source-destination calendar sync pair."""
    
    id: str                    # Unique identifier for this sync pair
    source_calendar: str       # Calendar ID (not name)
    destination_calendar: str  # Calendar ID (not name)
    privacy_mode: str = "preserve"  # "preserve" or "private"
    enabled: bool = True


@dataclass
class Config:
    """Main configuration for Calsinki."""
    
    accounts: List[CalendarAccount] = field(default_factory=list)
    calendars: List[Calendar] = field(default_factory=list)
    sync_pairs: List[SyncPair] = field(default_factory=list)
    log_level: str = "INFO"
    log_file: Optional[str] = None
    data_dir: str = "./data"
    
    @classmethod
    def from_file(cls, config_path: Path) -> "Config":
        """Load configuration from YAML file."""
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        return cls.from_dict(data)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Config":
        """Create configuration from dictionary."""
        config = cls()
        
        # Load accounts
        if 'accounts' in data:
            for account_data in data['accounts']:
                account = CalendarAccount(**account_data)
                config.accounts.append(account)
        
        # Load calendars
        if 'calendars' in data:
            for calendar_data in data['calendars']:
                calendar = Calendar(**calendar_data)
                config.calendars.append(calendar)
        
        # Load sync pairs
        if 'sync_pairs' in data:
            for pair_data in data['sync_pairs']:
                pair = SyncPair(**pair_data)
                config.sync_pairs.append(pair)
        
        # Load other settings
        if 'log_level' in data:
            config.log_level = data['log_level']
        if 'log_file' in data:
            config.log_file = data['log_file']
        if 'data_dir' in data:
            config.data_dir = data['data_dir']
        
        return config
    
    def validate(self) -> List[str]:
        """Validate configuration and return list of errors."""
        errors = []
        
        # Validate accounts
        account_names = {acc.name for acc in self.accounts}
        for account in self.accounts:
            if not account.name:
                errors.append("Account must have a name")
            if not account.email:
                errors.append(f"Account '{account.name}' must have an email")
        
        # Validate calendars
        calendar_ids = set()
        for calendar in self.calendars:
            if not calendar.account_name:
                errors.append(f"Calendar '{calendar.name}' must reference an account")
            elif calendar.account_name not in account_names:
                errors.append(f"Calendar '{calendar.name}' references unknown account: {calendar.account_name}")
            else:
                calendar_ids.add(calendar.calendar_id)
        
        # Validate sync pairs
        for pair in self.sync_pairs:
            # Check that source calendar exists
            if pair.source_calendar not in calendar_ids:
                errors.append(f"Sync pair references unknown source calendar ID: {pair.source_calendar}")
            
            # Check that destination calendar exists
            if pair.destination_calendar not in calendar_ids:
                errors.append(f"Sync pair references unknown destination calendar ID: {pair.destination_calendar}")
            
            # Check that source and destination are different
            if pair.source_calendar == pair.destination_calendar:
                errors.append(f"Sync pair cannot sync calendar to itself: {pair.source_calendar}")
        
        return errors
    
    def get_account(self, name: str) -> Optional[CalendarAccount]:
        """Get account by name."""
        for account in self.accounts:
            if account.name == name:
                return account
        return None
    
    def get_calendar(self, account_name: str, calendar_id: str) -> Optional[Calendar]:
        """Get calendar by account name and calendar ID."""
        for calendar in self.calendars:
            if calendar.account_name == account_name and calendar.calendar_id == calendar_id:
                return calendar
        return None
    
    def get_calendar_by_name(self, calendar_name: str) -> Optional[Calendar]:
        """Get calendar by its human-readable name."""
        for calendar in self.calendars:
            if calendar.name == calendar_name:
                return calendar
        return None
    
    def get_calendar_by_id(self, calendar_id: str) -> Optional[Calendar]:
        """Get calendar by its calendar ID."""
        for calendar in self.calendars:
            if calendar.calendar_id == calendar_id:
                return calendar
        return None
    
    def get_calendars_for_account(self, account_name: str) -> List[Calendar]:
        """Get all calendars for a specific account."""
        return [cal for cal in self.calendars if cal.account_name == account_name]


def create_example_config() -> str:
    """Create an example configuration file."""
    return """# Calsinki Configuration Example

# Google Calendar accounts (authentication)
accounts:
  - name: "work"
    email: "work@company.com"
    auth_type: "oauth2"
  
  - name: "personal"
    email: "personal@gmail.com"
    auth_type: "oauth2"

# Available calendars within each account
calendars:
  - account_name: "work"
    calendar_id: "work@company.com"
    name: "Work Calendar"
  
  - account_name: "work"
    calendar_id: "team@company.com"
    name: "Team Calendar"
  
  - account_name: "personal"
    calendar_id: "personal@gmail.com"
    name: "Personal Calendar"
  
  - account_name: "personal"
    calendar_id: "family@gmail.com"
    name: "Family Calendar"

# Calendar synchronization pairs
sync_pairs:
  - id: "work_to_personal"
    source_calendar: "work@company.com"
    destination_calendar: "personal@gmail.com"
    privacy_mode: "private"  # Strip sensitive details
    enabled: true
  
  - id: "team_to_family"
    source_calendar: "team@company.com"
    destination_calendar: "family@gmail.com"
    privacy_mode: "preserve"  # Keep all details
    enabled: true

# Logging configuration
log_level: "INFO"
log_file: "./logs/calsinki.log"

# Data directory for storing sync metadata
data_dir: "./data"
"""
