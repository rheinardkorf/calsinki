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
    calendar_id: str
    auth_type: str = "oauth2"  # "oauth2" or "service_account"
    credentials_file: Optional[str] = None
    is_source: bool = False
    is_destination: bool = False


@dataclass
class SyncPair:
    """Configuration for a source-destination calendar sync pair."""
    
    source_account: str  # Account name
    source_calendar: str  # Calendar ID
    destination_account: str  # Account name
    destination_calendar: str  # Calendar ID
    privacy_mode: str = "preserve"  # "preserve" or "private"
    sync_interval_minutes: int = 15
    enabled: bool = True


@dataclass
class Config:
    """Main configuration for Calsinki."""
    
    accounts: List[CalendarAccount] = field(default_factory=list)
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
            if not account.calendar_id:
                errors.append(f"Account '{account.name}' must have a calendar ID")
        
        # Validate sync pairs
        for pair in self.sync_pairs:
            if pair.source_account not in account_names:
                errors.append(f"Sync pair references unknown source account: {pair.source_account}")
            if pair.destination_account not in account_names:
                errors.append(f"Sync pair references unknown destination account: {pair.destination_account}")
            
            # Check that accounts are properly configured for their roles
            source_acc = next((acc for acc in self.accounts if acc.name == pair.source_account), None)
            dest_acc = next((acc for acc in self.accounts if acc.name == pair.destination_account), None)
            
            if source_acc and not source_acc.is_source:
                errors.append(f"Account '{pair.source_account}' is not configured as a source")
            if dest_acc and not dest_acc.is_destination:
                errors.append(f"Account '{pair.destination_account}' is not configured as a destination")
        
        return errors
    
    def get_account(self, name: str) -> Optional[CalendarAccount]:
        """Get account by name."""
        for account in self.accounts:
            if account.name == name:
                return account
        return None
    
    def get_source_accounts(self) -> List[CalendarAccount]:
        """Get all accounts configured as sources."""
        return [acc for acc in self.accounts if acc.is_source]
    
    def get_destination_accounts(self) -> List[CalendarAccount]:
        """Get all accounts configured as destinations."""
        return [acc for acc in self.accounts if acc.is_destination]


def create_example_config() -> str:
    """Create an example configuration file."""
    return """# Calsinki Configuration Example

# Google Calendar accounts
accounts:
  - name: "work"
    email: "work@company.com"
    calendar_id: "work@company.com"
    auth_type: "oauth2"
    is_source: true
    is_destination: false
  
  - name: "personal"
    email: "personal@gmail.com"
    calendar_id: "personal@gmail.com"
    auth_type: "oauth2"
    is_source: false
    is_destination: true

# Calendar synchronization pairs
sync_pairs:
  - source_account: "work"
    source_calendar: "work@company.com"
    destination_account: "personal"
    destination_calendar: "personal@gmail.com"
    privacy_mode: "private"  # Strip sensitive details
    sync_interval_minutes: 15
    enabled: true

# Logging configuration
log_level: "INFO"
log_file: "./logs/calsinki.log"

# Data directory for storing sync metadata
data_dir: "./data"
"""
