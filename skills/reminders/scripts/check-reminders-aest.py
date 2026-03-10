#!/usr/bin/env python3
"""
Reminder Checker - AEST-aware, fires reminders within 5-min windows
Call this during heartbeat to fire all due reminders
"""

import json
import os
import sys
from datetime import datetime, timezone, timedelta
import requests

REMINDERS_FILE = os.path.expanduser("~/.openclaw/workspace/reminders.json")
CHRIS_ID = "8636795192"
TELEGRAM_BOT_TOKEN = "8677611814:AAGRPJRGsvEGkHb7RV-W-eyQPq473uP1nCE"
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
AEST_TZ = timezone(timedelta(hours=10))

def get_aest_now():
    """Get current time in AEST"""
    return datetime.now(AEST_TZ)

def load_reminders():
    """Load reminders from JSON"""
    try:
        if not os.path.exists(REMINDERS_FILE):
            return {"reminders": []}
        with open(REMINDERS_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading reminders: {e}", file=sys.stderr)
        return {"reminders": []}

def save_reminders(data):
    """Save reminders to JSON"""
    try:
        with open(REMINDERS_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error saving reminders: {e}", file=sys.stderr)

def is_within_window(reminder_time, current_time, current_date, window_minutes=5):
    """Check if reminder_time is within window_minutes of current time"""
    try:
        # Parse reminder time
        reminder_parts = reminder_time.split()
        if len(reminder_parts) == 2:
            hm, d = reminder_parts
            h, m = hm.split(":")
            reminder_dt = datetime(int(d.split("-")[0]), int(d.split("-")[1]), int(d.split("-")[2]), 
                                  int(h), int(m), 0)
        else:
            return False
        
        # Parse current time
        ch, cm = current_time.split(":")
        cd_parts = current_date.split("-")
        current_dt = datetime(int(cd_parts[0]), int(cd_parts[1]), int(cd_parts[2]), 
                             int(ch), int(cm), 0)
        
        # Check if within window
        diff = abs((current_dt - reminder_dt).total_seconds())
        return diff <= (window_minutes * 60)
    except:
        return False

def send_reminder(message):
    """Send reminder via Telegram"""
    try:
        payload = {
            "chat_id": CHRIS_ID,
            "text": f"⏰ **REMINDER:** {message}",
            "parse_mode": "Markdown"
        }
        response = requests.post(TELEGRAM_API, json=payload, timeout=10)
        if response.status_code == 200:
            print(f"✅ Sent: {message}")
            return True
        else:
            print(f"❌ Telegram error: {response.status_code}", file=sys.stderr)
            return False
    except Exception as e:
        print(f"❌ Error sending: {e}", file=sys.stderr)
        return False

def check_and_fire():
    """Main: Check all reminders and fire due ones"""
    data = load_reminders()
    now_aest = get_aest_now()
    current_time = now_aest.strftime("%H:%M")
    current_date = now_aest.strftime("%Y-%m-%d")
    current_day = now_aest.strftime("%A")
    
    fired_count = 0
    
    for reminder in data.get("reminders", []):
        if not reminder.get("active", True):
            continue
        
        message = reminder.get("message", "Unknown")
        reminder_time = reminder.get("time", "")
        recurring = reminder.get("recurring")
        
        should_fire = False
        
        # One-time reminder
        if not recurring:
            if is_within_window(reminder_time, current_time, current_date):
                should_fire = True
        
        # Daily reminder
        elif recurring == "daily":
            if reminder_time == current_time:
                should_fire = True
        
        # Weekly reminder
        elif recurring == "weekly":
            parts = reminder_time.split()
            if len(parts) == 2:
                day, time_str = parts
                if day.lower() == current_day.lower() and time_str == current_time:
                    should_fire = True
        
        # Monthly reminder
        elif recurring == "monthly":
            import re
            match = re.match(r"(\d+)(st|nd|rd|th) of month (\d{2}:\d{2})", reminder_time)
            if match:
                day_of_month = int(match.group(1))
                fire_time = match.group(3)
                if now_aest.day == day_of_month and fire_time == current_time:
                    should_fire = True
        
        # Fire the reminder
        if should_fire:
            if send_reminder(message):
                # Mark one-time as inactive
                if not recurring:
                    reminder["active"] = False
                fired_count += 1
    
    # Save updated reminders
    save_reminders(data)
    
    if fired_count > 0:
        print(f"✅ Fired {fired_count} reminder(s)")
    
    return fired_count

if __name__ == "__main__":
    check_and_fire()
