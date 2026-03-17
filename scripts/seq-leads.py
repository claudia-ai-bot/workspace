#!/usr/bin/env python3
"""
SEQ Construction Lead Generator - Finds companies for Chris to pitch to
Builds a prospect list from known SEQ construction companies
"""
import json
import os
from datetime import datetime

PROSPECTS_FILE = "/home/chris/.openclaw/workspace/memory/construction-prospects.json"

# Known SEQ Construction Companies (for Lead Group to target)
CONSTRUCTION_PROSPECTS = [
    {"name": "Hutchinson Builders", "sector": "Commercial", "size": "Large", "location": "Brisbane"},
    {"name": "BMD Group", "sector": "Civil", "size": "Large", "location": "Brisbane"},
    {"name": "ADCO Group", "sector": "Commercial", "size": "Large", "location": "Gold Coast"},
    {"name": "Sinclair Group", "sector": "Commercial", "size": "Medium", "location": "Gold Coast"},
    {"name": "Pettina Group", "sector": "Commercial", "size": "Medium", "location": "Gold Coast"},
    {"name": "ABD Group", "sector": "Commercial", "size": "Medium", "location": "Brisbane"},
    {"name": "Waterway Constructions", "sector": "Civil", "size": "Medium", "location": "Brisbane"},
    {"name": "Starr Industrial", "sector": "Industrial", "size": "Medium", "location": "Brisbane"},
    {"name": "Cooper Group", "sector": "Commercial", "size": "Medium", "location": "Gold Coast"},
    {"name": "W纪录 Building", "sector": "Commercial", "size": "Small", "location": "Gold Coast"},
    {"name": "R性地產", "sector": "Commercial", "size": "Large", "location": "Gold Coast"},
    {"name": "JQZ", "sector": "Commercial", "size": "Medium", "location": "Gold Coast"},
    {"name": "Sunland Group", "sector": "Commercial", "size": "Medium", "location": "Gold Coast"},
    {"name": "Villa World", "sector": "Residential", "size": "Medium", "location": "Gold Coast"},
    {"name": "Metricon", "sector": "Residential", "size": "Large", "location": "Gold Coast"},
]

def generate_prospect_list():
    """Load or generate prospect list"""
    os.makedirs(os.path.dirname(PROSPECTS_FILE), exist_ok=True)
    
    prospects = CONSTRUCTION_PROSPECTS.copy()
    
    # Add metadata
    for p in prospects:
        p['added'] = datetime.now().isoformat()
        p['status'] = 'Cold'
        p['notes'] = ''
    
    with open(PROSPECTS_FILE, 'w') as f:
        json.dump(prospects, f, indent=2)
    
    return prospects

def display_prospects():
    """Show prospect list"""
    prospects = generate_prospect_list()
    
    print("=" * 60)
    print("🏗️ SEQ CONSTRUCTION PROSPECTS")
    print("=" * 60)
    print(f"Total: {len(prospects)} companies\n")
    
    by_location = {}
    for p in prospects:
        loc = p['location']
        if loc not in by_location:
            by_location[loc] = []
        by_location[loc].append(p)
    
    for loc, companies in by_location.items():
        print(f"📍 {loc} ({len(companies)})")
        for c in companies:
            print(f"   • {c['name']} - {c['sector']} ({c['size']})")
        print()
    
    print("=" * 60)
    return prospects

if __name__ == "__main__":
    display_prospects()
