#!/usr/bin/env python3
"""
SEQ Construction Lead Research Tool
Quick research script to find decision makers and hiring needs for Gold Coast construction companies.
Run: python3 lead-research.py
"""

import json
import os

# Gold Coast construction companies to research (prioritized by project volume)
TARGET_COMPANIES = [
    {"name": "Multiplex", "project": "Coomera Hospital", "value": "$1.1B", "tier": "T1"},
    {"name": "John Holland", "project": "Light Rail Stage 3", "value": "$1.2B", "tier": "T1"},
    {"name": "Hutchinson Builders", "project": "Royale, Lagoon, Sea Glass", "value": "$500M+", "tier": "T1"},
    {"name": "Icon Co", "project": "Gold Coast residential", "value": "$150M", "tier": "T1"},
    {"name": "SIERA Group", "project": "Tapestry, Exhale", "value": "$80M+", "tier": "T2"},
    {"name": "Mosaic Property Group", "project": "Sophia + 3 others", "value": "$500M+", "tier": "T2"},
    {"name": "CPB Contractors", "project": "Faster Rail Alliance", "value": "$5.75B", "tier": "T1"},
    {"name": "Seymour Whyte", "project": "Coomera Connector South", "value": "$410M", "tier": "T2"},
    {"name": "Fulton Hogan", "project": "Coomera Connector", "value": "$3.4B", "tier": "T1"},
    {"name": "ADCO Constructions", "project": "Gold Coast active", "value": "TBC", "tier": "T1"},
    {"name": "McNab", "project": "Awaken Residences", "value": "TBC", "tier": "T2"},
    {"name": "Mayd Group", "project": "Burleigh 17-storey", "value": "TBC", "tier": "T2"},
]

# Key roles in construction recruitment (what companies typically hire)
KEY_ROLES = [
    "Project Manager",
    "Site Manager",
    "Construction Manager",
    "Contracts Manager",
    "Project Engineer",
    "Site Engineer",
    "Supervisor",
    "Foreman",
    "Quantity Surveyor",
    "Estimator",
    "Structural Engineer",
    "Civil Engineer",
    "Project Director",
    "Senior Project Manager",
]

def generate_lead_brief():
    """Generate a lead research brief for Chris to use when starting at Lead Group."""
    
    print("=" * 60)
    print("🎯 SEQ CONSTRUCTION LEAD BRIEF - March 2026")
    print("=" * 60)
    print("\n📋 PRIORITY TARGETS (by project value):\n")
    
    for i, co in enumerate(TARGET_COMPANIES[:6], 1):
        print(f"{i}. {co['name']} ({co['tier']})")
        print(f"   📍 Project: {co['project']}")
        print(f"   💰 Value: {co['value']}")
        print()
    
    print("\n🎯 KEY ROLES TO PLACE (in demand):")
    for role in KEY_ROLES[:8]:
        print(f"   • {role}")
    
    print("\n" + "=" * 60)
    print("📝 RESEARCH NOTES:")
    print("=" * 60)
    print("""
1. MULTIPLEX - Coomera Hospital
   - Managing Contractor for $1.1B+ hospital
   - Design phase, construction starts H2 2026
   - Will need: Project Managers, Services Coordinators, Structural Engineers
   - Contact: Check LinkedIn for QLD leadership

2. JOHN HOLLAND - Light Rail Stage 3
   - $1.2B, 6.7km extension Broadbeach South → Burleigh
   - Peak construction NOW
   - Will need: Rail engineers, civil, electrical, station fit-out
   - Contact: GC office or LinkedIn

3. HUTCHINSON BUILDERS - GC Pipeline
   - Royale ($176M), Lagoon ($198M), Sea Glass ($122M)
   - Multiple projects completing 2026
   - Will need: PMs, Site Managers, Supervisors
   - Contact: Gold Coast office (07 5530 3200)

4. ICON CO - $150M GC Project
   - Was advertising PM on Seek Feb 2026
   - Active on Gold Coast
   - Contact: Seek or LinkedIn

5. SIERA GROUP - High-rise
   - Tapestry ($80M+, 22-storey Chevron Island)
   - Multiple projects under construction
   - Contact: GC office

6. CPB CONTRACTORS - Faster Rail
   - Part of ActivUs Alliance ($5.75B)
   - Major civil/rail roles coming
   - Contact: Brisbane office
""")
    
    print("\n" + "=" * 60)
    print("🚀 QUICK START ACTIONS FOR CHRIS:")
    print("=" * 60)
    print("""
1. ☎️ CALL - Ring Gold Coast offices of top 5, ask for Construction Manager
2. 🔍 LINKEDIN - Connect with PMs/Site Managers at these companies
3. 📰 NEWS - Set Google Alerts for company names + "project" + "Gold Coast"
4. 👥 NETWORK - Attend QMBA Gold Coast events
5. 📋 SEEK - Set up saved searches for "construction manager Gold Coast"
""")

def update_crm_notes(db_path="/home/chris/.openclaw/workspace/seq-crm/crm.db"):
    """Update CRM with lead research notes."""
    import sqlite3
    
    if not os.path.exists(db_path):
        print(f"CRM not found at {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Add research notes to companies
    notes_updates = [
        ("Multiplex", "🎯 PRIORITY - Coomera Hospital ($1.1B) managing contractor. H2 2026 construction start. Will need PMs, Services Coordinators, Structural Engineers. Contact: QLD LinkedIn."),
        ("John Holland", "🎯 PRIORITY - Light Rail Stage 3 ($1.2B). Peak construction NOW. Need rail engineers, civil, electrical. Contact: GC office."),
        ("Hutchinson Builders", "🎯 PRIORITY - Massive GC pipeline. Royale ($176M), Lagoon ($198M), Sea Glass ($122M). Completing 2026. Will need PMs, Site Managers. Contact: GC office 07 5530 3200."),
        ("Icon Co", "🎯 PRIORITY - $150M GC residential. Was hiring PM Feb 2026 on Seek. Active. Contact: Seek/LinkedIn."),
        ("SIERA Group", "🎯 Tapestry ($80M+, 22-storey Chevron Island). Multiple GC projects. Contact: GC office."),
        ("Mosaic Property Group", "🎯 Sophia by Mosaic ($135M Palm Beach) + 3 other GC projects ($500M+). Contact: Brisbane HQ."),
    ]
    
    for company_name, note in notes_updates:
        # Check if company exists
        cursor.execute("SELECT id, notes FROM companies WHERE name LIKE ?", (f"%{company_name}%",))
        result = cursor.fetchone()
        if result:
            company_id, existing_notes = result
            new_notes = f"{existing_notes}\n\n{note}" if existing_notes else note
            cursor.execute("UPDATE companies SET notes = ? WHERE id = ?", (new_notes, company_id))
            print(f"✅ Updated: {company_name}")
        else:
            print(f"⚠️ Not found in CRM: {company_name}")
    
    conn.commit()
    conn.close()
    print("\n✅ CRM updated with lead research notes!")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--update-crm":
        update_crm_notes()
    else:
        generate_lead_brief()
        print("\n💡 To update CRM with these notes, run: python3 lead-research.py --update-crm")
