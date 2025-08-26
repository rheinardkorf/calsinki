# 🗓️ Calsinki

> *"Because your calendars deserve to work together in perfect sync"*

A self-hosted calendar synchronization service that keeps your multiple Google Calendars in perfect harmony without compromising your privacy.

## 🎯 What Does Calsinki Do?

Calsinki is your personal calendar conductor, orchestrating events between multiple Google Calendar accounts with style and discretion. Think of it as a diplomatic ambassador between your work calendar, personal calendar, and any other calendars you juggle.

### ✨ Key Features

- **🎭 Multi-Account Harmony**: Sync between multiple Google Calendar accounts seamlessly
- **🔒 Privacy First**: Uses Google Calendar's native visibility settings (public/private) for smart privacy control
- **🔄 Smart Sync**: Automatically detects and updates existing events, preventing duplicates
- **📱 Mobile-Friendly Auth**: QR code authentication for easy setup on headless servers
- **🏠 Homelab Ready**: Designed to run on your own infrastructure, not in the cloud
- **🏷️ Custom Labels**: Configurable privacy labels for anonymous events with optional time display

## 🚀 Why Calsinki?

- **Self-hosted**: Your calendar data stays on your infrastructure
- **Privacy control**: Automatically respects Google Calendar visibility settings
- **No vendor lock-in**: You control the sync logic and data flow
- **Lightweight**: Minimal dependencies, runs on minimal Linux environments
- **Automated**: Set it and forget it with cron or systemd timers

## 🚀 Getting Started

1. **Clone and Setup**: `git clone <repo>` then `uv venv` and `source .venv/bin/activate`
2. **Install Dependencies**: `uv sync` to install all required packages
3. **Initialize**: `calsinki init` to create your configuration structure
4. **Configure**: Edit the generated config file with your calendar details
5. **Authenticate**: `calsinki auth <account_name>` to set up Google Calendar access
6. **Sync**: `calsinki sync` or `calsinki sync <pair_id>` to start calendar synchronization

## 📁 Configuration & Storage

Calsinki follows the XDG Base Directory Specification for configuration and data storage:

- **Configuration**: `$XDG_CONFIG_HOME/calsinki/config.yaml` (safe to commit to dotfiles)
  Default locations:
  - Linux: `~/.config/calsinki/config.yaml`
  - macOS: `~/Library/Application Support/calsinki/config.yaml`
  - Windows: `%APPDATA%\calsinki\config.yaml`
- **OAuth2 Config**: `$XDG_CONFIG_HOME/calsinki/oauth2_config.yaml` (contains Google API credentials)
- **Credentials**: `$XDG_DATA_HOME/calsinki/credentials/` (never commit - contains OAuth2 tokens)
  Default locations:
  - Linux: `~/.local/share/calsinki/credentials/`
  - macOS: `~/Library/Application Support/calsinki/credentials/`
  - Windows: `%LOCALAPPDATA%\calsinki\credentials\`
- **Data**: `$XDG_DATA_HOME/calsinki/data/` (sync metadata and logs)

If you have custom XDG paths set (e.g., `XDG_CONFIG_HOME=~/.config`), Calsinki will respect them automatically. Otherwise, it uses your operating system's default application directories.

## 🏗️ Architecture

Calsinki is built as a Python command-line tool that:
1. Reads configuration from a simple YAML file
2. Authenticates with Google Calendar APIs using OAuth2 device flow
3. Syncs events between source and destination calendars with privacy controls
4. Maintains sync metadata for reliable updates and duplicate prevention
5. Runs automatically on your schedule

## 🛠️ Tech Stack

- **Python 3.11+**: Core application logic
- **Google Calendar API**: Calendar operations and event management
- **OAuth2 Device Flow**: Secure authentication for headless environments
- **YAML**: Human-readable configuration
- **uv**: Fast Python package management
- **QR Codes**: Easy mobile authentication setup

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
- [ ] Cron/systemd integration
- [ ] Docker containerization
- [ ] Monitoring and health checks

## 🤝 Contributing

This is a personal project, but if you find it useful and want to contribute, feel free to open issues or submit pull requests!

## 📄 License

MIT License - because sharing is caring! ❤️

---

*Built in 🇦🇺 with ❤️ for people who love their calendars but hate vendor lock-in*
