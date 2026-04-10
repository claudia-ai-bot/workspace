#!/usr/bin/env python3
"""
Parse job adverts → Extract leads (construction industry only)
Direct employers + deduced clients from agency adverts (last 72 hours)
"""
import sqlite3
import re
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "crm.db"

AGENCY_KEYWORDS = [
    'recruit', 'staffing', 'search', 'talent', 'solutions', 'group', 'executive', 
    'hays', 'randstad', 'michael page', 'resourcing', '360', 'ri-kroot', 
    'jps', 'insight', 'focus', 'hudson', 'kelly', 'manpower',
    'frontline', 'people2people', 'six degrees', 'white collar', 'blue collar',
    'fuse', 'finite', 'paxus', 'clarius', 'porterallen', 'beaumont'
]

NON_CONSTRUCTION = [
    'westpac', 'cba', 'commonwealth', 'anz', 'nab', 'bank', 'financial',
    'accenture', 'deloitte', 'kpmg', 'pwc', 'tcs', 'infosys', 'cognizant',
    'apple', 'google', 'microsoft', 'amazon', 'meta', 'tech',
    'hotel', 'hospitality', 'restaurant', 'cafe', 'retail', 'grocery', 'bunnings',
    'sofitel', 'accor', 'hyatt', 'dnata', 'event', 'cinema', 'village roadshow',
    'law firm', 'legal', 'accounting', 'audit', 'lawyer',
    'pharmaceutical', 'health', 'hospital', 'medical', 'clinic', 'chef',
    'griffith', 'university', 'education'
]

# WHITELIST: Only these construction roles matter
KEEP_ROLES = [
    'project manager', 'senior project manager',
    'construction manager', 'senior construction manager',
    'commercial manager',
    'estimator', 'senior estimator', 'construction estimator',
    'project director',
    'quantity surveyor', 'senior quantity surveyor',
    'contracts manager', 'contract manager',
    'project controls'
]

# Roles to explicitly exclude even if they contain whitelist keywords
EXCLUDE_ROLES = [
    'business development', 'sales manager', 'account manager',
    'marketing', 'people & culture', 'hr manager', 'recruitment manager',
    'property manager', 'asset manager', 'fund manager',
    'civil designer', 'urban designer', 'landscape', 'urban planner',
    'water resources', 'hydraulic', 'environmental', 'heritage',
    'graduate', 'cadet', 'intern', 'administration', 'coordinator'
]

def should_exclude_role(title):
    title_lower = title.lower()
    return any(ex in title_lower for ex in EXCLUDE_ROLES)

def should_keep_role(title):
    """Check if role is in the whitelist"""
    title_lower = title.lower()
    return any(keep in title_lower for keep in KEEP_ROLES)

def is_agency(company_name):
    return any(kw in company_name.lower() for kw in AGENCY_KEYWORDS)

def is_non_construction(company_name):
    return any(kw in company_name.lower() for kw in NON_CONSTRUCTION)

def is_blacklisted(company_name):
    """Check if company is blacklisted (e.g. recruitment firms we don't want as leads)"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM company_blacklist WHERE LOWER(company_name) = LOWER(?) LIMIT 1", (company_name,))
    result = cur.fetchone()
    conn.close()
    return result is not None

def find_company_in_crm(search_term):
    if not search_term:
        return None
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute('SELECT id, name FROM companies WHERE LOWER(name) LIKE LOWER(?)', (f'%{search_term}%',))
    match = cur.fetchone()
    conn.close()
    return match

def extract_role_info(title):
    title_lower = title.lower()
    if "project director" in title_lower:
        return "Project Director"
    elif "project manager" in title_lower:
        return "Project Manager"
    elif "construction manager" in title_lower:
        return "Construction Manager"
    elif "commercial manager" in title_lower:
        return "Commercial Manager"
    elif "contracts manager" in title_lower or "contract manager" in title_lower:
        return "Contracts Manager"
    elif "quantity surveyor" in title_lower or " qs " in title_lower:
        return "Quantity Surveyor"
    elif "estimator" in title_lower:
        return "Estimator"
    elif "development manager" in title_lower:
        return "Development Manager"
    elif "project controls" in title_lower:
        return "Project Controls"
    return title  # Fall back to actual title if no match

def extract_location_suburb(location):
    suburbs = ["Surfers Paradise", "Broadbeach", "Mermaid Beach", "Miami", "Burleigh Heads",
               "Palm Beach", "Tallebudgera", "Varsity Lakes", "Robina", "Ashmore",
               "Molendinar", "Carrara", "Southport", "Main Beach", "Labrador",
               "Currumbin", "Tugun", "Mudgeeraba", "Boomerang", "Nerang",
               "Coomera", "Oxenford", "Helensvale", "Ormeau", "Guanaba"]
    for suburb in suburbs:
        if suburb.lower() in location.lower():
            return suburb
    if "gold coast" in location.lower():
        return "Gold Coast"
    return location

def process_adverts(limit=None):
    """Process job adverts → leads (construction only, last 72 hours)"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    if limit:
        cur.execute('''SELECT id, title, created_at, location, content, url 
                       FROM job_adverts 
                       WHERE (location LIKE '%Gold Coast%' OR location LIKE '%Brisbane%' OR location LIKE '%Queensland%' OR location LIKE '%SEQ%')
                       AND url IS NOT NULL AND url != '' AND url != 'None'
                       AND datetime(created_at) > datetime('now', '-72 hours')
                       ORDER BY created_at DESC LIMIT ?''', (limit,))
    else:
        cur.execute('''SELECT id, title, created_at, location, content, url 
                       FROM job_adverts 
                       WHERE (location LIKE '%Gold Coast%' OR location LIKE '%Brisbane%' OR location LIKE '%Queensland%' OR location LIKE '%SEQ%')
                       AND url IS NOT NULL AND url != '' AND url != 'None'
                       AND datetime(created_at) > datetime('now', '-72 hours')
                       ORDER BY created_at DESC''')
    
    adverts = cur.fetchall()
    conn.close()
    
    processed = 0
    created = 0
    skipped_non_construction = 0
    
    print(f"\n{'='*80}")
    print(f"Processing {len(adverts)} Gold Coast adverts (last 72h) → construction leads")
    print(f"{'='*80}\n")
    
    for advert in adverts:
        title = advert['title']
        location = extract_location_suburb(advert['location'])
        content = advert['content']
        company_name = None
        company_id = None
        confidence = 0
        
        lines = content.split('\n')
        first_line = lines[0] if lines else ""
        company_match = re.search(r'(?:DIRECT EMPLOYER|VIA AGENCY)\s+—\s+(.+?)(?:\n|$)', first_line)
        
        if company_match:
            raw_company = company_match.group(1).strip()
            
            # Skip non-construction companies
            if is_non_construction(raw_company):
                skipped_non_construction += 1
                processed += 1
                continue

            # Skip blacklisted companies (e.g. recruitment agencies posting job ads)
            if is_blacklisted(raw_company):
                processed += 1
                continue
            
            # Only process direct employers
            if not is_agency(raw_company):
                # Only keep whitelisted construction roles, exclude non-construction
                if not should_keep_role(title) or should_exclude_role(title):
                    processed += 1
                    continue
                
                crm_match = find_company_in_crm(raw_company)
                if crm_match:
                    company_name = crm_match['name']
                    company_id = crm_match['id']
                    confidence = 100
                    print(f"[MATCHED] {company_name}")
                else:
                    company_name = raw_company
                    company_id = None
                    confidence = 95
                    print(f"[NEW] {company_name}")
                
                role = extract_role_info(title)
                
                conn = sqlite3.connect(DB_PATH)
                cur = conn.cursor()
                try:
                    what_it_means = f"Actively hiring: {role} in {location}" if role else f"Actively hiring in {location}"
                    now = datetime.now().isoformat()
                    today = datetime.now().strftime('%Y-%m-%d')
                    cur.execute('''INSERT INTO leads (date, company, company_id, intel_type, source, what_it_means, action_trigger, created_at, job_advert_id, location)
                                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                               (today, company_name, company_id, f"Job Advert ({role})" if role else "Job Advert",
                                "Adzuna", what_it_means,
                                f"Call {company_name} about {location} {role or 'roles'}",
                                now, advert['id'], location))
                    conn.commit()
                    print(f"  Role: {role or title[:50]}")
                    print(f"  Location: {location}\n")
                    created += 1
                except Exception as e:
                    print(f"  Error: {e}\n")
                finally:
                    conn.close()
        
        processed += 1
    
    print(f"{'='*80}")
    print(f"Processed: {processed} | Created: {created} | Skipped (non-construction): {skipped_non_construction}")
    print(f"{'='*80}\n")
    
    return processed, created

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--all":
        process_adverts()
    else:
        print("SAMPLE MODE (first 50)")
        process_adverts(limit=100)
        print("\nTo process all: python3 advert-to-leads-v2.py --all")
