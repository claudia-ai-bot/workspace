#!/usr/bin/env python3
"""
Morning Summary Script
Reads the latest enrichment result and sends a Telegram summary to Chris.
"""

import json
import glob
import requests
from datetime import datetime, date
from pathlib import Path

# Config
TELEGRAM_BOT_TOKEN = "8677611814:AAGRPJRGsvEGkHb7RV-W-eyQPq473uP1nCE"
TELEGRAM_CHAT_ID = "8636795192"
CRON_RESULTS_DIR = Path("/home/chris/.openclaw/workspace/cron-results")

def send_telegram_message(message):
    """Send message via Telegram bot."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    response = requests.post(url, json=payload, timeout=10)
    return response.json()

def format_summary(result):
    """Format the enrichment result as a Telegram message."""
    date_str = result.get("date", date.today().isoformat())
    leads = result.get("leads", [])
    
    if not leads:
        return None  # No leads to report
    
    # Header
    message = f"🌅 Morning Brief — {date_str}\n\n"
    message += f"<b>{len(leads)}</b> new leads enriched overnight:\n\n"
    
    # Lead details
    for i, lead in enumerate(leads, 1):
        company = lead.get("company", "Unknown")
        hirer = lead.get("hiring_manager", "Unknown")
        title = lead.get("title", "Unknown")
        email = lead.get("hirer_email", "not found")
        email_quality = lead.get("email_quality", "unknown")
        linkedin = lead.get("hirer_linkedin", "not found")
        phone = lead.get("phone", "")
        
        message += f"<b>{i}. {company}</b>\n"
        message += f"   {hirer} | {title}\n"
        message += f"   📧 {email} ({email_quality})\n"
        message += f"   🔗 LinkedIn: {linkedin}\n"
        if phone:
            message += f"   📱 {phone}\n"
        message += "\n"
    
    # Top call today (first enriched lead with an email)
    top_call = None
    for lead in leads:
        if lead.get("hirer_email") and lead.get("hirer_email") != "not found":
            top_call = lead
            break
    
    if top_call:
        message += f"⭐ <b>Top call today:</b>\n"
        message += f"{top_call['company']} — {top_call['hiring_manager']}"
        if top_call.get("phone"):
            message += f" at {top_call['phone']}"
        elif top_call.get("hirer_email"):
            message += f" at {top_call['hirer_email']}"
        message += "\n"
    
    return message

def main():
    print(f"[{datetime.now().isoformat()}] Morning summary starting...")
    
    # Find latest enrichment result
    result_files = sorted(CRON_RESULTS_DIR.glob("nightly-enrichment-*.json"), reverse=True)
    
    if not result_files:
        print("No enrichment results found.")
        message = f"🌅 Morning Brief — {date.today().isoformat()}\n\nNo new leads to enrich last night."
        send_telegram_message(message)
        print("Sent 'no leads' message to Telegram.")
        return
    
    latest_file = result_files[0]
    print(f"Reading: {latest_file}")
    
    with open(latest_file) as f:
        result = json.load(f)
    
    # Format and send
    formatted_message = format_summary(result)
    
    if formatted_message:
        print("Sending summary to Telegram...")
        response = send_telegram_message(formatted_message)
        if response.get("ok"):
            print("✅ Summary sent successfully!")
        else:
            print(f"❌ Telegram error: {response}")
    else:
        print("No enriched leads to report.")
        message = f"🌅 Morning Brief — {date.today().isoformat()}\n\nNo new leads to enrich last night."
        send_telegram_message(message)
        print("Sent 'no leads' message to Telegram.")

if __name__ == "__main__":
    main()
