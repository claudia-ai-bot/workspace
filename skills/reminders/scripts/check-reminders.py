#!/usr/bin/env python3
"""
Reminder checker - runs periodically to fire reminders via Telegram
This is meant to be run as a cron job (e.g., every 5 minutes)
"""

import json
import os
import sys
from datetime import datetime
import subprocess

REMINDERS_FILE = os.path.expanduser("~/.openclaw/workspace/reminders.json")
CHRIS_ID = "8636795192"  # Chris's Telegram user ID

def load_reminders():
    """Load reminders from JSON file"""
    if not os.path.exists(REMINDERS_FILE):
        return {"reminders": []}
    with open(REMINDERS_FILE, 'r') as f:
        return json.load(f)

def save_reminders(data):
    """Save reminders to JSON file"""
    with open(REMINDERS_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def should_fire(reminder):
    """Check if a reminder should fire now"""
    if not reminder["active"]:
        return False
    
    now = datetime.now()
    current_time = now.strftime("%H:%M")
    current_date = now.strftime("%Y-%m-%d")
    current_day = now.strftime("%A")
    
    # One-time reminder
    if not reminder["recurring"]:
        # Format: "HH:MM YYYY-MM-DD"
        if reminder["time"] == f"{current_time} {current_date}":
            return True
    
    # Daily
    elif reminder["recurring"] == "daily":
        if reminder["time"] == current_time:
            return True
    
    # Weekly
    elif reminder["recurring"] == "weekly":
        # Format: "DAY HH:MM"
        parts = reminder["time"].split()
        if len(parts) == 2:
            day, time = parts
            if day.lower() == current_day.lower() and time == current_time:
                return True
    
    # Monthly
    elif reminder["recurring"] == "monthly":
        # Format: "1st of month HH:MM" or "15th of month HH:MM"
        import re
        match = re.match(r"(\d+)(st|nd|rd|th) of month (\d{2}:\d{2})", reminder["time"])
        if match:
            day_of_month = int(match.group(1))
            fire_time = match.group(3)
            if now.day == day_of_month and fire_time == current_time:
                return True
    
    return False

def send_reminder(message):
    """Send reminder via Telegram CLI"""
    try:
        # Using openclaw message send command
        cmd = [
            "openclaw", "message", "send",
            "--target", CHRIS_ID,
            "--channel", "telegram",
            "--message", f"⏰ **REMINDER:** {message}"
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        return True
    except Exception as e:
        print(f"Error sending reminder: {e}", file=sys.stderr)
        return False

def check_and_fire():
    """Check all reminders and fire those that should"""
    data = load_reminders()
    fired = 0
    
    for reminder in data["reminders"]:
        if should_fire(reminder):
            if send_reminder(reminder["message"]):
                # Mark one-time reminders as inactive after firing
                if not reminder["recurring"]:
                    reminder["active"] = False
                fired += 1
    
    if fired > 0:
        save_reminders(data)
        print(f"✅ Fired {fired} reminder(s)")
    
    return fired

if __name__ == "__main__":
    check_and_fire()
