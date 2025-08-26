# 🗓️ Calsinki

> *"Because your calendars deserve to work together in perfect sync"*

A self-hosted calendar synchronization service that keeps your multiple Google Calendars in perfect harmony without compromising your privacy.

## 🎯 What Does Calsinki Do?

Calsinki is your personal calendar conductor, orchestrating events between multiple Google Calendar accounts with style and discretion. Think of it as a diplomatic ambassador between your work calendar, personal calendar, and any other calendars you juggle.

### ✨ Key Features

- **🎭 Multi-Account Harmony**: Sync between multiple Google Calendar accounts seamlessly
- **🔒 Privacy First**: Option to strip sensitive details when syncing to destination calendars
- **🔄 Smart Sync**: Automatically updates and deletes events when source calendars change
- **📱 Mobile-Friendly Auth**: QR code authentication for easy setup on headless servers
- **🏠 Homelab Ready**: Designed to run on your own infrastructure, not in the cloud

## 🚀 Why Calsinki?

- **Self-hosted**: Your calendar data stays on your infrastructure
- **Privacy control**: Choose what information gets synced where
- **No vendor lock-in**: You control the sync logic and data flow
- **Lightweight**: Minimal dependencies, runs on minimal Linux environments
- **Automated**: Set it and forget it with cron or systemd timers

## 🚀 Getting Started

1. **Install Calsinki**: `pip install calsinki` or clone and run `uv pip install -e .`
2. **Initialize**: `calsinki init` to create your configuration structure
3. **Configure**: Edit the generated config file with your calendar details
4. **Authenticate**: `calsinki auth` to set up Google Calendar access
5. **Sync**: `calsinki sync` to start calendar synchronization

## 📁 Configuration & Storage

Calsinki follows the XDG Base Directory Specification for configuration and data storage:

- **Configuration**: `$XDG_CONFIG_HOME/calsinki/config.yaml` (safe to commit to dotfiles)
  Default locations:
  - Linux: `~/.config/calsinki/config.yaml`
  - macOS: `~/Library/Application Support/calsinki/config.yaml`
  - Windows: `%APPDATA%\calsinki\config.yaml`
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
2. Authenticates with Google Calendar APIs using OAuth2
3. Syncs events between source and destination calendars
4. Maintains sync metadata for reliable updates and deletions
5. Runs automatically on your schedule

## 🛠️ Tech Stack

- **Python**: Core application logic
- **Google Calendar API**: Calendar operations
- **OAuth2**: Secure authentication
- **YAML**: Human-readable configuration
- **uv**: Fast Python package management
- **QR Codes**: Easy mobile authentication

## 🎭 The Name

"Calsinki" combines "Calendar" with "Synchronization" - because every great tool needs a memorable name that rolls off the tongue. Plus, it sounds like a Finnish city, which adds that extra touch of Nordic efficiency!

## 🔮 Roadmap

- [ ] Core sync functionality
- [ ] OAuth2 authentication with QR codes
- [ ] Configuration management
- [ ] Error handling and logging
- [ ] Cron/systemd integration
- [ ] Docker containerization
- [ ] Monitoring and health checks

## 🤝 Contributing

This is a personal project, but if you find it useful and want to contribute, feel free to open issues or submit pull requests!

## 📄 License

MIT License - because sharing is caring! ❤️

---

*Built in 🇦🇺 with ❤️ for people who love their calendars but hate vendor lock-in*
