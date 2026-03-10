#!/usr/bin/env python3
"""
Reminders Skill - Schedule and manage reminders
"""

import json
import sys
import os
from datetime import datetime, timedelta
import argparse
import uuid

# Storage location
REMINDERS_FILE = os.path.expanduser("~/.openclaw/workspace/reminders.json")

def load_reminders():
    """Load reminders from JSON file"""
    if os.path.exists(REMINDERS_FILE):
        with open(REMINDERS_FILE, 'r') as f:
            return json.load(f)
    return {"reminders": []}

def save_reminders(data):
    """Save reminders to JSON file"""
    os.makedirs(os.path.dirname(REMINDERS_FILE), exist_ok=True)
    with open(REMINDERS_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def add_reminder(message, time_str, recurring=None):
    """Add a new reminder"""
    data = load_reminders()
    
    reminder = {
        "id": str(uuid.uuid4())[:8],
        "message": message,
        "time": time_str,
        "recurring": recurring,
        "created_at": datetime.now().isoformat(),
        "active": True
    }
    
    data["reminders"].append(reminder)
    save_reminders(data)
    
    print(f"✅ Reminder set: '{message}'")
    if recurring:
        print(f"   Every {recurring} at {time_str}")
    else:
        print(f"   One-time at {time_str}")
    print(f"   ID: {reminder['id']}")

def list_reminders():
    """List all active reminders"""
    data = load_reminders()
    
    if not data["reminders"]:
        print("📭 No reminders set")
        return
    
    print("\n📋 Active Reminders:\n")
    for i, r in enumerate(data["reminders"], 1):
        recurring = f" ({r['recurring']})" if r['recurring'] else ""
        status = "✅" if r['active'] else "❌"
        print(f"{i}. {status} {r['message']}")
        print(f"   Time: {r['time']}{recurring}")
        print(f"   ID: {r['id']}\n")

def delete_reminder(reminder_id):
    """Delete a reminder by ID"""
    data = load_reminders()
    
    for r in data["reminders"]:
        if r["id"] == reminder_id:
            r["active"] = False
            save_reminders(data)
            print(f"✅ Deleted reminder: {r['message']}")
            return
    
    print(f"❌ Reminder not found: {reminder_id}")

def main():
    parser = argparse.ArgumentParser(description="Manage reminders")
    parser.add_argument("message", nargs="?", help="Reminder message")
    parser.add_argument("time", nargs="?", help="Time/date (format: HH:MM or HH:MM YYYY-MM-DD or DAY HH:MM)")
    parser.add_argument("--recurring", choices=["daily", "weekly", "monthly"], help="Recurring type")
    parser.add_argument("--list", action="store_true", help="List all reminders")
    parser.add_argument("--delete", metavar="ID", help="Delete reminder by ID")
    
    args = parser.parse_args()
    
    if args.list:
        list_reminders()
    elif args.delete:
        delete_reminder(args.delete)
    elif args.message and args.time:
        add_reminder(args.message, args.time, args.recurring)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
