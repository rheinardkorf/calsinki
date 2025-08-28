# 🗓️ Calsinki

> *"Because your calendars deserve to work together in perfect sync"*

A self-hosted calendar synchronization service that keeps your multiple Google Calendars in perfect harmony without compromising your privacy.

## 🎯 What Does Calsinki Do?

Calsinki is your personal calendar conductor, orchestrating events between multiple Google Calendar accounts with style and discretion. Think of it as a diplomatic ambassador between your work calendar, personal calendar, and any other calendars you juggle.

### ✨ Key Features

- **🎭 Multi-Account Harmony**: Sync between multiple Google Calendar accounts seamlessly
- **🔒 Privacy First**: Uses Google Calendar's native visibility settings (public/private) for smart privacy control
- **🔄 Smart Sync**: Automatically detects and updates existing events, preventing duplicates
- **🗑️ Event Lifecycle Management**: Automatically removes events deleted from source calendars
- **🏷️ Custom Labels**: Configurable privacy labels for anonymous events with optional time display
- **🔍 Safe Preview**: Dry-run mode for both sync and purge operations
- **🧹 Cleanup Tools**: Purge synced events with granular control
- **📱 Mobile-Friendly Auth**: QR code authentication for easy setup on headless servers
- **🏠 Homelab Ready**: Designed to run on your own infrastructure, not in the cloud

## 🚀 Why Calsinki?

- **Self-hosted**: Your calendar data stays on your infrastructure
- **Privacy control**: Automatically respects Google Calendar visibility settings
- **No vendor lock-in**: You control the sync logic and data flow
- **Lightweight**: Minimal dependencies, runs on minimal Linux environments
- **Automated**: Set it and forget it with cron or systemd timers
- **Safe operations**: Dry-run mode prevents accidental changes
- **Complete lifecycle**: Handles creation, updates, and deletion of events

## 🚀 Getting Started

1. **Clone and Setup**: `git clone <repo>` then `uv venv` and `source .venv/bin/activate`
2. **Install Dependencies**: `uv sync` to install all required packages
3. **GCP Setup**: Follow the [GCP Setup Guide](docs/GCP_SETUP.md) to configure Google Cloud Platform and OAuth2
4. **Initialize**: `calsinki init` to create your configuration structure
5. **Configure**: Edit the generated config file with your calendar details
6. **Authenticate**: `calsinki auth <account_name>` to set up Google Calendar access
7. **Sync**: `calsinki sync` or `calsinki sync <pair_id>` to start calendar synchronization

## 🎮 Command Reference

### Core Commands
```bash
calsinki init                    # Initialize configuration structure
calsinki auth --setup            # Set up OAuth2 configuration (requires GCP setup first)
calsinki auth                    # Authenticate all accounts
calsinki auth personal           # Authenticate specific account
calsinki config                  # Show current configuration
calsinki config --example        # Show example configuration
```

**Note**: Before running `calsinki auth --setup`, you must complete the [GCP Setup Guide](docs/GCP_SETUP.md) to configure Google Cloud Platform and OAuth2 credentials.

### Synchronization
```bash
calsinki sync                    # Sync all enabled sync pairs
calsinki sync --dry-run          # Preview sync without making changes
calsinki sync demo_to_personal   # Sync specific sync pair
calsinki sync --list             # List available sync pairs
```

### Event Management
```bash
calsinki purge demo_to_personal  # Remove events from specific sync pair
calsinki purge --all             # Remove all synced events from all pairs
calsinki purge --dry-run         # Show what would be purged
```

### Safe Operations
Both `sync` and `purge` commands support `--dry-run` mode for safe previewing:
- **Sync dry-run**: Shows what events would be synced without modifying calendars
- **Purge dry-run**: Shows what events would be deleted without removing them

## 📁 Configuration & Storage

Calsinki follows the XDG Base Directory Specification for configuration and data storage:

- **Configuration**: `$XDG_CONFIG_HOME/calsinki/config.yaml` (safe to commit to dotfiles)
  Default locations:
  - Linux: `~/.config/calsinki/config.yaml`
  - macOS: `~/Library/Application Support/calsinki/config.yaml`
  - Windows: `%APPDATA%\calsinki\config.yaml`
- **OAuth2 Config**: `$XDG_DATA_HOME/calsinki/credentials/oauth2_config.yaml` (contains Google API credentials - never commit)
- **Credentials**: `$XDG_DATA_HOME/calsinki/credentials/` (never commit - contains OAuth2 tokens)
  Default locations:
  - Linux: `~/.local/share/calsinki/credentials/`
  - macOS: `~/Library/Application Support/calsinki/credentials/`
  - Windows: `%LOCALAPPDATA%\calsinki\credentials\`
- **Data**: `$XDG_DATA_HOME/calsinki/data/` (sync metadata and logs)

If you have custom XDG paths set (e.g., `XDG_CONFIG_HOME=~/.config`), Calsinki will respect them automatically. Otherwise, it uses your operating system's default application directories.

### 🔒 Security & Privacy
- **Configuration files** (`config.yaml`) are safe to commit to dotfiles
- **OAuth2 credentials** and **API keys** are stored in `$XDG_DATA_HOME` (never commit)
- **Sync metadata** is stored in destination events (Google Calendar handles privacy)
- **No sensitive data** is logged or transmitted beyond Google's secure APIs

## 🎨 Event Customization

Calsinki allows you to customize how synced events appear in your destination calendars:

### Title Customization
- **Prefix**: Add text before event titles (e.g., `[WORK]`, `TEAM:`)
- **Suffix**: Add text after event titles (e.g., `(synced)`, `[external]`)

### Event Colors
You can assign specific colors to synced events using Google Calendar's color IDs:

| Color ID | Color Name | Description |
|----------|------------|-------------|
| `"1"` | Lavender | Soft purple |
| `"2"` | Sage | Muted green |
| `"3"` | Grape | Rich purple |
| `"4"` | Flamingo | Bright pink |
| `"5"` | Banana | Light yellow |
| `"6"` | Tangerine | Bright orange |
| `"7"` | Peacock | Teal blue |
| `"8"` | Graphite | Dark gray |
| `"9"` | Blueberry | Deep blue |
| `"10"` | Basil | Forest green |
| `"11"` | Tomato | Bright red |

**Note**: Leave `event_color` empty (`""`) or omit the field to use the destination calendar's default color.

### Sync Metadata
Calsinki automatically adds comprehensive metadata to all synced events:

- **`last_synced`**: ISO timestamp of when the event was last synchronized
- **`last_sync_human`**: Human-readable timestamp (e.g., "2025-01-27 14:30:45 UTC")
- **`sync_count`**: Number of times the event has been synchronized
- **`source_calendar_id`**: ID of the source calendar
- **`source_event_id`**: Original event ID from the source calendar
- **`sync_version`**: Version of the sync metadata format

This metadata is stored in the event's extended properties and can be viewed in Google Calendar's event details.

### Bi-Directional Sync Protection
Calsinki automatically prevents infinite sync loops when using bi-directional sync pairs. If you set up sync pairs in both directions (e.g., `personal_to_work` and `work_to_personal`), Calsinki will:

- **Detect Calsinki-synced events** in source calendars
- **Skip syncing** events that already have Calsinki metadata
- **Prevent loops** from creating endless event duplication
- **Log skips** for debugging and monitoring

This ensures safe bi-directional synchronization without manual intervention.

### Example Configuration
```yaml
sync_pairs:
  - id: "work_to_personal"
    source_calendar: "work@company.com"
    destination_calendar: "personal@gmail.com"
    privacy_mode: "private"
    title_prefix: "[WORK]"
    title_suffix: "(synced)"
    event_color: "3"  # Grape color
    enabled: true
```

## 🏗️ Architecture

Calsinki is built as a Python command-line tool that:
1. Reads configuration from a simple YAML file
2. Authenticates with Google Calendar APIs using OAuth2 device flow
3. Syncs events between source and destination calendars with privacy controls
4. Maintains sync metadata for reliable updates and duplicate prevention
5. Automatically handles event lifecycle (creation, updates, deletion)
6. Provides safe preview modes for all operations
7. Runs automatically on your schedule

## 🛠️ Tech Stack

- **Python 3.11+**: Core application logic
- **Google Calendar API**: Calendar operations and event management
- **OAuth2 Device Flow**: Secure authentication for headless environments
- **YAML**: Human-readable configuration
- **uv**: Fast Python package management
- **QR Codes**: Easy mobile authentication setup
- **Dataclasses**: Clean, type-safe data structures

## 🎭 The Name

"Calsinki" combines "Calendar" with "Synchronization" - because every great tool needs a memorable name that rolls off the tongue. Plus, it sounds like a Finnish city, which adds that extra touch of Nordic efficiency!

## 🔮 Roadmap

- [x] Core sync functionality with Google Calendar API
- [x] OAuth2 authentication with QR codes and device flow
- [x] Configuration management with YAML
- [x] Error handling and logging
- [x] Privacy modes (public/private) with Google Calendar visibility integration
- [x] Duplicate prevention and smart event updates
- [x] Custom privacy labels and time display options
- [x] Event deletion synchronization
- [x] Purge functionality with safety controls
- [x] Dry-run mode for safe operations
- [x] Custom event title prefixes/suffixes per sync pair
- [x] Destination event color customization per sync pair
- [x] Sync timestamps and metadata tracking

## 🤝 Contributing

This is a personal project, but if you find it useful and want to contribute, feel free to open issues or submit pull requests!

## 📄 License

MIT License - because sharing is caring! ❤️

---

*Built in 🇦🇺 with ❤️ for people who love their calendars but hate vendor lock-in*
