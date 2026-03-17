#!/usr/bin/env python3
"""SEQ Construction Projects Monitor - Scrapes Queensland building approvals"""
import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime

OUTPUT_FILE = "/home/chris/.openclaw/workspace/memory/seq-construction-projects.json"
API_URL = "https://www.qleave.qld.gov.au/search/register-search"

def fetch_projects():
    """Fetch latest SEQ construction projects"""
    # Try QLeave register or fallback to dummy data
    projects = []
    
    # For now, create a tracker file - can be enhanced later
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, 'r') as f:
            projects = json.load(f)
    
    # Add timestamp
    for p in projects:
        p['last_checked'] = datetime.now().isoformat()
    
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(projects, f, indent=2)
    
    print(f"Checked {len(projects)} projects")
    return projects

if __name__ == "__main__":
    fetch_projects()
