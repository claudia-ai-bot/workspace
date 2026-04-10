#!/usr/bin/env python3
"""
Prospect Research & CRM Add Script
Automatically researches a company and adds it to the SEQ CRM with decision makers.
"""

import sqlite3
import sys
import json
from datetime import datetime
from urllib.parse import quote

# In production, you'd use actual web fetching. For now, this is a template.

DB_PATH = '/home/chris/.openclaw/workspace/seq-crm/crm.db'

def add_company_to_crm(name, sector, location, active_projects='', upcoming_projects='', notes='', tier='Tier 2'):
    """Add a company to the CRM."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Check if exists
    c.execute('SELECT id FROM companies WHERE name = ?', (name,))
    existing = c.fetchone()
    
    if existing:
        print(f"Company '{name}' already exists (ID: {existing[0]})")
        conn.close()
        return existing[0]
    
    now = datetime.now().isoformat()
    c.execute('''
        INSERT INTO companies (name, tier, sector, location, active_projects, upcoming_projects, competitors, notes, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, '', ?, ?, ?)
    ''', (name, tier, sector, location, active_projects, upcoming_projects, notes, now, now))
    
    company_id = c.lastrowid
    conn.commit()
    print(f"Added '{name}' to CRM (ID: {company_id})")
    conn.close()
    return company_id

def add_decision_maker(company_id, name, title, role, notes=''):
    """Add a decision maker to a company."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''
        INSERT INTO decision_makers (company_id, name, title, role, phone, email, linkedin, hiring_signals, relationship_score, last_contact, next_action, notes)
        VALUES (?, ?, ?, ?, NULL, NULL, NULL, NULL, 1, NULL, 'Research contact', ?)
    ''', (company_id, name, title, role, notes))
    
    dm_id = c.lastrowid
    conn.commit()
    print(f"  Added DM: {name} - {title}")
    conn.close()
    return dm_id

def quick_add_gold_coast_developer(company_name):
    """Template for quick-adding a Gold Coast developer."""
    print(f"\n=== Quick Add: {company_name} ===")
    
    # This would be populated from web research in production
    sector = input("Sector (Property Development/Construction/Civil): ") or "Property Development"
    location = input("Location (Gold Coast/Brisbane/SEQ): ") or "Gold Coast"
    tier = input("Tier (Tier 1/Tier 2/Tier 3): ") or "Tier 2"
    
    company_id = add_company_to_crm(company_name, sector, location, tier=tier)
    
    # Add standard decision maker slots
    add_decision_maker(company_id, "TBC - Managing Director", "Managing Director", "Leadership", "Final decision maker")
    add_decision_maker(company_id, "TBC - Construction Manager", "Construction Manager", "Construction", "Direct hiring authority")
    add_decision_maker(company_id, "TBC - Project Manager", "Project Manager", "Operations", "Project-level decisions")
    
    print(f"\n✓ Added {company_name} with 3 DM slots")
    return company_id

def list_companies_needing_research():
    """List companies that need decision maker research."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Companies with no decision makers or TBC DMs
    c.execute('''
        SELECT c.id, c.name, c.sector, c.location, COUNT(d.id) as dm_count
        FROM companies c
        LEFT JOIN decision_makers d ON c.id = d.company_id
        WHERE c.name NOT LIKE '%TBC%'
        GROUP BY c.id
        HAVING dm_count = 0 OR d.name LIKE 'TBC%'
        ORDER BY c.updated_at DESC
    ''')
    
    print("\n=== Companies Needing Research ===")
    for row in c.fetchall():
        print(f"  [{row[0]}] {row[1]} ({row[2]}) - {row[3]}")
    
    conn.close()

if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == '--list-needing-research':
            list_companies_needing_research()
        else:
            # Quick add company
            quick_add_gold_coast_developer(' '.join(sys.argv[1:]))
    else:
        print("Usage:")
        print("  python3 prospect-research.py \"Company Name\"   # Add new company")
        print("  python3 prospect-research.py --list-needing-research  # Show companies needing research")
