#!/usr/bin/env python3
"""
Direct Company Careers Scraper — Multi-Platform
Uses Playwright to scrape careers pages across different ATS platforms.
Runs weekly, zero API cost.

Supported platforms:
- Workday (myworkdayjobs.com)
- PageUp (pageuppeople.com)  
- SmartRecruiters
- Custom career pages
- Fallback: SerpAPI site search
"""
import sqlite3
import re
import time
import json
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "crm.db"
SERPAPI_KEY = '29ffd1d56fe9c2e071a3f83e92e66e0b64aa3ea399296d7fcb81731d3e15d967'  # legacy, replaced by Exa
EXA_API_KEY = 'ab647372-46fd-423f-86ed-fcb9df6045a7'

KEEP_ROLES = [
    'project manager', 'construction manager', 'commercial manager',
    'quantity surveyor', 'project director', 'contracts manager', 'contract manager',
    'senior project', 'general manager', 'operations manager', 'regional manager',
    'program manager', 'programme manager', 'construction director'
]
EXCLUDE_ROLES = [
    'graduate', 'cadet', 'estimator', 'site manager', 'foreman', 'supervisor',
    'superintendent', 'marketing', 'hr ', 'human resources', 'accountant',
    'finance', 'it ', 'software', 'intern', 'apprentice', 'business development',
    'civil designer', 'water resources', 'sales', 'office manager', 'administrator',
    'receptionist', 'cleaner', 'labour', 'laborer', 'labourer', 'truck driver',
    'equipment operator', 'electrician', 'plumber', 'crane operator'
]

# Company → careers URL mapping
# Format: (url, platform)
# platform: workday | pageup | smartrecruiters | custom | seek
COMPANY_CAREERS = {
    'Lendlease':              ('https://lendlease.wd3.myworkdayjobs.com/lendleasecareers', 'workday'),
    'ACCIONA':                ('https://acciona.wd3.myworkdayjobs.com/ACCIONA', 'workday'),
    'CPB Contractors (CIMIC)':('https://jobs.pageuppeople.com/727/au/en/listing/', 'pageup'),
    'John Holland':           ('https://careers.johnholland.com.au/caw/en/listing/', 'pageup'),
    'Multiplex':              ('https://careers.multiplex.global/go/All-Jobs/3775501/', 'pageup'),
    'Laing ORourke':          ('https://careers.laingorourke.com.au/go/All-Jobs/8099001/', 'pageup'),
    'Turner & Townsend':      ('https://turnerandtownsend.com/en/careers/search-jobs/', 'custom'),
    'SHAPE Australia':        ('https://www.shape.com.au/careers/current-opportunities/', 'custom'),
    'Hansen Yuncken':         ('https://hansenyuncken.pageuppeople.com/759/au/en/listing/', 'pageup'),
    'Hutchinson Builders':    ('https://www.hutchinsonbuilders.com.au/careers/current-vacancies/', 'custom'),
    'ADCO Constructions':     ('https://www.adco.com.au/careers/current-opportunities/', 'custom'),
    'FKG Group':              ('https://www.fkg.com.au/careers/', 'custom'),
    'Georgiou Group':         ('https://www.georgiou.com.au/careers/', 'custom'),
    'McNab':                  ('https://www.mcnab.com.au/join-us/', 'custom'),
    'BMD Group':              ('https://www.bmd.com.au/careers/', 'custom'),
    'Buildcorp':              ('https://www.buildcorp.com.au/careers/current-vacancies/', 'custom'),
    'BADGE Constructions':    ('https://www.badge.net.au/careers/', 'custom'),
    'Seymour Whyte (VINCI)':  ('https://www.seymourwhyte.com.au/careers/', 'custom'),
    'Rohrig Constructions':   ('https://www.rohrig.com.au/careers/', 'custom'),
    'Richard Crookes':        ('https://www.richardcrookes.com.au/careers/', 'custom'),
    'Mainbrace Constructions': ('https://www.mainbrace.com.au/careers/', 'custom'),
}

def db_connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def today():
    return datetime.now().strftime('%Y-%m-%d')

def is_relevant_role(title):
    t = title.lower().strip()
    if len(t) < 8 or len(t) > 100:
        return False
    if any(ex in t for ex in EXCLUDE_ROLES):
        return False
    return any(keep in t for keep in KEEP_ROLES)

def detect_sector(text):
    t = text.lower()
    if any(x in t for x in ['civil', 'road', 'bridge', 'rail', 'pipeline', 'infrastructure', 'drainage']):
        return 'Civil Infrastructure'
    if any(x in t for x in ['residential', 'apartment', 'townhouse', 'housing', 'high rise', 'high-rise']):
        return 'Residential'
    if any(x in t for x in ['industrial', 'warehouse', 'logistics']):
        return 'Industrial'
    if any(x in t for x in ['commercial', 'office', 'fitout']):
        return 'Commercial'
    return 'Construction'

AU_LOCATIONS = ['queensland', 'gold coast', 'brisbane', 'sunshine coast', 'ipswich',
                'new south wales', 'victoria', 'western australia', 'south australia',
                'canberra', 'australia', ', qld', ', nsw', ', vic', ', wa', ', sa']
OVERSEAS = ['malaysia', 'singapore', 'china', 'uk', 'london', 'new zealand', 
            'dubai', 'hong kong', 'usa', 'canada', 'india']

def extract_jobs_from_text(text, company_name=None, au_only=True):
    """Extract job titles from page text, with optional AU-only filter"""
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    jobs = []
    
    skip_patterns = ['privacy', 'copyright', 'terms', 'cookie', 'subscribe',
                    'follow us', 'contact us', 'sign in', 'log in', 'apply now',
                    'read more', 'learn more', 'view all', 'back to', 'posted on',
                    'posted today', 'days ago', 'req-']
    
    for i, line in enumerate(lines):
        line = re.sub(r'\s+', ' ', line).strip()
        if len(line) < 8 or len(line) > 120:
            continue
        if any(s in line.lower() for s in skip_patterns):
            continue
        
        if is_relevant_role(line):
            # Check location context (next 6 lines)
            context = ' '.join(lines[i+1:i+7]).lower()
            
            if au_only:
                is_au = any(loc in context for loc in AU_LOCATIONS)
                is_overseas = any(x in context for x in OVERSEAS)
                if not is_au or is_overseas:
                    continue
            
            # Extract specific location
            location = 'Australia'
            for loc_line in lines[i+1:i+5]:
                ll = loc_line.lower()
                if 'gold coast' in ll:
                    location = 'Gold Coast'
                    break
                elif 'brisbane' in ll or 'queensland' in ll:
                    location = 'Brisbane'
                    break
                elif any(l in ll for l in AU_LOCATIONS):
                    location = loc_line[:40]
                    break
            
            # Clean title
            clean = re.sub(r'\s*[-–|]\s*(Gold Coast|Brisbane|Queensland|Australia|QLD|Permanent|Full.?time).*$', '', line, flags=re.I).strip()
            if is_relevant_role(clean):
                jobs.append((clean, location))
    
    # Deduplicate by title
    seen = set()
    unique = []
    for job, loc in jobs:
        if job not in seen:
            seen.add(job)
            unique.append((job, loc))
    
    return unique

def scrape_with_playwright(url, platform, company_name):
    """Scrape a careers page using Playwright"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return []
    
    jobs = []
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36')
            
            page.goto(url, timeout=25000, wait_until='domcontentloaded')
            
            # Accept cookies if prompted
            try:
                page.click('button:text("Accept")', timeout=3000)
                page.wait_for_timeout(500)
            except:
                pass
            try:
                page.click('button:text("Accept All")', timeout=2000)
                page.wait_for_timeout(500)
            except:
                pass
            
            # Wait for JS to render job listings
            wait_ms = 6000 if platform in ('workday', 'pageup') else 4000
            page.wait_for_timeout(wait_ms)
            
            text = page.evaluate('() => document.body.innerText')
            
            # Also grab job links
            job_links = page.evaluate('''() => {
                return Array.from(document.querySelectorAll("a"))
                    .map(a => ({text: a.innerText.trim(), href: a.href}))
                    .filter(a => a.text.length > 5 && a.href.length > 10)
            }''')
            browser.close()
            
            # Extract jobs with location info
            job_tuples = extract_jobs_from_text(text, company_name, au_only=True)
            
            # Match to URLs
            job_urls = {}
            for link in job_links:
                lt = link['text'].lower()
                if any(k in lt for k in KEEP_ROLES):
                    job_urls[link['text'][:80]] = link['href']
            
            # Return (title, url, location)
            results = []
            for title, location in job_tuples:
                link_url = job_urls.get(title, url)
                results.append((title, link_url, location))
            
            return results
    
    except Exception as e:
        print(f"    Playwright error: {e}")
        return []

def serpapi_fallback(company_name):
    """Search for company jobs using Exa AI search (replaces SerpAPI)"""
    import requests as req_lib
    
    query = f'{company_name} project manager OR construction manager OR commercial manager Gold Coast jobs hiring 2026'
    
    try:
        from datetime import datetime, timedelta
        cutoff = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%dT00:00:00.000Z")
        resp = req_lib.post(
            "https://api.exa.ai/search",
            headers={"x-api-key": EXA_API_KEY, "Content-Type": "application/json"},
            json={"query": query, "numResults": 5, "startPublishedDate": cutoff},
            timeout=12
        )
        resp.raise_for_status()
        data = resp.json()
        
        jobs = []
        for result in data.get('results', []):
            title = result.get('title', '')
            link = result.get('url', '')
            if any(s in link.lower() for s in ['salary', 'reviews', 'overview', '/companies/']):
                continue
            clean = re.sub(r'\s*[-|]\s*' + re.escape(company_name) + r'.*$', '', title, flags=re.IGNORECASE).strip()
            clean = re.sub(r'\s+(?:at|@)\s+.*$', '', clean, flags=re.IGNORECASE).strip()
            if is_relevant_role(clean):
                if company_name.split()[0].lower() in title.lower():
                    jobs.append((clean, link))
        return jobs
    except Exception as e:
        print(f"  Exa search error: {e}")
        return []

def insert_lead(company_name, company_id, title, url, location='Gold Coast'):
    """Insert lead if not duplicate"""
    conn = db_connect()
    cur = conn.cursor()
    
    intel_type = f"Direct Careers ({title})"
    # Strict dedup: if this company already has ANY Direct Careers lead, skip
    cur.execute('''SELECT id FROM leads 
                   WHERE company = ? AND intel_type LIKE 'Direct Careers%'
                   LIMIT 1''',
                (company_name,))
    
    if cur.fetchone():
        conn.close()
        return False
    
    sector = detect_sector(title + ' ' + company_name)
    
    cur.execute('''INSERT INTO leads (date, company, company_id, intel_type, source, 
                   what_it_means, action_trigger, created_at, location, sector)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
               (today(), company_name, company_id, intel_type,
                "Company Website (Direct)",
                f"Actively hiring: {title} — found on company careers page",
                url, datetime.now().isoformat(), location, sector))
    conn.commit()
    conn.close()
    return True

def run_careers_scan():
    """Main scan — check all CRM companies"""
    print(f"\n{'='*60}")
    print(f"🏢 Direct Careers Scan — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*60}\n")
    
    conn = db_connect()
    cur = conn.cursor()
    cur.execute('SELECT id, name, website, location FROM companies WHERE website IS NOT NULL AND website != "" ORDER BY name')
    companies = cur.fetchall()
    conn.close()
    
    print(f"Scanning {len(companies)} companies...\n")
    
    total_new = 0
    serpapi_used = 0
    
    for company in companies:
        company_id = company['id']
        company_name = company['name']
        location = company['location'] or 'Gold Coast'
        
        # Get careers URL and platform
        careers_info = COMPANY_CAREERS.get(company_name)
        
        if careers_info:
            careers_url, platform = careers_info
            print(f"  🔍 {company_name} ({platform})")
            job_results = scrape_with_playwright(careers_url, platform, company_name)
        else:
            # Use SerpAPI as fallback (costs a search credit)
            if serpapi_used < 50:  # Cap SerpAPI usage
                serp_results = serpapi_fallback(company_name)
                job_results = [(title, url, 'Gold Coast') for title, url in serp_results]
                serpapi_used += 1
            else:
                continue
        
        if not job_results:
            continue
        
        new_count = 0
        for result in job_results:
            title, job_url, job_location = result if len(result) == 3 else (*result, location)
            if insert_lead(company_name, company_id, title, job_url, job_location):
                total_new += 1
                new_count += 1
                print(f"    ✅ {title} [{job_location}]")
        
        if new_count == 0 and job_results:
            print(f"    ♻️  {len(job_results)} roles already in CRM")
        
        time.sleep(1)
    
    print(f"\n{'='*60}")
    print(f"✅ Scan complete — {total_new} new leads | {serpapi_used} Exa searches used")
    print(f"{'='*60}\n")
    return total_new

if __name__ == "__main__":
    run_careers_scan()
