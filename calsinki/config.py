"""Configuration management for Calsinki calendar synchronization service."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from platformdirs import user_config_dir, user_data_dir


@dataclass
class Calendar:
    """Configuration for a specific calendar within an account."""

    label: str  # Unique label for this calendar within the account
    calendar_id: str  # Google Calendar ID (can be email, calendar ID, or resource ID)
    name: str  # Human-readable name for this calendar
    description: str | None = None  # Optional description of the calendar

    def get_account_name(self, config: "Config") -> str | None:
        """Get the account name that owns this calendar."""
        for account in config.accounts:
            for calendar in account.calendars:
                if calendar.calendar_id == self.calendar_id:
                    return account.name
        return None


@dataclass
class CalendarAccount:
    """Configuration for a single Google Calendar account."""

    name: str
    email: str
    auth_type: str = "oauth2"  # "oauth2" or "service_account"
    credentials_file: str | None = None
    calendars: list[Calendar] = field(
        default_factory=list
    )  # List of calendars in this account


@dataclass
class SyncTarget:
    """Configuration for a single target calendar within a sync rule."""

    calendar: str  # Calendar label (not calendar ID)
    privacy_mode: str = (
        "public"  # "public" or "private" - aligns with Google Calendar visibility
    )
    privacy_label: str = "Busy"  # Custom label for private mode (defaults to "Busy")
    show_time: bool = (
        False  # Whether to show time in privacy labels (defaults to false)
    )
    title_prefix: str = ""  # Optional prefix to add to destination event titles
    title_suffix: str = ""  # Optional suffix to add to destination event titles
    event_color: str = (
        ""  # Optional color ID for destination events (Google Calendar color ID)
    )
    enabled: bool = True


@dataclass
class SyncRule:
    """Configuration for a source calendar sync rule with multiple target calendars."""

    id: str  # Unique identifier for this sync rule
    source_calendar: str  # Calendar label (not calendar ID)
    destination: list[SyncTarget] = field(
        default_factory=list
    )  # List of target calendars with individual settings


@dataclass
class Config:
    """Main configuration for Calsinki."""

    accounts: list[CalendarAccount] = field(default_factory=list)
    sync_rules: list[SyncRule] = field(default_factory=list)  # Sync rules support
    log_level: str = "INFO"
    log_file: str | None = None
    data_dir: str = "./data"
    default_identifier: str = "calsinki"  # Default identifier for all sync operations

    @classmethod
    def from_file(cls, config_path: Path) -> "Config":
        """Load configuration from YAML file."""
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        with open(config_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Config":
        """Create configuration from dictionary."""
        config = cls()

        # Load accounts with nested calendars
        if "accounts" in data:
            for account_data in data["accounts"]:
                # Extract calendars from account data
                calendars = []
                if "calendars" in account_data:
                    for calendar_data in account_data["calendars"]:
                        calendar = Calendar(**calendar_data)
                        calendars.append(calendar)

                # Create account with calendars
                account = CalendarAccount(
                    name=account_data["name"],
                    email=account_data["email"],
                    auth_type=account_data.get("auth_type", "oauth2"),
                    credentials_file=account_data.get("credentials_file"),
                    calendars=calendars,
                )
                config.accounts.append(account)

        # Load sync rules
        if "sync_rules" in data:
            for rule_data in data["sync_rules"]:
                # Handle nested destination structure
                destinations = []
                if "destination" in rule_data:
                    for dest_data in rule_data["destination"]:
                        destination = SyncTarget(**dest_data)
                        destinations.append(destination)

                # Create rule with destinations
                rule = SyncRule(
                    id=rule_data["id"],
                    source_calendar=rule_data["source_calendar"],
                    destination=destinations,
                )
                config.sync_rules.append(rule)

        # Load other settings
        if "log_level" in data:
            config.log_level = data["log_level"]
        if "log_file" in data:
            config.log_file = data["log_file"]
        if "data_dir" in data:
            config.data_dir = data["data_dir"]
        if "default_identifier" in data:
            config.default_identifier = data["default_identifier"]

        return config

    def get_effective_identifier_for_rule(
        self, sync_rule: SyncRule, target_calendar_label: str
    ) -> str:
        """
        Get the effective identifier for a sync rule by combining:
        default_identifier + sync_rule.id

        Examples:
        - default_identifier: "calsinki", rule.id: "demo_to_personal"
          → "calsinki_demo_to_personal"
        """
        default_id = getattr(self, "default_identifier", "calsinki") or "calsinki"
        return f"{default_id}_{sync_rule.id}"

    def validate(self) -> list[str]:
        """Validate configuration and return list of errors."""
        errors = []

        # Validate accounts
        for account in self.accounts:
            if not account.name:
                errors.append("Account must have a name")
            if not account.email:
                errors.append(f"Account '{account.name}' must have an email")

        # Validate calendars within accounts
        calendar_ids = set()
        for account in self.accounts:
            for calendar in account.calendars:
                if not calendar.calendar_id:
                    errors.append(
                        f"Calendar '{calendar.name}' in account '{account.name}' must have a calendar ID"
                    )
                else:
                    calendar_ids.add(calendar.calendar_id)

        # Validate sync rules
        for rule in self.sync_rules:
            # Check that source calendar exists
            source_calendar = self.get_calendar_by_label(rule.source_calendar)
            if not source_calendar:
                errors.append(
                    f"Sync rule references unknown source calendar label: {rule.source_calendar}"
                )

            # Check that all destination calendars exist
            for target in rule.destination:
                dest_calendar = self.get_calendar_by_label(target.calendar)
                if not dest_calendar:
                    errors.append(
                        f"Sync rule '{rule.id}' references unknown destination calendar label: {target.calendar}"
                    )

                # Check that source and destination are different
                if rule.source_calendar == target.calendar:
                    errors.append(
                        f"Sync rule '{rule.id}' cannot sync calendar to itself: {rule.source_calendar}"
                    )

        return errors

    def get_account(self, name: str) -> CalendarAccount | None:
        """Get account by name."""
        for account in self.accounts:
            if account.name == name:
                return account
        return None

    def get_calendar(self, account_name: str, calendar_id: str) -> Calendar | None:
        """Get calendar by account name and calendar ID."""
        for account in self.accounts:
            if account.name == account_name:
                for calendar in account.calendars:
                    if calendar.calendar_id == calendar_id:
                        return calendar
        return None

    def get_calendar_by_name(self, calendar_name: str) -> Calendar | None:
        """Get calendar by its human-readable name."""
        for account in self.accounts:
            for calendar in account.calendars:
                if calendar.name == calendar_name:
                    return calendar
        return None

    def get_calendar_by_id(self, calendar_id: str) -> Calendar | None:
        """Get calendar by its calendar ID."""
        for account in self.accounts:
            for calendar in account.calendars:
                if calendar.calendar_id == calendar_id:
                    return calendar
        return None

    def get_calendars_for_account(self, account_name: str) -> list[Calendar]:
        """Get all calendars for a specific account."""
        for account in self.accounts:
            if account.name == account_name:
                return account.calendars
        return []

    def get_all_calendars(self) -> list[Calendar]:
        """Get all calendars from all accounts."""
        all_calendars = []
        for account in self.accounts:
            all_calendars.extend(account.calendars)
        return all_calendars

    def get_account_name_for_calendar(self, calendar_id: str) -> str | None:
        """Get the account name that owns a calendar with the given ID."""
        for account in self.accounts:
            for calendar in account.calendars:
                if calendar.calendar_id == calendar_id:
                    return account.name
        return None

    def get_calendar_id_by_label(self, account_label: str) -> str | None:
        """Get the calendar ID for a given account.label format."""
        if "." not in account_label:
            return None

        account_name, label = account_label.split(".", 1)
        for account in self.accounts:
            if account.name == account_name:
                for calendar in account.calendars:
                    if calendar.label == label:
                        return calendar.calendar_id
        return None

    def get_calendar_by_label(self, account_label: str) -> Calendar | None:
        """Get a calendar by its account.label format."""
        if "." not in account_label:
            return None

        account_name, label = account_label.split(".", 1)
        for account in self.accounts:
            if account.name == account_name:
                for calendar in account.calendars:
                    if calendar.label == label:
                        return calendar
        return None

    def get_sync_rule(self, rule_id: str) -> SyncRule | None:
        """Get sync rule by ID."""
        for rule in self.sync_rules:
            if rule.id == rule_id:
                return rule
        return None

    def get_enabled_sync_rules(self) -> list[SyncRule]:
        """Get all sync rules that have at least one enabled destination."""
        enabled_rules = []
        for rule in self.sync_rules:
            if any(target.enabled for target in rule.destination):
                enabled_rules.append(rule)
        return enabled_rules

    def get_enabled_targets_for_rule(
        self, rule_or_id: SyncRule | str
    ) -> list[SyncTarget]:
        """Get all enabled targets for a specific sync rule."""
        if isinstance(rule_or_id, str):
            # If string, treat as rule ID and look it up
            rule = self.get_sync_rule(rule_or_id)
        else:
            # If already a rule object, use it directly
            rule = rule_or_id

        if rule:
            return [target for target in rule.destination if target.enabled]
        return []


def create_example_config() -> str:
    """Create an example configuration file."""
    return """# Calsinki Configuration Example

# Google Calendar accounts (authentication)
accounts:
  - name: "work"
    email: "work@company.com"
    auth_type: "oauth2"
    calendars:
      - label: "primary"
        calendar_id: "work@company.com"
        name: "Work Calendar"
        description: "Primary work calendar"
      - label: "team"
        calendar_id: "team@company.com"
        name: "Team Calendar"
        description: "Shared team events and meetings"

  - name: "personal"
    email: "personal@gmail.com"
    auth_type: "oauth2"
    calendars:
      - label: "primary"
        calendar_id: "personal@gmail.com"
        name: "Personal Calendar"
        description: "Primary personal calendar"
      - label: "family"
        calendar_id: "family@gmail.com"
        name: "Family Calendar"
        description: "Shared family events"

# Calendar synchronization rules (supports multiple targets per source)
sync_rules:
  - id: "demo1"
    source_calendar: "work.team"
    destination:
      - calendar: "work.primary"
        privacy_mode: "private"
        privacy_label: "BUSY"
        title_prefix: "[D1]"
        enabled: true
      - calendar: "personal.family"
        privacy_mode: "public"
        privacy_label: "So busy"
        title_prefix: "[DEMO]"
        title_suffix: "(sync)"
        enabled: false

# Logging configuration
log_level: "INFO"
log_file: "./logs/calsinki.log"

# Data directory for storing sync metadata
data_dir: "./data"
"""


def get_config_dir() -> Path:
    """Get the standard configuration directory."""
    xdg_config = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config:
        return Path(xdg_config) / "calsinki"
    return Path(user_config_dir("calsinki"))


def get_credentials_dir() -> Path:
    """Get the standard credentials directory."""
    xdg_data = os.environ.get("XDG_DATA_HOME")
    if xdg_data:
        return Path(xdg_data) / "calsinki" / "credentials"
    return Path(user_data_dir("calsinki")) / "credentials"


def get_default_config_path() -> Path:
    """Get the default configuration file path."""
    return get_config_dir() / "config.yaml"


def get_credentials_path(account_name: str) -> Path:
    """Get the credentials file path for a specific account."""
    return get_credentials_dir() / f"{account_name}.json"


def get_oauth2_config_path() -> Path:
    """Get the OAuth2 configuration file path in the data directory."""
    return get_credentials_dir() / "oauth2_config.yaml"


def ensure_directories():
    """Ensure that the necessary directories exist."""
    get_config_dir().mkdir(parents=True, exist_ok=True)
    get_credentials_dir().mkdir(parents=True, exist_ok=True)
