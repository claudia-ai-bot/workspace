#!/usr/bin/env python3
"""
Seek Job Scraper - Auto-adds construction jobs as qualified leads to CRM
Run: python3 seek-scraper.py
"""
import os
import sqlite3
from datetime import datetime

DB_PATH = "/home/chris/.openclaw/workspace/seq-crm/crm.db"

# Seek search URLs for construction roles in SEQ
SEEK_URLS = [
    # Gold Coast
    "https://www.seek.com.au/construction-jobs/in-All-Gold-Coast-QLD",
    "https://www.seek.com.au/project-manager-construction-jobs/in-All-Gold-Coast-QLD",
    "https://www.seek.com.au/site-manager-jobs/in-All-Gold-Coast-QLD",
    # Brisbane
    "https://www.seek.com.au/construction-jobs/in-All-Brisbane-QLD",
    "https://www.seek.com.au/project-manager-construction-jobs/in-All-Brisbane-QLD",
]

def init_db():
    """Ensure leads table exists with correct schema"""
    if not os.path.exists(DB_PATH):
        print("❌ CRM not found")
        return False
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check existing schema
    cursor.execute("PRAGMA table_info(leads)")
    columns = {col[1] for col in cursor.fetchall()}
    
    # Add missing columns if needed
    if 'source' not in columns:
        cursor.execute("ALTER TABLE leads ADD COLUMN source TEXT DEFAULT 'Seek'")
    if 'company' not in columns:
        cursor.execute("ALTER TABLE leads ADD COLUMN company TEXT")
        
    conn.commit()
    conn.close()
    return True

def add_lead(company, role, contact_name=None, notes=None):
    """Add a lead to CRM"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if lead already exists (same company + role = duplicate)
    cursor.execute(
        "SELECT id FROM leads WHERE company = ? AND intel_type LIKE ?",
        (company, f"%{role}%")
    )
    if cursor.fetchone():
        conn.close()
        return False  # Already exists
    
    cursor.execute(
        "INSERT INTO leads (date, company, intel_type, source, what_it_means, action_trigger) VALUES (?, ?, ?, ?, ?, ?)",
        (datetime.now().strftime("%Y-%m-%d"), company, role, 'Seek', notes or '', contact_name or '')
    )
    conn.commit()
    conn.close()
    return True

def get_stats():
    """Get lead stats"""
    if not os.path.exists(DB_PATH):
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT COUNT(*) FROM leads WHERE source = 'Seek'")
        total = cursor.fetchone()[0] or 0
    except:
        total = 0
    
    print(f"\n📊 Seek Leads: {total} total")
    
    # Show recent leads
    try:
        cursor.execute("SELECT company, intel_type, created_at FROM leads WHERE source = 'Seek' ORDER BY created_at DESC LIMIT 5")
        rows = cursor.fetchall()
        if rows:
            print("\n📋 Recent leads:")
            for company, role, created in rows:
                print(f"  • {company} - {role}")
    except:
        pass
    
    conn.close()

if __name__ == "__main__":
    print("=" * 60)
    print("🔍 SEEK JOB SCRAPER - SEQ Construction")
    print(datetime.now().strftime("%A %d %B %Y"))
    print("=" * 60)
    
    if not init_db():
        print("❌ Failed to initialize CRM")
        exit(1)
    
    print("\n📋 Note: Browser automation needed for live scraping")
    print("\nTo scrape Seek, run:")
    print("  1. Open browser to Seek construction jobs (Gold Coast/Brisbane)")
    print("  2. Extract company, role, hiring manager from each ad")
    print("  3. Call add_lead() for each job found")
    
    get_stats()
    
    print("\n" + "=" * 60)
    print("✅ Scraper ready - add browser automation to populate leads")
    print("=" * 60)
