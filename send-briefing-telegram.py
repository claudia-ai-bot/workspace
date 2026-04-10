#!/usr/bin/env python3
"""
SEQ Construction CRM - Send Daily Briefing to Telegram
Generates briefing + sends to Chris via Telegram API
"""

import json
import os
import sys
import requests
from datetime import datetime

CRM_FILE = os.path.expanduser("~/.openclaw/workspace/seq-crm/companies.json")
CHRIS_ID = "8636795192"
TELEGRAM_BOT_TOKEN = "8677611814:AAGRPJRGsvEGkHb7RV-W-eyQPq473uP1nCE"
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

# Import the briefing generator
sys.path.insert(0, os.path.dirname(__file__))
from briefing_generator import load_companies, generate_daily_briefing

def send_to_telegram(message):
    """Send formatted briefing to Telegram"""
    try:
        payload = {
            "chat_id": CHRIS_ID,
            "text": message,
            "parse_mode": "Markdown"
        }
        response = requests.post(TELEGRAM_API, json=payload, timeout=10)
        if response.status_code == 200:
            print("✅ Briefing sent to Telegram")
            return True
        else:
            print(f"❌ Telegram error: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error sending: {e}")
        return False

if __name__ == "__main__":
    companies = load_companies()
    
    if not companies:
        print("❌ No companies loaded from CRM")
        sys.exit(1)
    
    # Generate briefing
    briefing = generate_daily_briefing(companies)
    
    # Send to Telegram
    if send_to_telegram(briefing):
        print("✅ Daily briefing complete")
    else:
        print("⚠️ Failed to send briefing")
