"""OAuth2 authentication for Calsinki calendar synchronization service."""

import json
import os
from dataclasses import dataclass, field

import qrcode
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from .config import get_credentials_path, get_oauth2_config_path


@dataclass
class OAuth2Config:
    """OAuth2 configuration for Google API authentication."""

    client_id: str
    client_secret: str
    scopes: list[str] = field(
        default_factory=lambda: [
            "https://www.googleapis.com/auth/calendar.readonly",  # Read calendar metadata and events
            "https://www.googleapis.com/auth/calendar.events",  # Read/write calendar events
        ]
    )


class GoogleAuthenticator:
    """Handles Google OAuth2 authentication for calendar access."""

    def __init__(self, account_name: str, oauth2_config: OAuth2Config):
        self.account_name = account_name
        self.oauth2_config = oauth2_config
        self.credentials_path = get_credentials_path(account_name)

    def authenticate(self) -> Credentials:
        """Authenticate with Google using OAuth2 device flow."""
        credentials = self._load_existing_credentials()

        if credentials and credentials.valid:
            return credentials

        if credentials and credentials.expired and credentials.refresh_token:
            try:
                credentials.refresh(Request())
                self._save_credentials(credentials)
                return credentials
            except RefreshError:
                print(
                    f"⚠️  Refresh token expired for {self.account_name}, re-authenticating..."
                )

        return self._perform_device_flow()

    def _load_existing_credentials(self) -> Credentials | None:
        """Load existing credentials from file."""
        if not self.credentials_path.exists():
            return None

        try:
            with open(self.credentials_path) as f:
                creds_data = json.load(f)
            return Credentials.from_authorized_user_info(creds_data)
        except Exception as e:
            print(f"⚠️  Error loading credentials for {self.account_name}: {e}")
            return None

    def _save_credentials(self, credentials: Credentials):
        """Save credentials to file."""
        self.credentials_path.parent.mkdir(parents=True, exist_ok=True)

        creds_data = {
            "token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "scopes": credentials.scopes,
        }

        with open(self.credentials_path, "w") as f:
            json.dump(creds_data, f, indent=2)

        # Set restrictive permissions on credentials file
        os.chmod(self.credentials_path, 0o600)

    def _perform_device_flow(self) -> Credentials:
        """Perform OAuth2 authentication for desktop applications using base Flow class."""
        print(f"🔐 Starting OAuth2 authentication for {self.account_name}...")

        # For desktop apps, use the base Flow class to have full control
        from google_auth_oauthlib.flow import Flow

        flow = Flow.from_client_config(
            {
                "installed": {
                    "client_id": self.oauth2_config.client_id,
                    "client_secret": self.oauth2_config.client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob"],
                }
            },
            scopes=self.oauth2_config.scopes,
        )

        # Set the redirect URI explicitly
        flow.redirect_uri = "urn:ietf:wg:oauth:2.0:oob"

        # Get authorization URL
        auth_url, _ = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",  # Force consent screen to get refresh token
        )

        # Generate QR code for mobile authentication
        self._display_qr_code(auth_url)

        print("\n📱 Scan the QR code above with your mobile device")
        print(f"🔗 Or visit this URL manually: {auth_url}")
        print("\n💡 Complete the authentication on your device")
        print(
            "⚠️  Note: You may see an error about redirect_uri - this is expected for mobile auth"
        )
        print("    The important thing is that you complete the Google sign-in process")
        print(
            "    After completing auth, you'll get an authorization code - copy it and paste it here"
        )

        # For desktop apps with urn:ietf:wg:oauth:2.0:oob, we need to handle the code manually
        auth_code = input("\n📝 Enter the authorization code from Google: ").strip()

        if not auth_code:
            raise Exception("No authorization code provided")

        try:
            # Exchange authorization code for credentials
            flow.fetch_token(code=auth_code)
            credentials = flow.credentials

            # Save credentials for future use
            self._save_credentials(credentials)

            print(f"✅ Authentication successful for {self.account_name}!")
            return credentials

        except Exception as e:
            print(f"❌ Authentication failed for {self.account_name}: {e}")
            raise

    def _try_local_server_flow(self) -> Credentials:
        """Fallback to local server flow for desktop applications."""
        # This method is no longer needed as we use the correct installed app flow
        pass

    def _display_qr_code(self, auth_url: str):
        """Display QR code containing the authorization URL."""
        try:
            # Generate QR code
            qr = qrcode.QRCode(version=1, box_size=2, border=2)
            qr.add_data(auth_url)
            qr.make(fit=True)

            # Display QR code in terminal using qrcode's built-in method
            print("📱 QR Code for Mobile Authentication:")
            print("=" * 50)
            qr.print_ascii(invert=True)
            print("=" * 50)
            print("📱 Scan this QR code with your mobile device")

        except Exception as e:
            print(f"⚠️  Could not generate QR code: {e}")
            print(f"🔗 Please visit this URL manually: {auth_url}")

    def _display_terminal_qr(self, qr):
        """Display QR code in terminal using ASCII art."""
        # This method is no longer needed as we use qrcode's built-in display
        pass


def create_oauth2_config_file():
    """Create a template OAuth2 configuration file."""
    config_path = get_oauth2_config_path()

    template = """# OAuth2 Configuration for Google Calendar API
# Copy this file and fill in your Google Cloud Console credentials

google_oauth2:
  client_id: "your-client-id.apps.googleusercontent.com"
  client_secret: "your-client-secret"
  scopes:
    - "https://www.googleapis.com/auth/calendar.readonly"
    - "https://www.googleapis.com/auth/calendar.events"
"""

    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w") as f:
        f.write(template)

    return config_path


def load_oauth2_config() -> OAuth2Config | None:
    """Load OAuth2 configuration from file."""
    import yaml

    config_path = get_oauth2_config_path()

    if not config_path.exists():
        print(f"⚠️  OAuth2 configuration not found at {config_path}")
        print("💡 Run 'calsinki auth --setup' to create the configuration file")
        return None

    try:
        with open(config_path) as f:
            config_data = yaml.safe_load(f)

        oauth2_data = config_data.get("google_oauth2", {})
        return OAuth2Config(
            client_id=oauth2_data["client_id"],
            client_secret=oauth2_data["client_secret"],
            scopes=oauth2_data.get("scopes", None),
        )
    except Exception as e:
        print(f"❌ Error loading OAuth2 configuration: {e}")
        return None
