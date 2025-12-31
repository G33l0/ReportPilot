# ReportPilot - Activity Reporting Automation System

A comprehensive, cross-platform Python automation system for compiling activity data and generating weekly reports with automatic delivery.

## Features

- **Multiple Data Sources**: Ingest from CSV, Excel, APIs, and folders
- **Intelligent Data Cleaning**: Automated validation, deduplication, and normalization
- **Weekly Summaries**: Calculate totals, averages, trends, and counts automatically
- **Professional Reports**: Generate both Excel and PDF reports with charts
- **Automated Delivery**: Send reports via email (SMTP) and Slack
- **Flexible Scheduling**: Use cron-style or interval-based scheduling
- **Cross-Platform**: Works on Windows, macOS, and Linux
- **Modular Architecture**: Clean separation of concerns for easy extension

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Data Sources](#data-sources)
- [Running the System](#running-the-system)
- [Scheduling](#scheduling)
- [Notifications](#notifications)
- [Extending the System](#extending-the-system)
- [Project Structure](#project-structure)
- [Troubleshooting](#troubleshooting)

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Step 1: Clone or Download

```bash
cd ReportPilot
```

### Step 2: Create Virtual Environment (Recommended)

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

## Quick Start

### 1. Run with Sample Data

The system comes with sample data ready to use:

```bash
python run.py
```

This will:
- Read sample data from `data/input/sample_data.csv`
- Clean and process the data
- Generate weekly summaries
- Create Excel and PDF reports in `data/output/`

### 2. View Generated Reports

Check the `data/output/` directory for:
- `activity_report_YYYYMMDD_HHMMSS.xlsx` - Excel report with charts
- `activity_report_YYYYMMDD_HHMMSS.pdf` - PDF report with tables

## Configuration

### Basic Configuration

1. Copy the example config file (if needed):
```bash
cp config/config.yaml.example config/config.yaml
```

2. Edit `config/config.yaml` to customize:
   - Data sources
   - Cleaning rules
   - Report settings
   - Output directory

### Environment Variables (Secrets)

1. Copy the example environment file:
```bash
cp config/.env.example .env
```

2. Edit `.env` with your credentials:
```env
# Email Configuration
REPORTPILOT_SMTP_HOST=smtp.gmail.com
REPORTPILOT_SMTP_PORT=587
REPORTPILOT_FROM_EMAIL=your-email@example.com
REPORTPILOT_EMAIL_PASSWORD=your-app-password

# Slack Configuration
REPORTPILOT_SLACK_BOT_TOKEN=xoxb-your-bot-token
```

**Note**: Never commit `.env` to version control!

## Data Sources

### CSV Files

```yaml
data_sources:
  - type: csv
    enabled: true
    path: data/input/activities.csv
    encoding: utf-8
    delimiter: ','
```

### Excel Files

```yaml
data_sources:
  - type: excel
    enabled: true
    path: data/input/activities.xlsx
    sheet_name: 'Weekly Data'  # or use index: 0
```

### Folder (Multiple Files)

```yaml
data_sources:
  - type: folder
    enabled: true
    path: data/input/daily/
    pattern: '*.csv'
    recursive: false
```

### REST APIs

```yaml
data_sources:
  - type: api
    enabled: true
    url: https://api.example.com/activities
    auth_type: bearer
    auth_token: ${REPORTPILOT_API_TOKEN}
    data_path: data.items
```

**Supported auth types:**
- `bearer` - Bearer token authentication
- `basic` - Basic authentication (username/password)
- `api_key` - API key in X-API-Key header
- `null` - No authentication

## Running the System

### One-Time Execution

Run the report generation once and exit:

```bash
python run.py
```

### Scheduled Execution

Run continuously with automatic scheduling:

```bash
python run.py --schedule
```

### Run Now + Schedule

Execute immediately, then continue with schedule:

```bash
python run.py --schedule --now
```

### Custom Config File

Use a different configuration file:

```bash
python run.py --config config/production.yaml
```

## Scheduling

### Cron-Style Scheduling

Run every Monday at 9:00 AM:

```yaml
schedule:
  type: cron
  cron:
    day_of_week: mon
    hour: 9
    minute: 0
```

**Day of week options**: mon, tue, wed, thu, fri, sat, sun

### Interval-Based Scheduling

Run every week:

```yaml
schedule:
  type: interval
  interval:
    weeks: 1
    days: 0
    hours: 0
    minutes: 0
```

**Note**: The system uses APScheduler, not OS-specific schedulers (cron/Task Scheduler), making it fully cross-platform.

## Notifications

### Email Notifications

1. Enable email in `config/config.yaml`:
```yaml
email:
  enabled: true
  recipients:
    - team@example.com
  subject: "Weekly Activity Report - {date}"
```

2. Set credentials in `.env`:
```env
REPORTPILOT_SMTP_HOST=smtp.gmail.com
REPORTPILOT_SMTP_PORT=587
REPORTPILOT_FROM_EMAIL=your-email@example.com
REPORTPILOT_EMAIL_PASSWORD=your-app-password
```

**Gmail Users**: Use an [App Password](https://support.google.com/accounts/answer/185833), not your regular password.

### Slack Notifications

#### Method 1: Bot Token (Recommended)

Supports file uploads and rich formatting.

1. Create a Slack App at https://api.slack.com/apps
2. Add OAuth scopes: `chat:write`, `files:write`
3. Install app to workspace
4. Copy Bot Token (starts with `xoxb-`)

```env
REPORTPILOT_SLACK_BOT_TOKEN=xoxb-your-bot-token
```

```yaml
slack:
  enabled: true
  default_channel: '#reports'
```

#### Method 2: Webhook URL (Simpler)

Simpler setup but no file uploads.

1. Create Incoming Webhook at https://api.slack.com/messaging/webhooks
2. Copy webhook URL

```env
REPORTPILOT_SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

## Extending the System

### Adding a New Data Source

1. Create a new reader in `src/ingestion/`:

```python
from .base import DataReader
import pandas as pd

class CustomReader(DataReader):
    def validate_config(self):
        # Validate required config keys
        pass

    def read(self) -> pd.DataFrame:
        # Implement data reading logic
        return df
```

2. Register in `src/ingestion/__init__.py`:

```python
from .custom_reader import CustomReader
__all__ = [..., 'CustomReader']
```

3. Add to main.py data source selection:

```python
elif source_type == 'custom':
    reader = CustomReader(source_config)
```

4. Use in configuration:

```yaml
data_sources:
  - type: custom
    enabled: true
    # your custom config here
```

### Adding Custom Cleaning Rules

```yaml
cleaning:
  custom_rules:
    - column: value
      condition: '>'
      value: 0
    - column: status
      condition: 'in'
      value: ['Completed', 'In Progress']
```

**Supported conditions**: `>`, `<`, `>=`, `<=`, `==`, `!=`, `in`, `not_in`

## Project Structure

```
ReportPilot/
├── config/
│   ├── .env.example          # Environment variables template
│   ├── config.yaml           # Working configuration
│   └── config.yaml.example   # Configuration template
├── data/
│   ├── input/                # Input data files
│   │   └── sample_data.csv
│   └── output/               # Generated reports
├── logs/                     # Application logs
├── src/
│   ├── ingestion/           # Data source readers
│   │   ├── base.py          # Base reader interface
│   │   ├── csv_reader.py
│   │   ├── excel_reader.py
│   │   ├── api_reader.py
│   │   └── folder_reader.py
│   ├── cleaning/            # Data cleaning
│   │   └── cleaner.py
│   ├── aggregation/         # Data summarization
│   │   └── summarizer.py
│   ├── reporting/           # Report generation
│   │   ├── excel_generator.py
│   │   └── pdf_generator.py
│   ├── notification/        # Delivery systems
│   │   ├── email_sender.py
│   │   └── slack_sender.py
│   ├── utils/               # Utilities
│   │   ├── config_loader.py
│   │   └── logger.py
│   └── main.py              # Main orchestration
├── run.py                    # Entry point with scheduler
├── requirements.txt          # Python dependencies
└── README.md                # This file
```

## Data Format Requirements

### Input Data

Your data should include at minimum:
- **date column**: For time-based grouping (e.g., `date`, `timestamp`)
- **metric columns**: Numeric values to summarize (e.g., `value`, `count`, `duration`)
- **category columns**: For grouping (e.g., `activity`, `user`, `category`)

### Example CSV:

```csv
date,activity,category,value,count,duration
2025-01-01,Code Review,Development,5,3,120
2025-01-01,Bug Fix,Development,8,2,180
2025-01-02,Testing,QA,10,6,200
```

## Troubleshooting

### Import Errors

**Error**: `ModuleNotFoundError: No module named 'pandas'`

**Solution**: Install dependencies:
```bash
pip install -r requirements.txt
```

### Configuration Not Found

**Error**: `Configuration file not found: config/config.yaml`

**Solution**: The working config.yaml should already exist, but you can copy from example:
```bash
cp config/config.yaml.example config/config.yaml
```

### Email Sending Fails

**Common issues**:
1. **Gmail**: Use App Password, not regular password
2. **Corporate email**: May need different SMTP settings
3. **Port blocked**: Try port 465 (SSL) instead of 587 (TLS)

### Slack Messages Not Sending

**Check**:
1. Token starts with `xoxb-` for bot token
2. Bot has been added to the channel
3. Channel name includes `#` (e.g., `#reports`)

### No Data in Reports

**Check**:
1. Data source file exists and has data
2. `date` column exists and is properly formatted
3. Check `logs/activity_reporter.log` for errors

### Scheduler Not Working

**Verify**:
1. Using `--schedule` flag: `python run.py --schedule`
2. Check schedule configuration in `config.yaml`
3. Process is running (not exited)

## Logs

All activity is logged to `logs/activity_reporter.log`:

```bash
# View recent logs (macOS/Linux)
tail -f logs/activity_reporter.log

# Windows
type logs\activity_reporter.log
```

## Performance Tips

1. **Large datasets**: Use `folder` type to split files by date
2. **API rate limits**: Add delays in API configuration
3. **Memory usage**: Process files in batches
4. **Report size**: Use `max_rows_per_table` to limit PDF size

## Security Best Practices

1. ✅ Never commit `.env` to version control
2. ✅ Use environment variables for all credentials
3. ✅ Restrict file permissions on `.env` (Unix: `chmod 600 .env`)
4. ✅ Use app-specific passwords for email
5. ✅ Regularly rotate API keys and tokens
6. ✅ Use HTTPS for all API endpoints

## License

This project is provided as-is for use in your organization.

## Support

For issues and questions:
1. Check the logs: `logs/activity_reporter.log`
2. Review this README
3. Check configuration examples in `config/`

---

**Happy Reporting! 📊**

