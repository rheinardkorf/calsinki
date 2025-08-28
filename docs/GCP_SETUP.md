# 🚀 Google Cloud Platform (GCP) Setup Guide for Calsinki

This guide walks you through setting up Google Cloud Platform for Calsinki, including OAuth consent screen configuration, API credentials, and test user setup.

## 📋 Prerequisites

- A Google account (personal or Google Workspace)
- Access to [Google Cloud Console](https://console.cloud.google.com/)
- Basic familiarity with Google Cloud concepts

## 🎯 What We're Setting Up

Calsinki needs access to Google Calendar APIs to:
- Read calendar events from source calendars
- Create/update/delete events in destination calendars
- Manage calendar permissions and visibility

## 🚀 Step 1: Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click **"Select a project"** in the top navigation
3. Click **"New Project"**
4. Enter a project name (e.g., "Calsinki Calendar Sync")
5. Click **"Create"**
6. Wait for the project to be created and select it

## 🔐 Step 2: Enable Google Calendar API

1. In your project, go to **"APIs & Services"** > **"Library"**
2. Search for **"Google Calendar API"**
3. Click on **"Google Calendar API"**
4. Click **"Enable"**
5. Wait for the API to be enabled

## 🎭 Step 3: Configure OAuth Consent Screen

This is where you define what your app does and what permissions it requests.

### 3.1 Access OAuth Consent Screen
1. Go to **"APIs & Services"** > **"OAuth consent screen"**
2. Click **"Get Started"**

### 3.2 App Information
1. **App name**: `Calsinki Calendar Sync`
2. **User support email**: Your email address
3. **App logo**: Optional - you can add a logo later
4. **App domain**: Leave blank for desktop apps
5. **Developer contact information**: Your email address
6. Click **"Save and Continue"**

### 3.3 Scopes Configuration
This is the most important part - we need to request the right permissions.

1. Click **"Add or Remove Scopes"**
2. Search for and add these scopes:

#### Required Scopes for Calsinki:
- **`https://www.googleapis.com/auth/calendar`** - Full access to Google Calendar
  - This allows reading and writing calendar events
  - Required for sync operations

#### Alternative (More Restrictive) Scopes:
If you prefer minimal permissions, you can use these instead:
- **`https://www.googleapis.com/auth/calendar.events`** - Access to calendar events only
- **`https://www.googleapis.com/auth/calendar.readonly`** - Read-only access (for testing)

**Note**: The full calendar scope is recommended for Calsinki as it needs to create, update, and delete events.

3. Click **"Update"**
4. Click **"Save and Continue"**

### 3.4 Test Users
Since Calsinki is a desktop app, you'll need to add test users:

**Note**: To add test users, navigate to **"APIs & Services"** > **"OAuth consent screen"** > **"Audience"**

1. Click **"Add Users"**
2. Add your Google account email address
3. Add any other Google accounts you want to test with
4. Click **"Save and Continue"**

### 3.5 Review and Publish
1. Review your configuration
2. Click **"Back to Dashboard"**

## 🔑 Step 4: Create OAuth 2.0 Credentials

Now we need to create the credentials that Calsinki will use to authenticate.

### 4.1 Create Credentials
1. Go to **"APIs & Services"** > **"Credentials"**
2. Click **"Create Credentials"** > **"OAuth 2.0 Client IDs"**

### 4.2 Application Type
1. **Application type**: Select **"Desktop application"**
2. **Name**: `Calsinki Desktop Client`
3. Click **"Create"**

### 4.3 Download Credentials
1. A popup will appear with your client ID and client secret
2. **Important**: Download the JSON file or copy the credentials
3. Click **"OK"**

## 📁 Step 5: Configure Calsinki with Your Credentials

Now you need to tell Calsinki about your OAuth credentials.

### 5.1 Initialize Calsinki
```bash
calsinki init
```

### 5.2 Set Up OAuth Configuration
```bash
calsinki auth --setup
```

This command creates a template OAuth2 configuration file that you'll need to edit manually.

### 5.3 Edit the OAuth2 Configuration File
The `calsinki auth --setup` command will show you the path to the created file. You need to edit this file and add your credentials:

1. **Open the OAuth2 config file** (usually located in `~/.local/share/calsinki/credentials/oauth2_config.yaml`)
2. **Replace the placeholder values** with your actual credentials:
   ```yaml
   google_oauth2:
     client_id: "your-actual-client-id.apps.googleusercontent.com"
     client_secret: "your-actual-client-secret"
     scopes:
       - "https://www.googleapis.com/auth/calendar"
   ```
3. **Save the file**

## 🧪 Step 6: Test Authentication

Let's verify everything is working:

```bash
calsinki auth
```

This should:
1. Display a QR code
2. Open a browser window (or you can scan the QR code with your phone)
3. Ask you to sign in to your Google account
4. Show a consent screen with the permissions we configured
5. Complete the authentication

## 🔒 Step 7: Security Best Practices

### 7.1 Keep Credentials Secure
- **Never commit** OAuth credentials to version control
- Store them in the secure location Calsinki creates (`$XDG_DATA_HOME/calsinki/credentials/`)
- Use different credentials for development and production

### 7.2 Monitor API Usage
1. Go to **"APIs & Services"** > **"Dashboard"**
2. Check **"Google Calendar API"** usage
3. Monitor for any unusual activity

### 7.3 Regular Credential Rotation
- Consider rotating OAuth credentials periodically
- Monitor for any security alerts from Google

## 🚨 Troubleshooting

### Common Issues and Solutions

#### "Invalid Credentials" Error
- Verify your client ID and client secret are correct
- Ensure you copied them exactly from the Google Cloud Console
- Check that the credentials are for a "Desktop application"

#### "Access Denied" Error
- Verify the Google Calendar API is enabled
- Check that your OAuth consent screen is properly configured
- Ensure your account is added as a test user

#### "Scope Not Allowed" Error
- Verify the required scopes are added to your OAuth consent screen
- Check that you're using the correct scope URLs
- Ensure the scopes are saved and published

#### Authentication Fails
- Clear any existing OAuth tokens: `rm -rf ~/.local/share/calsinki/credentials/`
- Re-run `calsinki auth --setup` to recreate the template file
- Edit the OAuth2 config file with your correct credentials
- Check that your Google account has 2FA properly configured

## 📚 Additional Resources

- [Google Calendar API Documentation](https://developers.google.com/calendar/api)
- [OAuth 2.0 Scopes for Google APIs](https://developers.google.com/identity/protocols/oauth2/scopes)
- [Google Cloud Console](https://console.cloud.google.com/)
- [Google Workspace Developer Hub](https://developers.google.com/workspace)

## 🎉 Next Steps

Once you've completed this setup:

1. **Configure your sync pairs** in `~/.config/calsinki/config.yaml`
2. **Test with a simple sync** using `calsinki sync --dry-run`
3. **Set up automated syncing** with cron or systemd timers
4. **Monitor your syncs** and adjust configuration as needed

## 🆘 Need Help?

If you encounter issues:

1. Check the [troubleshooting section](#-troubleshooting) above
2. Review the [main README](../README.md) for command usage
3. Check Calsinki logs for detailed error messages
4. Verify your Google Cloud Console configuration matches this guide

---

*This guide covers the essential GCP setup for Calsinki. For advanced configuration options or enterprise features, refer to the [Google Workspace documentation](https://developers.google.com/workspace/guides/configure-oauth-consent).*
