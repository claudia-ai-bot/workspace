#!/usr/bin/env python3
"""
Airtable CRM Setup - Create tables + populate sample data
"""

import os
import requests
import json
import time

# Config
# Set these from environment variables or pass as arguments
API_TOKEN = os.environ.get("AIRTABLE_TOKEN", "")
BASE_ID = os.environ.get("AIRTABLE_BASE_ID", "")
AIRTABLE_API = "https://api.airtable.com/v0/meta/bases"

HEADERS = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}

def create_table(table_name, fields):
    """Create a table with specified fields"""
    url = f"{AIRTABLE_API}/{BASE_ID}/tables"
    
    payload = {
        "name": table_name,
        "fields": fields
    }
    
    response = requests.post(url, json=payload, headers=HEADERS)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Table created: {table_name} (ID: {data['id']})")
        return data['id']
    else:
        print(f"❌ Error creating {table_name}: {response.status_code} - {response.text}")
        return None

def add_records(table_id, records):
    """Add records to a table"""
    url = f"https://api.airtable.com/v0/{BASE_ID}/{table_id}"
    
    payload = {
        "records": [
            {
                "fields": record
            }
            for record in records
        ]
    }
    
    response = requests.post(url, json=payload, headers=HEADERS)
    
    if response.status_code == 200:
        print(f"✅ Added {len(records)} records to {table_id}")
        return response.json()
    else:
        print(f"❌ Error adding records: {response.status_code} - {response.text}")
        return None

# Define fields for Companies table
companies_fields = [
    {"name": "Company Name", "type": "singleLineText"},
    {"name": "Location", "type": "singleLineText"},
    {"name": "Sector", "type": "singleSelect", "options": [
        {"name": "Commercial"},
        {"name": "Residential"},
        {"name": "Mixed-use"},
        {"name": "Heavy/Civil"},
        {"name": "Hospitality"}
    ]},
    {"name": "Website", "type": "url"},
    {"name": "Status", "type": "singleSelect", "options": [
        {"name": "Cold"},
        {"name": "Warm"},
        {"name": "Approached"},
        {"name": "Hired"}
    ]},
    {"name": "Current Projects", "type": "multilineText"},
    {"name": "Pipeline Projects", "type": "multilineText"},
    {"name": "Hiring Needs", "type": "multilineText"},
    {"name": "Notes", "type": "multilineText"}
]

# Define fields for Contacts table
contacts_fields = [
    {"name": "Contact Name", "type": "singleLineText"},
    {"name": "Company", "type": "singleLineText"},
    {"name": "Role", "type": "singleLineText"},
    {"name": "Title", "type": "singleLineText"},
    {"name": "Phone", "type": "phoneNumber"},
    {"name": "Email", "type": "email"},
    {"name": "LinkedIn", "type": "url"},
    {"name": "Last Contacted", "type": "date"},
    {"name": "Status", "type": "singleSelect", "options": [
        {"name": "Cold"},
        {"name": "Warm"},
        {"name": "Ready to hire"}
    ]},
    {"name": "Notes", "type": "multilineText"}
]

# Sample data
companies_data = [
    {
        "Company Name": "Meridian Property Group",
        "Location": "Southport",
        "Sector": "Mixed-use",
        "Website": "meridianproperty.com.au",
        "Status": "Cold",
        "Current Projects": "Southport Central Plaza (hotel + retail, $200M)",
        "Pipeline Projects": "Broadbeach Entertainment Precinct (planning stage)",
        "Hiring Needs": "Senior Estimator, Planning Director, Safety Director, HR Manager",
        "Notes": "Major developer. Southport Central = months away from approved (green light soon). Lisa is contact point."
    },
    {
        "Company Name": "Broadwater Developers",
        "Location": "Main Beach",
        "Sector": "Residential",
        "Website": "broadwaterdev.com.au",
        "Status": "Warm",
        "Current Projects": "The Pinnacle Main Beach (48 luxury apartments, $95M)",
        "Pipeline Projects": "Southport Waterfront Redevelopment (approval expected Q2)",
        "Hiring Needs": "HR Manager (luxury projects experience), Safety Director, Planning Engineer",
        "Notes": "Patricia very responsive. Southport project = major hiring phase coming (Q2-Q3)."
    },
    {
        "Company Name": "Helix Construction",
        "Location": "Robina",
        "Sector": "Commercial",
        "Website": "helixconstruction.com.au",
        "Status": "Cold",
        "Current Projects": "Robina Industrial Park Expansion (12,000 sqm, $45M)",
        "Pipeline Projects": "M1 Corridor Logistics Hub (TBA)",
        "Hiring Needs": "Senior PM, Estimator, Safety Manager",
        "Notes": "Strong commercial track record. James is approachable via LinkedIn."
    },
    {
        "Company Name": "Goldspan Group",
        "Location": "Surfers Paradise",
        "Sector": "Residential",
        "Website": "goldspan.com.au",
        "Status": "Cold",
        "Current Projects": "Surfers Paradise Towers (155 units, $85M)",
        "Pipeline Projects": "Broadbeach Commercial Hub (Stage 2, $120M)",
        "Hiring Needs": "Senior Estimator, Safety Director, Engineering Lead",
        "Notes": "Major GC developer, consistent pipeline. CEO is Michael Ford (worth researching)."
    },
    {
        "Company Name": "Apex Engineering & Contracting",
        "Location": "Nerang",
        "Sector": "Heavy/Civil",
        "Website": "apexengineering.com.au",
        "Status": "Cold",
        "Current Projects": "Nerang River Bridge Upgrade ($180M, govt contract)",
        "Pipeline Projects": "M1 Widening - Stage 3 (tendering)",
        "Hiring Needs": "Senior Project Manager (civil), Safety Manager, Engineering Manager",
        "Notes": "Government contracts. Robert harder to reach but worth the effort. High-value hires."
    }
]

contacts_data = [
    {"Contact Name": "Lisa Wong", "Company": "Meridian Property Group", "Role": "Development Manager", "Title": "Senior", "Phone": "+61755505678", "Email": "l.wong@meridian.com.au", "LinkedIn": "linkedin.com/in/lwong-development", "Status": "Cold", "Notes": "Development Manager, major $200M project"},
    {"Contact Name": "Patricia Grant", "Company": "Broadwater Developers", "Role": "Project Director", "Title": "Director", "Phone": "+61755913456", "Email": "p.grant@broadwater.com.au", "LinkedIn": "linkedin.com/in/pgrant-director", "Status": "Warm", "Notes": "Very responsive, luxury projects"},
    {"Contact Name": "Tom Richards", "Company": "Broadwater Developers", "Role": "Senior Estimator", "Title": "Senior", "Phone": "+61755913457", "Email": "t.richards@broadwater.com.au", "LinkedIn": "linkedin.com/in/trichards-estimator", "Status": "Cold", "Notes": "Estimator expertise"},
    {"Contact Name": "James Morrison", "Company": "Helix Construction", "Role": "Operations Manager", "Title": "Senior", "Phone": "+61755752345", "Email": "j.morrison@helix.com.au", "LinkedIn": "linkedin.com/in/jmorrison-construction", "Status": "Cold", "Notes": "Approachable via LinkedIn"},
    {"Contact Name": "David Mitchell", "Company": "Goldspan Group", "Role": "Development Director", "Title": "Senior", "Phone": "+61755501234", "Email": "d.mitchell@goldspan.com.au", "LinkedIn": "linkedin.com/in/davidmitchell-gc", "Status": "Cold", "Notes": "Major developer contact"},
    {"Contact Name": "Sarah Chen", "Company": "Goldspan Group", "Role": "Project Manager", "Title": "Senior PM", "Phone": "+61755501235", "Email": "s.chen@goldspan.com.au", "LinkedIn": "linkedin.com/in/sarahchen-pm", "Status": "Cold", "Notes": "Senior PM"},
    {"Contact Name": "Robert Carlisle", "Company": "Apex Engineering & Contracting", "Role": "Chief Operations Officer", "Title": "COO", "Phone": "+61755274567", "Email": "r.carlisle@apexeng.com.au", "LinkedIn": "linkedin.com/in/rcarlisle-coo", "Status": "Cold", "Notes": "Harder to reach but high-value"}
]

print("Starting Airtable setup...\n")

# Create Companies table
print("Creating Companies table...")
companies_table_id = create_table("Companies", companies_fields)
if companies_table_id:
    time.sleep(1)
    add_records(companies_table_id, companies_data)

print()

# Create Contacts table
print("Creating Contacts table...")
contacts_table_id = create_table("Contacts", contacts_fields)
if contacts_table_id:
    time.sleep(1)
    add_records(contacts_table_id, contacts_data)

print("\n✅ Airtable setup complete!")
print(f"Companies Table ID: {companies_table_id}")
print(f"Contacts Table ID: {contacts_table_id}")
