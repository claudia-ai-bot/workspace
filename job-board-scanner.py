#!/usr/bin/env python3
"""
Job Board Scanner using Adzuna API
Scans for construction recruitment roles in SEQ
"""
import json
import sqlite3
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

# Config
KEYS_PATH = Path(__file__).parent / "adzuna_keys.json"
DB_PATH = Path(__file__).parent / "crm.db"

# Search parameters for construction recruitment
SEARCH_QUERIES = [
    # Core white-collar roles only
    "project manager construction",
    "senior project manager construction",
    "construction manager",
    "senior construction manager",
    # Commercial
    "quantity surveyor construction",
    "senior quantity surveyor",
    "commercial manager construction",
    "contracts manager construction",
    "contract manager construction",
    "estimator construction",
    "senior estimator",
    # Leadership
    "project director construction",
    "general manager construction",
    "operations manager construction",
    "development manager construction",
    # Design management
    "design manager construction",
]

LOCATIONS = [
    "Gold Coast",
    "Gold Coast Queensland",
    "Brisbane",
    "Sunshine Coast",
    "Ipswich Queensland",
    "Logan Queensland",
    "Southeast Queensland",
]

def load_keys():
    with open(KEYS_PATH) as f:
        return json.load(f)

def search_adzuna(query, location, page=1, results_per_page=20):
    """Search Adzuna API"""
    keys = load_keys()
    
    what = urllib.parse.quote(query)
    where = urllib.parse.quote(location)
    
    url = f"https://api.adzuna.com/v1/api/jobs/au/search/{page}"
    url += f"?app_id={keys['app_id']}&app_key={keys['app_key']}"
    url += f"&what={what}&where={where}&results_per_page={results_per_page}&max_days_old=1"
    
    try:
        with urllib.request.urlopen(url, timeout=15) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        print(f"Error searching {query} in {location}: {e}")
        return None

# Keywords to filter out (agencies + non-construction companies)
AGENCY_KEYWORDS = [
    'recruit', 'staffing', 'search', 'staff', 'talent', 
    'solutions', 'group', 'executive', 'human capital', 
    'human', 'page', 'hays', 'randstad', 'michael page',
    # Non-construction companies that appear in job ads
    'first focus', 'global 360', 'insight', 'ri-kroot'
]

def is_direct_employer(company_name):
    """Check if company is a direct employer (not an agency)"""
    name_lower = company_name.lower()
    return not any(kw in name_lower for kw in AGENCY_KEYWORDS)

def extract_jobs(results):
    """Extract job data from API results"""
    jobs = []
    
    for job in results.get("results", []):
        # Skip jobs outside SEQ (keep if no location = national role)
        loc = job.get("location", {}).get("display_name", "").lower()
        if loc and not any(l in loc for l in ["gold coast", "brisbane", "sunshine coast", "ipswich", "logan", "queensland", "qld"]):
            continue
        
        # Tag whether it's a direct employer or agency (don't skip agencies — useful intel)
        company = job.get("company", {}).get("display_name", "")
            
        # Extract data
        jobs.append({
            "title": job.get("title"),
            "company": job.get("company", {}).get("display_name"),
            "location": job.get("location", {}).get("display_name"),
            "salary_min": job.get("salary_min"),
            "salary_max": job.get("salary_max"),
            "description": job.get("description", "")[:500],
            "url": job.get("redirect_url") or job.get("url"),
            "adzuna_id": job.get("adzuna_id"),
            "date_posted": job.get("created"),
        })
    
    return jobs

def save_to_db(jobs):
    """Save jobs to job_adverts table"""
    if not jobs:
        print("No new jobs to save")
        return 0
    
    db = sqlite3.connect(DB_PATH)
    saved = 0
    
    for job in jobs:
        # Check if URL already exists
        existing = db.execute(
            "SELECT id FROM job_adverts WHERE url = ?", (job["url"],)
        ).fetchone()
        
        if existing:
            continue
        
        # Determine tier based on salary
        sal = job["salary_min"] or job["salary_max"] or 0
        if sal > 200000:
            tier = "Tier 1"
        elif sal > 150000:
            tier = "Tier 2"
        else:
            tier = "Consultant"
        
        # Determine sector from title
        title = job["title"].lower()
        if "residential" in title or "apartment" in title:
            sector = "Residential"
        elif "commercial" in title or "office" in title:
            sector = "Commercial"
        elif "infrastructure" in title or "road" in title or "civil" in title:
            sector = "Infrastructure"
        elif "industrial" in title or "warehouse" in title:
            sector = "Industrial"
        else:
            sector = "Commercial"
        
        # Determine role_type
        role_type = determine_role_type(job["title"])
        
        # Estimate project size from salary
        if sal > 250000:
            project_size = "$100M+"
        elif sal > 180000:
            project_size = "$50M-$100M"
        elif sal > 130000:
            project_size = "$20M-$50M"
        else:
            project_size = "$5M-$20M"
        
        # Build content
        salary_str = f"${job['salary_min']:,.0f}" if job["salary_min"] else ""
        if job["salary_max"]:
            salary_str += f" - ${job['salary_max']:,.0f}" if salary_str else f"Up to ${job['salary_max']:,.0f}"
        
        employer_type = "DIRECT EMPLOYER" if is_direct_employer(job['company']) else "VIA AGENCY"
        content = f"""{employer_type} — {job['company']}

Location: {job['location']}
Salary: {salary_str if salary_str else 'Not listed'}
Posted: {job['date_posted']}

Description:
{job['description']}

Apply: {job['url']}"""

        db.execute("""
            INSERT INTO job_adverts 
            (title, tier, sector, project_size, location, content, role_type, created_at, adzuna_id, url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            job["title"], tier, sector, project_size, 
            job["location"], content, role_type, datetime.now().isoformat(),
            str(job.get("adzuna_id", "")), job.get("url", "")
        ))
        saved += 1
    
    db.commit()
    db.close()
    return saved

def determine_role_type(title):
    """Map title to role_type"""
    t = title.lower()
    
    if "senior project manager" in t or "spm" in t:
        return "Senior Project Manager"
    if "project manager" in t or "pm " in t:
        return "Project Manager"
    if "commercial manager" in t:
        return "Commercial Manager"
    if "construction manager" in t:
        return "Construction Manager"
    if "site manager" in t or "site supervisor" in t:
        return "Site Manager"
    if "contracts manager" in t:
        return "Contracts Manager"
    if "quantity surveyor" in t or "qs " in t:
        return "Quantity Surveyor"
    if "senior estimator" in t:
        return "Senior Estimator"
    if "estimator" in t:
        return "Estimator"
    if "design manager" in t:
        return "Design Manager"
    if "safety" in t or "hsseq" in t:
        return "HSSEQ Manager"
    if "procurement" in t:
        return "Procurement Manager"
    if "program manager" in t:
        return "Program Manager"
    if "project engineer" in t:
        return "Project Engineer"
    if "bid manager" in t:
        return "Bid Manager"
    
    return "Project Manager"  # default

def main():
    print(f"🔍 Job Board Scanner — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 50)
    
    total_found = 0
    total_saved = 0
    
    for query in SEARCH_QUERIES:
        for location in LOCATIONS:
            results = search_adzuna(query, location)
            if results:
                jobs = extract_jobs(results)
                saved = save_to_db(jobs)
                total_found += len(jobs)
                total_saved += saved
                print(f"  {query[:30]:30} | {location:20} → {len(jobs)} found, {saved} new")
    
    print("=" * 50)
    print(f"Total: {total_found} found, {total_saved} new jobs saved to CRM")

if __name__ == "__main__":
    main()
