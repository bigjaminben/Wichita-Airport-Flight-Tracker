"""
ICT Airport Email Report Scheduler
Sends automated daily and weekly email reports
"""
import requests
import schedule
import time
from datetime import datetime
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

API_BASE = "http://127.0.0.1:5001"
EMAIL_TO = "bigjaminben@gmail.com"


def send_daily_report():
    """Send daily flight report email"""
    try:
        logger.info("Fetching daily report data...")
        response = requests.get(f"{API_BASE}/api/report/daily", timeout=10)
        data = response.json()
        
        # Format HTML email
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #f9f9f9; margin: 0; padding: 20px; }}
        .container {{ max-width: 900px; margin: 0 auto; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }}
        .header {{ background: linear-gradient(135deg, #000000 0%, #1a1a1a 100%); color: white; padding: 30px; border-bottom: 4px solid #86BC25; }}
        .header h1 {{ margin: 0; font-size: 28px; }}
        .header p {{ margin: 10px 0 0 0; opacity: 0.9; }}
        .content {{ padding: 30px; }}
        .summary-box {{ background: linear-gradient(135deg, #86BC25 0%, #6b9a1f 100%); color: white; padding: 25px; border-radius: 8px; margin-bottom: 30px; }}
        .summary-box h2 {{ margin: 0 0 20px 0; font-size: 20px; }}
        .summary-stats {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; }}
        .summary-stat {{ background: rgba(255,255,255,0.15); padding: 15px; border-radius: 6px; text-align: center; }}
        .summary-stat-label {{ font-size: 11px; opacity: 0.9; text-transform: uppercase; letter-spacing: 0.5px; }}
        .summary-stat-value {{ font-size: 28px; font-weight: bold; margin-top: 5px; }}
        .section {{ margin: 30px 0; }}
        .section-title {{ font-size: 18px; font-weight: 600; color: #2C2C2C; margin-bottom: 15px; border-bottom: 2px solid #86BC25; padding-bottom: 10px; }}
        .metric-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; }}
        .metric-card {{ background: #f9f9f9; padding: 20px; border-radius: 8px; border-left: 4px solid #86BC25; }}
        .metric-label {{ font-size: 13px; color: #53565A; margin-bottom: 8px; }}
        .metric-value {{ font-size: 24px; font-weight: bold; color: #2C2C2C; }}
        .footer {{ background: #2C2C2C; color: #D0D0CE; padding: 20px 30px; text-align: center; font-size: 12px; }}
        .footer a {{ color: #86BC25; text-decoration: none; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 ICT Airport Daily Report</h1>
            <p>Real-Time Flight Operations Summary - {datetime.now().strftime('%B %d, %Y')}</p>
        </div>
        <div class="content">
            <div class="summary-box">
                <h2>Today's Highlights</h2>
                <div class="summary-stats">
                    <div class="summary-stat">
                        <div class="summary-stat-label">Total Flights</div>
                        <div class="summary-stat-value">{data.get('total_flights', 0)}</div>
                    </div>
                    <div class="summary-stat">
                        <div class="summary-stat-label">Arrivals</div>
                        <div class="summary-stat-value">{data.get('arrivals', 0)}</div>
                    </div>
                    <div class="summary-stat">
                        <div class="summary-stat-label">Departures</div>
                        <div class="summary-stat-value">{data.get('departures', 0)}</div>
                    </div>
                    <div class="summary-stat">
                        <div class="summary-stat-label">On-Time %</div>
                        <div class="summary-stat-value">{data.get('on_time_percentage', 0):.1f}%</div>
                    </div>
                </div>
            </div>
            
            <div class="section">
                <div class="section-title">Flight Status Breakdown</div>
                <div class="metric-grid">
                    <div class="metric-card">
                        <div class="metric-label">On-Time Flights</div>
                        <div class="metric-value">{data.get('on_time', 0)}</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Delayed Flights</div>
                        <div class="metric-value">{data.get('delayed', 0)}</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Cancelled Flights</div>
                        <div class="metric-value">{data.get('cancelled', 0)}</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Active Flights</div>
                        <div class="metric-value">{data.get('on_time', 0) + data.get('delayed', 0)}</div>
                    </div>
                </div>
            </div>
            
            <div class="section">
                <div class="section-title">Peak Operations</div>
                <div class="metric-grid">
                    <div class="metric-card">
                        <div class="metric-label">Busiest Hour</div>
                        <div class="metric-value">{data.get('busiest_hour', 'N/A')}</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Top Route</div>
                        <div class="metric-value">{data.get('top_route', 'N/A')}</div>
                    </div>
                </div>
            </div>
        </div>
        <div class="footer">
            <p><strong>ICT Airport Operations Intelligence Platform</strong></p>
            <p>Daily automated report | Powered by Deloitte Technology Consulting</p>
            <p><a href="http://127.0.0.1:5001">View Live Dashboard</a></p>
            <p>© 2025 Deloitte Consulting LLP. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
"""
        
        # Send email
        email_payload = {
            "to": EMAIL_TO,
            "subject": f"ICT Airport Daily Report - {datetime.now().strftime('%B %d, %Y')}",
            "html": html,
            "report_type": "daily"
        }
        
        logger.info("Sending daily report email...")
        email_response = requests.post(
            f"{API_BASE}/api/send-email",
            json=email_payload,
            timeout=30
        )
        
        if email_response.status_code == 200:
            logger.info(f"✓ Daily report sent successfully to {EMAIL_TO}")
        else:
            logger.error(f"✗ Failed to send daily report: {email_response.text}")
            
    except Exception as e:
        logger.error(f"✗ Error sending daily report: {e}")


def send_weekly_report():
    """Send weekly flight summary email"""
    try:
        logger.info("Fetching weekly report data...")
        response = requests.get(f"{API_BASE}/api/report/weekly", timeout=10)
        data = response.json()
        
        # Format HTML email (simplified for weekly)
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #f9f9f9; margin: 0; padding: 20px; }}
        .container {{ max-width: 900px; margin: 0 auto; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }}
        .header {{ background: linear-gradient(135deg, #000000 0%, #1a1a1a 100%); color: white; padding: 30px; border-bottom: 4px solid #86BC25; }}
        .header h1 {{ margin: 0; font-size: 28px; }}
        .summary-box {{ background: linear-gradient(135deg, #86BC25 0%, #6b9a1f 100%); color: white; padding: 25px; border-radius: 8px; margin: 30px; }}
        .summary-stats {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-top: 20px; }}
        .summary-stat {{ background: rgba(255,255,255,0.15); padding: 15px; border-radius: 6px; text-align: center; }}
        .summary-stat-label {{ font-size: 11px; opacity: 0.9; text-transform: uppercase; }}
        .summary-stat-value {{ font-size: 28px; font-weight: bold; margin-top: 5px; }}
        .footer {{ background: #2C2C2C; color: #D0D0CE; padding: 20px 30px; text-align: center; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📈 ICT Airport Weekly Summary</h1>
            <p>7-Day Flight Operations Report</p>
        </div>
        <div class="summary-box">
            <h2 style="margin:0 0 10px 0;">Weekly Highlights</h2>
            <div class="summary-stats">
                <div class="summary-stat">
                    <div class="summary-stat-label">Total Flights</div>
                    <div class="summary-stat-value">{data.get('total_flights', 0)}</div>
                </div>
                <div class="summary-stat">
                    <div class="summary-stat-label">Avg Daily</div>
                    <div class="summary-stat-value">{data.get('avg_daily_flights', 0)}</div>
                </div>
                <div class="summary-stat">
                    <div class="summary-stat-label">On-Time %</div>
                    <div class="summary-stat-value">{data.get('on_time_percentage', 0):.1f}%</div>
                </div>
                <div class="summary-stat">
                    <div class="summary-stat-label">Top Route</div>
                    <div class="summary-stat-value" style="font-size:16px;">{data.get('top_route', 'N/A')}</div>
                </div>
            </div>
        </div>
        <div class="footer">
            <p><strong>ICT Airport Operations Intelligence Platform</strong></p>
            <p>Weekly automated report | Powered by Deloitte Technology Consulting</p>
            <p>© 2025 Deloitte Consulting LLP. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
"""
        
        email_payload = {
            "to": EMAIL_TO,
            "subject": f"ICT Airport Weekly Summary - Week of {datetime.now().strftime('%B %d, %Y')}",
            "html": html,
            "report_type": "weekly"
        }
        
        logger.info("Sending weekly report email...")
        email_response = requests.post(
            f"{API_BASE}/api/send-email",
            json=email_payload,
            timeout=30
        )
        
        if email_response.status_code == 200:
            logger.info(f"✓ Weekly report sent successfully to {EMAIL_TO}")
        else:
            logger.error(f"✗ Failed to send weekly report: {email_response.text}")
            
    except Exception as e:
        logger.error(f"✗ Error sending weekly report: {e}")


# Schedule jobs
schedule.every().day.at("23:59").do(send_daily_report)  # Daily at 11:59 PM
schedule.every().sunday.at("20:00").do(send_weekly_report)  # Sunday at 8:00 PM

# For testing: send immediately on startup
logger.info("Email scheduler started!")
logger.info(f"Daily reports scheduled for 11:59 PM → {EMAIL_TO}")
logger.info(f"Weekly reports scheduled for Sunday 8:00 PM → {EMAIL_TO}")
logger.info("Sending test email on startup...")
send_daily_report()

# Keep running
while True:
    schedule.run_pending()
    time.sleep(60)  # Check every minute
