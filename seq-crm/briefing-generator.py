#!/usr/bin/env python3
"""
SEQ Construction CRM - Briefing Generator
Pulls companies.json, identifies opportunities, ranks by fit, generates daily/weekly briefings
"""

import json
import os
from datetime import datetime, timedelta

CRM_FILE = os.path.expanduser("~/.openclaw/workspace/seq-crm/companies.json")

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
    """
    Rank individual CONTACTS by opportunity fit
    Scoring: Company stage + hiring need + contact seniority + recency
    """
    opportunities = []
    
    for company in companies:
        company_score = 0
        
        # Company-level scoring
        if company.get("pipeline_projects"):
            company_score += 5
        if company.get("current_projects"):
            company_score += 8
        
        # Hiring need magnitude
        hiring_needs = company.get("hiring_needs", "")
        num_roles = len([x for x in hiring_needs.split(",") if x.strip()])
        company_score += num_roles * 2
        
        # Company status boost
        if company.get("status") == "warm":
            company_score += 5
        
        # Last contact recency
        last_contact = company.get("last_contact", "2026-01-01")
        days_ago = (datetime.now() - datetime.strptime(last_contact, "%Y-%m-%d")).days
        company_score += min(days_ago // 7, 5)
        
        # Now score each contact within company
        for contact in company.get("key_contacts", []):
            contact_score = company_score
            
            # Boost for senior titles
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
    """Generate daily Telegram briefing (top 5 CONTACTS to approach)"""
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

def generate_weekly_digest(companies):
    """Generate weekly email-style digest"""
    opportunities = rank_opportunities(companies)
    
    digest = "SEQ CONSTRUCTION WEEKLY DIGEST\n"
    digest += "=" * 50 + "\n\n"
    digest += f"Week of {datetime.now().strftime('%Y-%m-%d')}\n"
    digest += f"Region: Gold Coast | Total Companies Tracked: {len(companies)}\n\n"
    
    # Group by status
    warm = [o for o in opportunities if o["status"] == "warm"]
    cold = [o for o in opportunities if o["status"] == "cold"]
    
    digest += f"🔥 WARM (Ready to engage): {len(warm)}\n"
    for opp in warm[:3]:
        digest += f"  • {opp['company']} - {opp['hiring']}\n"
    
    digest += f"\n❄️ COLD (Build relationship): {len(cold)}\n"
    for opp in cold[:3]:
        digest += f"  • {opp['company']} - {opp['hiring']}\n"
    
    digest += "\n" + "=" * 50 + "\n"
    digest += "Top action items:\n"
    for opp in opportunities[:3]:
        digest += f"1. Reach out to {opp['contact']['name'] if opp['contact'] else 'TBD'} @ {opp['company']}\n"
    
    return digest

if __name__ == "__main__":
    companies = load_companies()
    
    print("=" * 60)
    print("DAILY BRIEFING")
    print("=" * 60)
    print(generate_daily_briefing(companies))
    
    print("\n\n")
    print("=" * 60)
    print("WEEKLY DIGEST")
    print("=" * 60)
    print(generate_weekly_digest(companies))
