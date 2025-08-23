# EOD Bill Summary Scheduler Setup

## Overview
The EOD (End of Day) Bill Summary feature automatically sends daily summaries to billers and administrators.

## Features
- **Billers** receive their own bill summaries
- **Admins** receive comprehensive summaries of all billers' activities
- Summaries include statistics, bill details, and completion status
- Can be triggered manually or scheduled automatically

## Access Points

### 1. Manual Trigger (Admin Only)
- **Preview EOD Email**: `/eod_summary_preview`
- **Send EOD Summaries**: Click "Send EOD Summaries" button in Bill Summary page
- **API Endpoint**: `POST /api/bill_summary/send_eod`

### 2. Scheduled Trigger (Cron Job)
- **Endpoint**: `POST /api/bill_summary/schedule_eod`
- **Authentication**: Requires `X-EOD-Secret` header

## Setting Up Email Configuration

Add these environment variables to your `.env` file:

```env
# SMTP Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
FROM_EMAIL=TraceTrack System <noreply@tracetrack.com>

# EOD Secret Key for scheduled jobs
EOD_SECRET_KEY=your-secure-secret-key-here
```

## Setting Up Automatic EOD Scheduling

### Option 1: Using Cron (Linux/Unix)

Add this to your crontab (`crontab -e`):

```bash
# Send EOD summaries daily at 6:00 PM
0 18 * * * curl -X POST https://your-domain.com/api/bill_summary/schedule_eod \
  -H "X-EOD-Secret: your-secure-secret-key-here" \
  -H "Content-Type: application/json"
```

### Option 2: Using a Monitoring Service

Many services can call the endpoint on a schedule:
- UptimeRobot
- Cron-job.org
- AWS CloudWatch Events
- Google Cloud Scheduler

Configure them to:
- **URL**: `https://your-domain.com/api/bill_summary/schedule_eod`
- **Method**: POST
- **Headers**: 
  - `X-EOD-Secret: your-secure-secret-key-here`
  - `Content-Type: application/json`
- **Schedule**: Daily at your preferred time

### Option 3: Using Python Scheduler

Create a file `eod_scheduler.py`:

```python
import schedule
import time
import requests
import os

def send_eod_summary():
    url = "http://localhost:5000/api/bill_summary/schedule_eod"
    headers = {
        "X-EOD-Secret": os.environ.get("EOD_SECRET_KEY", "default-eod-secret-2025"),
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, headers=headers)
        print(f"EOD summary sent: {response.json()}")
    except Exception as e:
        print(f"Error sending EOD summary: {e}")

# Schedule for 6:00 PM daily
schedule.every().day.at("18:00").do(send_eod_summary)

print("EOD Scheduler started. Will send summaries daily at 6:00 PM")

while True:
    schedule.run_pending()
    time.sleep(60)  # Check every minute
```

Run with: `python eod_scheduler.py &`

## Email Content

### Biller Email Includes:
- Daily summary statistics (bills created, completed, pending)
- Total parent and child bags processed
- Total weight handled
- Detailed list of their bills with status

### Admin Email Includes:
- Overall system statistics
- Individual summaries for each biller
- Activity breakdown by user
- Comprehensive bill details

## Testing the Feature

1. **Preview the email format**:
   - Login as admin
   - Go to Bill Summary page
   - Click "Preview EOD Email"

2. **Send test email**:
   - Click "Send EOD Summaries" button
   - Confirm the action
   - Check email inboxes

3. **Test scheduled endpoint**:
   ```bash
   curl -X POST http://localhost:5000/api/bill_summary/schedule_eod \
     -H "X-EOD-Secret: default-eod-secret-2025" \
     -H "Content-Type: application/json"
   ```

## Troubleshooting

### Emails not sending:
1. Check SMTP credentials are configured
2. Verify email addresses are set for users
3. Check application logs for errors
4. Ensure firewall allows SMTP port (587/465)

### Schedule not working:
1. Verify cron job is active (`crontab -l`)
2. Check EOD_SECRET_KEY matches
3. Ensure application is running
4. Check logs for authentication errors

## Security Notes

- Always use HTTPS in production
- Keep EOD_SECRET_KEY secure and rotate regularly
- Use app-specific passwords for SMTP (not main account password)
- Consider rate limiting the schedule endpoint
- Monitor for failed email attempts

## API Response Format

Successful response:
```json
{
  "success": true,
  "message": "EOD summaries sent successfully",
  "results": {
    "billers_sent": ["biller1", "biller2"],
    "billers_failed": [],
    "admins_sent": ["admin"],
    "admins_failed": [],
    "total_processed": 3
  }
}
```