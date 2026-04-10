#!/usr/bin/env python3
"""
Nightly Lead Enrichment Script
Pulls top 5 new leads, enriches hiring manager info via Hunter.io + Exa,
writes back to CRM, and outputs a JSON summary.
"""

import sqlite3
import json
import time
import requests
from datetime import datetime, date
from pathlib import Path

# API Keys
HUNTER_API_KEY = "a4309eac38a707b805e3437cf8ab968056fb15e8"
EXA_API_KEY = "ab647372-46fd-423f-86ed-fcb9df6045a7"

# Paths
DB_PATH = "/home/chris/.openclaw/workspace/seq-crm/crm.db"
CRON_RESULTS_DIR = Path("/home/chris/.openclaw/workspace/cron-results")

def get_unenriched_leads(limit=5):
    """Pull top 5 new leads that haven't been enriched yet."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, company, hiring_manager, hiring_manager_title, location, sector, phone
        FROM leads 
        WHERE hiring_manager IS NOT NULL 
          AND hiring_manager != ''
          AND (hirer_email IS NULL OR hirer_email = '')
        ORDER BY created_at DESC
        LIMIT ?
    """, (limit,))
    leads = cursor.fetchall()
    conn.close()
    return leads

def enrich_with_hunter(company, hiring_manager_name):
    """Use Hunter.io to find email for the hiring manager."""
    try:
        # First search for the company domain
        domain_url = f"https://api.hunter.io/v2/domain-search"
        params = {
            "domain": f"{company.lower().replace(' ', '')}.com",
            "company": company,
            "api_key": HUNTER_API_KEY
        }
        
        response = requests.get(domain_url, params=params, timeout=10)
        time.sleep(1.5)  # Prevent Hunter.io/Alibaba Cloud rate limiting
        if response.status_code != 200:
            return None, None, "error"
        
        data = response.json()
        emails = data.get("data", {}).get("emails", [])
        
        if emails:
            # Look for email matching hiring manager name
            first_name = hiring_manager_name.split()[0].lower()
            last_name = hiring_manager_name.split()[-1].lower()
            
            for email_entry in emails:
                email = email_entry.get("value", "")
                if email:
                    # Check if first or last name appears in email
                    email_lower = email.lower()
                    if first_name in email_lower or last_name in email_lower:
                        verification = email_entry.get("verification", {}).get("status", "unknown")
                        return email, verification, "found"
            
            # If no match, return first email with guessed status
            first_email = emails[0].get("value", "")
            return first_email, "guessed", "found"
        
        return None, None, "not_found"
    except Exception as e:
        print(f"  Hunter API error: {e}")
        return None, None, "error"

def enrich_with_exa_linkedin(hiring_manager_name, company):
    """Use Exa API to search LinkedIn for the hiring manager."""
    try:
        search_query = f'{hiring_manager_name} {company} LinkedIn'
        
        response = requests.post(
            "https://api.exa.ai/search",
            headers={
                "Authorization": f"Bearer {EXA_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "query": search_query,
                "num_results": 3,
                "include_domains": ["linkedin.com"]
            },
            timeout=15
        )
        
        if response.status_code != 200:
            return None, "error"
        
        results = response.json().get("results", [])
        
        for result in results:
            url = result.get("url", "")
            if "linkedin.com" in url.lower():
                # Extract LinkedIn profile URL
                return url, "found"
        
        # If no LinkedIn found in results, try first URL anyway
        if results:
            return results[0].get("url", None), "found"
        
        return None, "not_found"
    except Exception as e:
        print(f"  Exa API error: {e}")
        return None, "error"

def update_lead_in_db(lead_id, hirer_email, email_quality, hirer_linkedin):
    """Write enriched data back to the CRM."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE leads 
        SET hirer_email = ?, hirer_linkedin = ?, enriched = 1
        WHERE id = ?
    """, (hirer_email, hirer_linkedin, lead_id))
    conn.commit()
    conn.close()

def main():
    print(f"[{datetime.now().isoformat()}] Starting nightly enrichment...")
    
    # Ensure cron results directory exists
    CRON_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Get unenriched leads
    leads = get_unenriched_leads(limit=5)
    
    if not leads:
        print("No new leads to enrich.")
        result = {
            "date": date.today().isoformat(),
            "leads_enriched": 0,
            "leads": []
        }
    else:
        print(f"Found {len(leads)} leads to enrich.")
        enriched_leads = []
        
        for lead in leads:
            lead_id, company, hiring_manager, hiring_manager_title, location, sector, phone = lead
            print(f"\nEnriching: {company} - {hiring_manager}")
            
            lead_result = {
                "id": lead_id,
                "company": company,
                "hiring_manager": hiring_manager,
                "title": hiring_manager_title,
                "location": location,
                "sector": sector,
                "phone": phone,
                "hirer_email": None,
                "email_quality": None,
                "hirer_linkedin": None,
                "status": "pending"
            }
            
            # Step 1: Hunter.io for email
            print(f"  Searching Hunter.io for email...")
            hirer_email, email_quality, hunter_status = enrich_with_hunter(company, hiring_manager)
            
            if hirer_email:
                lead_result["hirer_email"] = hirer_email
                lead_result["email_quality"] = email_quality
                print(f"  Email found: {hirer_email} ({email_quality})")
            else:
                print(f"  No email found (status: {hunter_status})")
            
            # Step 2: Exa API for LinkedIn
            print(f"  Searching Exa for LinkedIn...")
            hirer_linkedin, exa_status = enrich_with_exa_linkedin(hiring_manager, company)
            
            if hirer_linkedin:
                lead_result["hirer_linkedin"] = hirer_linkedin
                print(f"  LinkedIn found: {hirer_linkedin}")
            else:
                print(f"  No LinkedIn found (status: {exa_status})")
            
            # Step 3: Update CRM
            update_lead_in_db(lead_id, hirer_email, email_quality, hirer_linkedin)
            lead_result["status"] = "enriched"
            
            enriched_leads.append(lead_result)
        
        result = {
            "date": date.today().isoformat(),
            "leads_enriched": len(enriched_leads),
            "leads": enriched_leads
        }
    
    # Write result to JSON file
    result_file = CRON_RESULTS_DIR / f"nightly-enrichment-{date.today().isoformat()}.json"
    with open(result_file, "w") as f:
        json.dump(result, f, indent=2)
    
    print(f"\n[{datetime.now().isoformat()}] Enrichment complete!")
    print(f"Result saved to: {result_file}")
    print(f"Leads enriched: {result['leads_enriched']}")
    
    return result

if __name__ == "__main__":
    main()
