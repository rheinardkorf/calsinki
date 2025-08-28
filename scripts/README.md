# Calsinki Scripts

This folder contains utility scripts for managing and maintaining your Calsinki calendar synchronization setup.

## Available Scripts

### purge_reclaim_events.py

A comprehensive cleanup script to remove all Reclaim.ai remnant events from your Google Calendar.

#### What It Does

This script identifies and removes events that were created by Reclaim.ai calendar synchronization service. It searches for events with the metadata `reclaim.personalSync=true` in their extended properties and safely deletes them.

#### Features

- **Safe by Default**: Runs in dry-run mode by default to preview deletions
- **Recurring Event Handling**: Properly handles recurring events by deleting master events
- **Batch Processing**: Efficiently processes large calendars with thousands of events
- **Comprehensive Logging**: Provides detailed output and saves summary files
- **Error Handling**: Gracefully handles API errors and continues processing

#### Prerequisites

1. **Calsinki Setup**: Must have calsinki configured and authenticated
2. **Google Calendar Access**: Requires OAuth2 credentials for calendar accounts
3. **Python Environment**: Python 3.11+ with required dependencies

#### Installation

1. Ensure you're in the calsinki project directory
2. Activate the virtual environment:
   ```bash
   source .venv/bin/activate
   ```
3. The script is ready to use

#### Usage

##### Dry Run (Default - Safe)
```bash
python scripts/purge_reclaim_events.py
```
Shows what would be deleted without making any changes.

##### Preview Deletions
```bash
python scripts/purge_reclaim_events.py --execute
```
Shows deletions with interactive confirmation prompt.

##### Execute Deletions
```bash
python scripts/purge_reclaim_events.py --execute --force
```
Actually deletes the Reclaim events (use with caution).

#### Command Line Options

- `--execute`: Execute deletions instead of dry-run
- `--force`: Skip interactive confirmation (use with --execute)

#### Output

The script provides:
- Real-time progress updates
- Summary of events found and deleted
- Detailed summary file with timestamp
- Error reporting for failed deletions

#### Example Output

```
🔍 DRY RUN MODE - No events will be deleted
Use --execute to actually delete events
================================================================================
✅ Config loaded successfully from /Users/user/.config/calsinki/config.yaml
✅ OAuth2 config loaded successfully

📅 Processing account: work (work@company.com)
✅ Authenticated with Google Calendar API
  📋 Calendar: Work Calendar (work@company.com)
    🔍 Fetching events from 2022-08-29 to 2026-08-28
    📊 Fetched 5638 total events
    🎯 Found 3043 Reclaim events to purge
      📅 Single events: 15
      🔄 Recurring series: 14
        🗑️  Would delete: Coffee (2024-04-22)
        🔄 Would delete recurring series: Work Commitment (730 instances)

================================================================================
🔍 DRY RUN SUMMARY:
   📊 Total Reclaim events found: 3043
   🗑️  Events that would be deleted: 3043

💡 To actually delete these events, run:
   python scripts/purge_reclaim_events.py --execute --force
```

#### Safety Features

1. **Dry-Run Default**: Script defaults to safe preview mode
2. **Interactive Confirmation**: Requires typing 'DELETE' to confirm
3. **Force Flag**: Requires explicit --force flag for execution
4. **Summary Files**: Saves detailed logs for audit purposes
5. **Error Handling**: Continues processing even if individual deletions fail

#### What Gets Deleted

The script removes events with these characteristics:
- `reclaim.personalSync=true` in extended properties
- Events created by Reclaim.ai synchronization
- Both single events and recurring event series
- Events across all configured calendars

#### What Stays Safe

- Events not created by Reclaim
- Events without Reclaim metadata
- Events in calendars not configured in calsinki
- Your original calendar events

#### Troubleshooting

##### Common Issues

1. **Authentication Errors**: Run `calsinki auth` to refresh credentials
2. **Configuration Errors**: Ensure `calsinki init` has been run
3. **Permission Errors**: Check Google Calendar API permissions

##### Getting Help

- Check the calsinki configuration: `calsinki config`
- Verify OAuth2 setup: `calsinki auth --setup`
- Review the generated summary files for details

#### File Locations

- **Script**: `scripts/purge_reclaim_events.py`
- **Summary Files**: Generated in project root with timestamps
- **Configuration**: Uses calsinki config from `~/.config/calsinki/`

#### Dependencies

- `calsinki` package (local)
- `google-api-python-client`
- `google-auth-oauthlib`
- Standard Python libraries (datetime, pathlib, etc.)

## Contributing

When adding new scripts to this folder:

1. Follow the existing naming convention
2. Include comprehensive error handling
3. Add dry-run options where appropriate
4. Document usage in this README
5. Test thoroughly before committing

## License

These scripts are part of the Calsinki project and follow the same licensing terms.
