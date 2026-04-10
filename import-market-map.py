#!/usr/bin/env python3
"""
Import Market Map CSV into CRM database
"""

import csv
import sqlite3
import os

DB_FILE = os.path.expanduser("~/.openclaw/workspace/seq-crm/crm.db")
CSV_FILE = "/home/chris/.openclaw/media/inbound/SEQ_Desk_Engine_v5_Market_Map---52b4783d-8ef4-46ab-8676-30d4d08de3dc.csv"

def import_market_map():
    """Parse CSV and load into database"""
    db = sqlite3.connect(DB_FILE)
    cursor = db.cursor()
    
    with open(CSV_FILE, 'r', encoding='latin-1') as f:
        lines = f.readlines()
        
        # Skip first 2 header rows, start from line 3 (index 2)
        csv_content = ''.join(lines[2:])
        reader = csv.DictReader(csv_content.splitlines())
        
        current_company = None
        current_company_id = None
        companies_added = 0
        dms_added = 0
        
        for row in reader:
            if not row:
                continue
                
            # Skip header rows and empty rows
            company_name = row.get('Company', '').strip()
            if not company_name or company_name in ['Company', 'MARKET MAP']:
                continue
            
            dm_name = row.get('Decision Maker Name', '').strip()
            
            # New company
            if company_name != current_company and company_name:
                current_company = company_name
                sector = row.get('Sector', '').strip()
                location = row.get('Location', '').strip()
                active_projects = row.get('Active Projects', '').strip()
                upcoming_projects = row.get('Upcoming Projects', '').strip()
                competitors = row.get('Competitors', '').strip()
                notes = row.get('Notes', '').strip()
                
                # Check if company exists
                cursor.execute('SELECT id FROM companies WHERE name = ?', (company_name,))
                existing = cursor.fetchone()
                
                if existing:
                    current_company_id = existing[0]
                else:
                    cursor.execute('''
                        INSERT INTO companies 
                        (name, sector, location, active_projects, upcoming_projects, competitors, notes)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (company_name, sector, location, active_projects, upcoming_projects, competitors, notes))
                    current_company_id = cursor.lastrowid
                    companies_added += 1
            
            # Add decision maker (if row has a DM)
            if dm_name and current_company_id:
                dm_title = row.get('DM Title', '').strip()
                role = row.get('DM Title', '').split('–')[-1].strip() if '–' in row.get('DM Title', '') else dm_title
                hiring_signals = row.get('Hiring Signals', '').strip()
                relationship = row.get('Relationship\n(1-5)', '1').strip()
                last_contact = row.get('Last Contact', '').strip()
                next_action = row.get('Next Action', '').strip()
                dm_notes = row.get('Notes', '').strip()
                
                try:
                    rel_score = int(relationship) if relationship.isdigit() else 1
                except:
                    rel_score = 1
                
                # Check if DM exists
                cursor.execute('''
                    SELECT id FROM decision_makers 
                    WHERE company_id = ? AND name = ?
                ''', (current_company_id, dm_name))
                
                existing_dm = cursor.fetchone()
                
                if not existing_dm:
                    cursor.execute('''
                        INSERT INTO decision_makers 
                        (company_id, name, title, role, hiring_signals, relationship_score, 
                         last_contact, next_action, notes)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (current_company_id, dm_name, dm_title, role, hiring_signals, 
                          rel_score, last_contact, next_action, dm_notes))
                    dms_added += 1
        
        db.commit()
        db.close()
        
        print(f"✅ Import complete!")
        print(f"   Companies added: {companies_added}")
        print(f"   Decision makers added: {dms_added}")
        print(f"\n🚀 Visit http://localhost:8080 to view")

if __name__ == "__main__":
    import_market_map()
