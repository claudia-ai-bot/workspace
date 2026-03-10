#!/usr/bin/env python3
"""
Reminder Daemon - Proper automation with direct Telegram API
Uses bot token directly, doesn't rely on openclaw CLI
"""

import json
import os
import sys
import time
import requests
from datetime import datetime
import signal
import logging

REMINDERS_FILE = os.path.expanduser("~/.openclaw/workspace/reminders.json")
CHRIS_ID = "8636795192"
TELEGRAM_BOT_TOKEN = "8677611814:AAGRPJRGsvEGkHb7RV-W-eyQPq473uP1nCE"  # From config
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
LOG_FILE = os.path.expanduser("~/.openclaw/workspace/reminder-daemon.log")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger(__name__)

checked_times = set()

def load_reminders():
    """Load reminders from JSON file"""
    try:
        if not os.path.exists(REMINDERS_FILE):
            return {"reminders": []}
        with open(REMINDERS_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading reminders: {e}")
        return {"reminders": []}

def save_reminders(data):
    """Save reminders to JSON file"""
    try:
        with open(REMINDERS_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving reminders: {e}")

def should_fire(reminder):
    """Check if a reminder should fire now"""
    if not reminder.get("active", True):
        return False
    
    try:
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        current_date = now.strftime("%Y-%m-%d")
        current_day = now.strftime("%A")
        
        # One-time reminder
        if not reminder.get("recurring"):
            reminder_datetime = reminder.get("time", "")
            if reminder_datetime == f"{current_time} {current_date}":
                return True
        
        # Daily
        elif reminder.get("recurring") == "daily":
            if reminder.get("time") == current_time:
                return True
        
        # Weekly
        elif reminder.get("recurring") == "weekly":
            parts = reminder.get("time", "").split()
            if len(parts) == 2:
                day, time_str = parts
                if day.lower() == current_day.lower() and time_str == current_time:
                    return True
        
        # Monthly
        elif reminder.get("recurring") == "monthly":
            import re
            time_str = reminder.get("time", "")
            match = re.match(r"(\d+)(st|nd|rd|th) of month (\d{2}:\d{2})", time_str)
            if match:
                day_of_month = int(match.group(1))
                fire_time = match.group(3)
                if now.day == day_of_month and fire_time == current_time:
                    return True
    
    except Exception as e:
        logger.error(f"Error checking reminder: {e}")
    
    return False

def send_reminder(message):
    """Send reminder via direct Telegram API"""
    try:
        payload = {
            "chat_id": CHRIS_ID,
            "text": f"⏰ **REMINDER:** {message}",
            "parse_mode": "Markdown"
        }
        response = requests.post(TELEGRAM_API, json=payload, timeout=10)
        if response.status_code == 200:
            logger.info(f"✅ Reminder sent: {message}")
            return True
        else:
            logger.error(f"❌ Telegram API error: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logger.error(f"Error sending reminder: {e}")
        return False

def handle_shutdown(signum, frame):
    """Handle shutdown gracefully"""
    logger.info("Reminder daemon shutting down...")
    sys.exit(0)

def main():
    """Main daemon loop"""
    logger.info("Reminder daemon starting...")
    
    # Register signal handlers
    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)
    
    while True:
        try:
            data = load_reminders()
            now = datetime.now()
            current_minute = now.strftime("%H:%M")
            
            # Check each reminder
            for reminder in data.get("reminders", []):
                if should_fire(reminder):
                    # Avoid duplicate fires in the same minute
                    reminder_key = f"{reminder.get('id')}_{current_minute}"
                    if reminder_key not in checked_times:
                        if send_reminder(reminder.get("message", "Unknown")):
                            # Mark one-time reminders as inactive
                            if not reminder.get("recurring"):
                                reminder["active"] = False
                            checked_times.add(reminder_key)
            
            # Clean up checked_times periodically
            if len(checked_times) > 100:
                checked_times.clear()
            
            # Save updated reminders
            save_reminders(data)
            
            # Sleep 30 seconds before next check
            time.sleep(30)
        
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            time.sleep(30)

if __name__ == "__main__":
    main()
