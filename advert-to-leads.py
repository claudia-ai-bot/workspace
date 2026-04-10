#!/usr/bin/env python3
"""
Parse job adverts → Extract leads (direct employers or client hints from agency adverts)
Intelligently populate the leads table with company, contact, role, and confidence scores
"""
import sqlite3
import re
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "crm.db"

# Known agency/recruiter keywords
AGENCY_KEYWORDS = [
    'recruit', 'staffing', 'search', 'talent', 'solutions', 'group', 'executive', 
    'hays', 'randstad', 'michael page', 'resourcing', '360', 'ri-kroot', 
    'jps', 'insight', 'focus', 'hudson', 'kelly', 'manpower', 'adzuna', 
    'linkedin jobs', 'indeed', 'seek', 'employment', 'placement',
    'advisor', 'consultant firm', 'consulting'
]

# Non-construction employers to skip
NON_CONSTRUCTION = [
    'westpac', 'cba', 'commonwealth', 'anz', 'nab', 'bank', 'financial',
    'accenture', 'deloitte', 'kpmg', 'pwc', 'tcs', 'infosys', 'cognizant',
    'apple', 'google', 'microsoft', 'amazon', 'meta', 'tech',
    'hotel', 'hospitality', 'restaurant', 'cafe', 'retail', 'grocery',
    'bunnings', 'sofitel', 'accor', 'hyatt', 'dnata', 'event', 'cinema',
    'law firm', 'legal', 'accounting', 'audit',
    'pharmaceutical', 'health', 'hospital', 'medical', 'clinic'
]

def is_non_construction(company_name):
    """Check if company is non-construction (finance, tech, retail, hospitality)"""
    name_lower = company_name.lower()
    return any(kw in name_lower for kw in NON_CONSTRUCTION)

def is_agency(company_name):
    """Check if company is a recruiter/agency"""
    return any(kw in company_name.lower() for kw in AGENCY_KEYWORDS)

def extract_client_hints(content):
    """
    Try to extract client company name from agency advert description
    Look for patterns like:
    - "Our client is..."
    - "Building for..."
    - "Working with..."
    - "Assisting a major..."
    - Project names (e.g. "Paradise Place", "Broadbeach Tower")
    """
    hints = []
    
    # Pattern: "Our client is [Company Name]"
    client_match = re.search(r'(?:our client|client|working with|for|assisting)\s+(?:a\s+)?(?:major\s+)?([A-Z][A-Za-z\s&]+?)(?:\.|,|\s+is|\s+to|\s+on)', content, re.IGNORECASE)
    if client_match:
        hints.append(client_match.group(1).strip())
    
    # Pattern: Project names (proper nouns)
    project_matches = re.findall(r'([A-Z][a-z]+\s+(?:Place|Tower|Development|Project|Building|Estate|Complex))', content)
    hints.extend(project_matches)
    
    # Pattern: "Developer/Builder: [Name]"
    dev_match = re.search(r'(?:developer|builder|contractor):\s*([A-Z][A-Za-z\s&]+?)(?:\.|,|$)', content, re.IGNORECASE)
    if dev_match:
        hints.append(dev_match.group(1).strip())
    
    return list(set(hints))  # dedupe

def find_company_in_crm(search_term):
    """Try to find company in CRM by name"""
    if not search_term:
        return None
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # Exact match first
    cur.execute('SELECT id, name FROM companies WHERE LOWER(name) = LOWER(?)', (search_term,))
    match = cur.fetchone()
    if match:
        conn.close()
        return match
    
    # Fuzzy match (partial)
    cur.execute('SELECT id, name FROM companies WHERE LOWER(name) LIKE LOWER(?)', (f'%{search_term}%',))
    matches = cur.fetchall()
    conn.close()
    
    return matches[0] if matches else None

def extract_role_info(title):
    """Extract role type from job title"""
    title_lower = title.lower()
    
    if "project manager" in title_lower or "pm" in title_lower:
        return "Project Manager"
    elif "site manager" in title_lower:
        return "Site Manager"
    elif "construction manager" in title_lower:
        return "Construction Manager"
    elif "quantity surveyor" in title_lower:
        return "Quantity Surveyor"
    elif "commercial manager" in title_lower:
        return "Commercial Manager"
    elif "contracts manager" in title_lower:
        return "Contracts Manager"
    
    return None

def extract_location_suburb(location):
    """Extract suburb from location string"""
    # Gold Coast suburbs
    suburbs = [
        "Surfers Paradise", "Broadbeach", "Mermaid Beach", "Miami", "Burleigh Heads",
        "Palm Beach", "Tallebudgera", "Varsity Lakes", "Robina", "Ashmore",
        "Molendinar", "Carrara", "Southport", "Main Beach", "Labrador",
        "Currumbin", "Tugun", "Mudgeeraba", "Boomerang", "Nerang",
        "Coomera", "Oxenford", "Helensvale", "Ormeau", "Guanaba"
    ]
    
    for suburb in suburbs:
        if suburb.lower() in location.lower():
            return suburb
    
    # Generic location if on Gold Coast
    if "gold coast" in location.lower():
        return "Gold Coast"
    
    return location

def create_lead(company_name, company_id, role, location, content, source, confidence):
    """Insert into leads table"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    try:
        cur.execute('''
            INSERT INTO leads (company, company_id, intel_type, source, what_it_means, action_trigger, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            company_name,
            company_id,
            f"Job Advert ({role})" if role else "Job Advert",
            source,
            f"Direct employer hiring (confidence: {confidence}%)",
            f"Call {company_name} about {location} {role or 'roles'}",
            datetime.now().isoformat()
        ))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"  Error inserting lead: {e}")
        conn.close()
        return False

def process_adverts(limit=None, sample_only=False):
    """Process job adverts → leads"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # Get adverts from last 72 hours (ordered by newest first, Gold Coast first)
    if limit:
        cur.execute('''
            SELECT id, title, created_at, location, content 
            FROM job_adverts 
            WHERE location LIKE '%Gold Coast%'
            AND datetime(created_at) > datetime('now', '-72 hours')
            ORDER BY created_at DESC 
            LIMIT ?
        ''', (limit,))
    else:
        cur.execute('''
            SELECT id, title, created_at, location, content 
            FROM job_adverts 
            WHERE location LIKE '%Gold Coast%'
            AND datetime(created_at) > datetime('now', '-72 hours')
            ORDER BY created_at DESC
        ''')
    
    adverts = cur.fetchall()
    conn.close()
    
    processed = 0
    created = 0
    
    print(f"\n{'='*80}")
    print(f"Processing {len(adverts)} Gold Coast job adverts → leads")
    print(f"{'='*80}\n")
    
    for i, advert in enumerate(adverts):
        if sample_only and i >= 10:
            print(f"\n... (showing sample of 10, {len(adverts)-10} more available)")
            break
        
        # Extract from advert
        title = advert['title']
        location = extract_location_suburb(advert['location'])
        content = advert['content']
        company_name = None
        company_id = None
        confidence = 0
        source = "Adzuna"
        
        # Parse content to get company (first line usually has it)
        lines = content.split('\n')
        first_line = lines[0] if lines else ""
        
        # Extract company from "DIRECT/AGENCY — CompanyName"
        company_match = re.search(r'(?:DIRECT EMPLOYER|VIA AGENCY)\s+—\s+(.+?)(?:\n|$)', first_line)
        if company_match:
            raw_company = company_match.group(1).strip()
            
            if is_agency(raw_company):
                # It's an agency - try to find the client
                hints = extract_client_hints(content)
                if hints:
                    # Try to match hints to CRM companies
                    for hint in hints:
                        crm_match = find_company_in_crm(hint)
                        if crm_match:
                            company_name = crm_match['name']
                            company_id = crm_match['id']
                            confidence = 60  # Medium confidence (deduced from agency advert)
                            print(f"[AGENCY → DEDUCED] {raw_company}")
                            print(f"  → Likely client: {company_name} (from hint: '{hint}')")
                            break
                
                if not company_name:
                    # Couldn't deduce client - skip for now
                    print(f"[AGENCY - SKIPPED] {raw_company}")
                    print(f"  → Couldn't determine client company")
                    processed += 1
                    continue
            
            else:
                # Direct employer
                crm_match = find_company_in_crm(raw_company)
                if crm_match:
                    company_name = crm_match['name']
                    company_id = crm_match['id']
                    confidence = 100
                    print(f"[DIRECT - MATCHED] {company_name}")
                else:
                    company_name = raw_company
                    company_id = None
                    confidence = 95  # High confidence but not in CRM yet
                    print(f"[DIRECT - NEW] {company_name}")
        
        # Extract role
        role = extract_role_info(title)
        
        # Create lead
        if company_name:
            if create_lead(company_name, company_id, role, location, content, source, confidence):
                print(f"  Role: {role or title}")
                print(f"  Location: {location}")
                print()
                created += 1
        
        processed += 1
    
    print(f"{'='*80}")
    print(f"Processed: {processed} | Created leads: {created}")
    print(f"{'='*80}\n")
    
    return processed, created

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--all":
        # Process all
        processed, created = process_adverts()
    else:
        # Sample first
        print("SAMPLE MODE (showing first 10)")
        processed, created = process_adverts(limit=100, sample_only=True)
        print("\nTo process all: python3 advert-to-leads.py --all")
