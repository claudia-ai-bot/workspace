#!/usr/bin/env python3
"""
SEQ Construction CRM - Unified script
Loads companies, generates briefings, sends to Telegram
"""

import json
import os
import sys
import requests
from datetime import datetime, timedelta

# Config
CRM_FILE = os.path.expanduser("~/.openclaw/workspace/seq-crm/companies.json")
CHRIS_ID = "8636795192"
TELEGRAM_BOT_TOKEN = "8677611814:AAGRPJRGsvEGkHb7RV-W-eyQPq473uP1nCE"
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

def load_companies():
    """Load companies from JSON"""
    try:
        with open(CRM_FILE, 'r') as f:
            data = json.load(f)
            return data.get("companies", [])
    except Exception as e:
        print(f"Error loading CRM: {e}")
        return []

def rank_opportunities(companies):
    """Rank individual CONTACTS by opportunity fit"""
    opportunities = []
    
    for company in companies:
        company_score = 0
        
        if company.get("pipeline_projects"):
            company_score += 5
        if company.get("current_projects"):
            company_score += 8
        
        hiring_needs = company.get("hiring_needs", "")
        num_roles = len([x for x in hiring_needs.split(",") if x.strip()])
        company_score += num_roles * 2
        
        if company.get("status") == "warm":
            company_score += 5
        
        last_contact = company.get("last_contact", "2026-01-01")
        days_ago = (datetime.now() - datetime.strptime(last_contact, "%Y-%m-%d")).days
        company_score += min(days_ago // 7, 5)
        
        for contact in company.get("key_contacts", []):
            contact_score = company_score
            
            title = contact.get("title", "").lower()
            if "director" in title or "coo" in title:
                contact_score += 5
            elif "senior" in title:
                contact_score += 3
            
            opportunities.append({
                "contact_name": contact["name"],
                "company": company["name"],
                "location": company["location"],
                "role": contact.get("role", "TBD"),
                "title": contact.get("title", "TBD"),
                "phone": contact.get("phone", "—"),
                "email": contact.get("email", "—"),
                "linkedin": contact.get("linkedin", "—"),
                "score": contact_score,
                "current_project": company.get("current_projects", ["TBD"])[0] if company.get("current_projects") else "Pipeline only",
                "hiring": company.get("hiring_needs", "TBD"),
                "company_status": company.get("status", "unknown"),
                "notes": company.get("notes", "")
            })
    
    return sorted(opportunities, key=lambda x: x["score"], reverse=True)

def generate_daily_briefing(companies):
    """Generate daily Telegram briefing (top 5 CONTACTS)"""
    opportunities = rank_opportunities(companies)
    top_5 = opportunities[:5]
    
    msg = "🏗️ **SEQ Construction Brief - Daily** (Gold Coast)\n\n"
    msg += f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M AEST')}\n"
    msg += "🎯 Top 5 contacts to approach today\n\n"
    
    for i, opp in enumerate(top_5, 1):
        msg += f"**{i}. {opp['contact_name']}**\n"
        msg += f"   {opp['role']} @ {opp['company']} ({opp['location']})\n"
        msg += f"   📞 {opp['phone']} | 📧 {opp['email']}\n"
        msg += f"   🔗 {opp['linkedin']}\n"
        msg += f"   Project: {opp['current_project']}\n"
        msg += f"   Hiring: {opp['hiring']}\n"
        msg += f"   Note: {opp['notes']}\n\n"
    
    return msg

def send_to_telegram(message):
    """Send message to Telegram"""
    try:
        payload = {
            "chat_id": CHRIS_ID,
            "text": message,
            "parse_mode": "Markdown"
        }
        response = requests.post(TELEGRAM_API, json=payload, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    companies = load_companies()
    
    if not companies:
        print("❌ No companies loaded")
        sys.exit(1)
    
    briefing = generate_daily_briefing(companies)
    
    if send_to_telegram(briefing):
        print("✅ Daily briefing sent to Telegram")
    else:
        print("❌ Failed to send")
