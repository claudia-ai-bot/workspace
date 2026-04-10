#!/usr/bin/env python3
"""
Contact Enricher — scrapes email and phone for CRM contacts
Uses SerpAPI + web_fetch to find contact details from public sources
"""
import sqlite3
import urllib.request
import urllib.parse
import json
import re
import time
from pathlib import Path

DB_PATH = Path(__file__).parent / "crm.db"
SERPAPI_KEY = '29ffd1d56fe9c2e071a3f83e92e66e0b64aa3ea399296d7fcb81731d3e15d967'
HUNTER_KEY = 'a4309eac38a707b805e3437cf8ab968056fb15e8'

# Company domain map
DOMAINS = {
    'AECOM': 'aecom.com',
    'Stantec': 'stantec.com',
    'Golding Contractors': 'golding.com.au',
    'UGL Group': 'ugllimited.com',
    'Veolia': 'veolia.com.au',
    'Alder Group': 'aldergroup.com.au',
    'Gurner': 'gurner.com.au',
    'Aniko Group': 'anikogroup.com.au',
    'Multiplex': 'multiplex.global',
    'Lendlease': 'lendlease.com',
    'Laing ORourke': 'laingorourke.com',
    'CPB Contractors (CIMIC)': 'cpbcontractors.com.au',
    'John Holland': 'johnholland.com.au',
    'McNab': 'mcnab.com.au',
    'ACCIONA': 'acciona.com.au',
    'ADCO Constructions': 'adco.com.au',
    'SHAPE Australia': 'shape.com.au',
    'Hansen Yuncken': 'hansenyuncken.com.au',
    'Buildcorp': 'buildcorp.com.au',
    'FKG Group': 'fkg.com.au',
    'BMD Group': 'bmd.com.au',
    'Georgiou Group': 'georgiou.com.au',
    'Mainbrace Constructions': 'mainbrace.com.au',
    'Richard Crookes': 'richardcrookes.com.au',
    'BADGE Constructions': 'badge.net.au',
    'Hutchinson Builders': 'hutchinsonbuilders.com.au',
    'Icon Co': 'icon.co',
    'Rohrig Constructions': 'rohrig.com.au',
    'Turner & Townsend': 'turnerandtownsend.com',
    'RCP Australia': 'rcpaustralia.com.au',
    'Seymour Whyte (VINCI)': 'seymourwhyte.com.au',
}

def clean_email(text):
    """Extract email from text"""
    match = re.search(r'\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b', text)
    return match.group(0).lower() if match else None

def clean_phone(text):
    """Extract AU phone from text"""
    # Match AU formats: 04xx xxx xxx, +61 4xx, 07 xxxx xxxx
    match = re.search(r'(?:\+61\s?|0)(?:4\d{2}\s?\d{3}\s?\d{3}|[2378]\s?\d{4}\s?\d{4})', text)
    if match:
        phone = re.sub(r'\s', '', match.group(0))
        return phone
    return None

def search_contact_details(name, company):
    """Search for email/phone via SerpAPI"""
    query = f'"{name}" "{company}" email OR phone contact'
    encoded = urllib.parse.quote(query)
    url = f'https://serpapi.com/search?q={encoded}&api_key={SERPAPI_KEY}&num=5'
    
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            data = json.loads(r.read().decode())
        
        full_text = ' '.join([
            r.get('title', '') + ' ' + r.get('snippet', '')
            for r in data.get('organic_results', [])
        ])
        
        email = clean_email(full_text)
        phone = clean_phone(full_text)
        return email, phone
    except Exception as e:
        return None, None

def hunter_email(name, company):
    """Try Hunter.io email finder for a specific person"""
    domain = DOMAINS.get(company)
    if not domain:
        return None
    
    parts = name.strip().split()
    if len(parts) < 2:
        return None
    
    first = parts[0]
    last = parts[-1]
    
    url = f'https://api.hunter.io/v2/email-finder?domain={domain}&first_name={first}&last_name={last}&api_key={HUNTER_KEY}'
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            data = json.loads(r.read().decode())
        email = data.get('data', {}).get('email')
        return email
    except:
        return None

def guess_email(name, company):
    """Guess email based on common patterns + domain"""
    domain = DOMAINS.get(company)
    if not domain:
        return None
    
    parts = name.strip().lower().split()
    if len(parts) < 2:
        return None
    
    first = parts[0]
    last = parts[-1]
    
    # Most common AU construction patterns
    patterns = [
        f'{first}.{last}@{domain}',
        f'{first[0]}{last}@{domain}',
        f'{first}@{domain}',
    ]
    return patterns[0]  # Return most likely pattern

def run_enrichment(dry_run=False):
    """Enrich all contacts missing email/phone"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # Get contacts with real names (skip TBC entries)
    cur.execute('''SELECT id, contact_name, company, personal_detail, email, phone
                   FROM contacts
                   WHERE contact_name NOT LIKE "TBC%"
                   AND contact_name != ""
                   AND (email IS NULL OR email = "" OR phone IS NULL OR phone = "")
                   ORDER BY company''')
    contacts = cur.fetchall()
    
    print(f'\n📧 Contact Enricher — {len(contacts)} contacts to process\n')
    print(f'{"NAME":30} {"COMPANY":25} {"EMAIL":35} {"PHONE":15}')
    print('='*110)
    
    updated = 0
    
    for contact in contacts:
        name = contact['contact_name']
        company = contact['company']
        has_email = bool(contact['email'])
        has_phone = bool(contact['phone'])
        
        email = contact['email']
        phone = contact['phone']
        
        # Step 1: Try Hunter for email
        if not has_email:
            hunter = hunter_email(name, company)
            if hunter:
                email = hunter
        
        # Step 2: SerpAPI search for both
        if not email or not has_phone:
            found_email, found_phone = search_contact_details(name, company)
            if found_email and not email:
                email = found_email
            if found_phone and not phone:
                phone = found_phone
        
        # Step 3: Guess email if still nothing
        if not email:
            guessed = guess_email(name, company)
            if guessed:
                email = f'~{guessed}'  # Prefix ~ to mark as guessed
        
        print(f'{name[:29]:30} {company[:24]:25} {(email or "-")[:34]:35} {(phone or "-")[:14]:15}')
        
        if not dry_run and (email or phone):
            cur.execute('''UPDATE contacts SET email = ?, phone = ? WHERE id = ?''',
                       (email if email else contact['email'],
                        phone if phone else contact['phone'],
                        contact['id']))
            updated += 1
        
        time.sleep(0.8)
    
    if not dry_run:
        conn.commit()
        print(f'\n✅ Updated {updated} contacts')
    else:
        print(f'\n[DRY RUN] Would update {updated} contacts')
    
    conn.close()

if __name__ == "__main__":
    import sys
    dry = '--dry-run' in sys.argv
    run_enrichment(dry_run=dry)
