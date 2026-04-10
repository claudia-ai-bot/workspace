#!/usr/bin/env python3
"""
SEQ CRM Follow-up Reminder Checker
Checks for overdue follow-ups and sends Telegram notifications
Run via cron or heartbeat
"""

import json
import os
import sqlite3
import sys
from datetime import datetime, timezone, timedelta
import requests

# Configuration
CRM_DB = os.path.expanduser("~/.openclaw/workspace/seq-crm/crm.db")
CHRIS_ID = "8636795192"
TELEGRAM_BOT_TOKEN = "8677611814:AAGRPJRGsvEGkHb7RV-W-eyQPq473uP1nCE"
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
AEST_TZ = timezone(timedelta(hours=10))

def get_aest_now():
    """Get current date in AEST"""
    return datetime.now(AEST_TZ).date()

def get_db():
    """Get database connection"""
    conn = sqlite3.connect(CRM_DB)
    conn.row_factory = sqlite3.Row
    return conn

def check_overdue_followups():
    """Check for overdue follow-ups across companies, candidates, and deals"""
    db = get_db()
    cursor = db.cursor()
    today = get_aest_now()
    overdue_items = []
    
    # Check decision_makers (contacts)
    try:
        cursor.execute('''
            SELECT dm.id, dm.name, dm.next_action, dm.last_contact, c.name as company_name
            FROM decision_makers dm
            JOIN companies c ON dm.company_id = c.id
            WHERE dm.next_action IS NOT NULL 
            AND dm.next_action != ''
            AND date(dm.next_action) < date(?)
            ORDER BY dm.next_action ASC
        ''', (today.isoformat(),))
        
        for row in cursor.fetchall():
            overdue_items.append({
                'type': 'contact',
                'name': row['name'],
                'company': row['company_name'],
                'next_action': row['next_action'],
                'table': 'decision_makers',
                'id': row['id']
            })
    except Exception as e:
        print(f"Error checking decision_makers: {e}")
    
    # Check candidates
    try:
        cursor.execute('''
            SELECT id, name, next_follow_up, last_contact
            FROM candidates
            WHERE next_follow_up IS NOT NULL 
            AND next_follow_up != ''
            AND date(next_follow_up) < date(?)
            ORDER BY next_follow_up ASC
        ''', (today.isoformat(),))
        
        for row in cursor.fetchall():
            overdue_items.append({
                'type': 'candidate',
                'name': row['name'],
                'company': row.get('current_company', 'N/A'),
                'next_action': row['next_follow_up'],
                'table': 'candidates',
                'id': row['id']
            })
    except Exception as e:
        print(f"Error checking candidates: {e}")
    
    # Check deals
    try:
        cursor.execute('''
            SELECT id, client, role, next_action
            FROM deals
            WHERE next_action IS NOT NULL 
            AND next_action != ''
            AND date(next_action) < date(?)
            ORDER BY next_action ASC
        ''', (today.isoformat(),))
        
        for row in cursor.fetchall():
            overdue_items.append({
                'type': 'deal',
                'name': row['role'],
                'company': row['client'],
                'next_action': row['next_action'],
                'table': 'deals',
                'id': row['id']
            })
    except Exception as e:
        print(f"Error checking deals: {e}")
    
    db.close()
    return overdue_items

def send_telegram(message):
    """Send message via Telegram"""
    try:
        payload = {
            "chat_id": CHRIS_ID,
            "text": f"⏰ **SEQ CRM REMINDER:**\n\n{message}",
            "parse_mode": "Markdown"
        }
        response = requests.post(TELEGRAM_API, json=payload, timeout=10)
        if response.status_code == 200:
            print(f"✅ Telegram sent: {message[:50]}...")
            return True
        else:
            print(f"❌ Telegram error: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error sending Telegram: {e}")
        return False

def main():
    """Main function"""
    print(f"🔍 Checking SEQ CRM for overdue follow-ups...")
    
    overdue = check_overdue_followups()
    
    if not overdue:
        print("✅ No overdue follow-ups found!")
        return 0
    
    # Group by type for cleaner messaging
    contacts = [o for o in overdue if o['type'] == 'contact']
    candidates = [o for o in overdue if o['type'] == 'candidate']
    deals = [o for o in overdue if o['type'] == 'deal']
    
    messages = []
    
    if contacts:
        msg = "📋 **OVERDUE CONTACTS:**\n"
        for c in contacts:
            msg += f"• {c['name']} ({c['company']}) - was {c['next_action']}\n"
        messages.append(msg)
    
    if candidates:
        msg = "👤 **OVERDUE CANDIDATES:**\n"
        for c in candidates:
            msg += f"• {c['name']} - was {c['next_action']}\n"
        messages.append(msg)
    
    if deals:
        msg = "💼 **OVERDUE DEALS:**\n"
        for d in deals:
            msg += f"• {d['name']} @ {d['company']} - was {d['next_action']}\n"
        messages.append(msg)
    
    # Send combined message
    full_message = "\n\n".join(messages)
    send_telegram(full_message)
    
    print(f"📊 Found {len(overdue)} overdue item(s): {len(contacts)} contacts, {len(candidates)} candidates, {len(deals)} deals")
    
    return len(overdue)

if __name__ == "__main__":
    sys.exit(main())
