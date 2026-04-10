#!/usr/bin/env python3
"""
Daily Market Intelligence Scanner
Runs at 6am AEST — gathers leads from:
1. Adzuna job adverts (last 24h) → enriched leads
2. Google News RSS (Gold Coast + Brisbane construction) → project intel leads

Deposits everything into the leads table with source + link.
"""
import sqlite3
import urllib.request
import urllib.parse
import json
import xml.etree.ElementTree as ET
import re
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).parent / "crm.db"

# ─── Helpers ───────────────────────────────────────────────────────────────────

def db_connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def today():
    return datetime.now().strftime('%Y-%m-%d')

def run_adzuna_scan():
    """Run job board scanner for last 24 hours, then enrich to leads"""
    print("\n📋 STEP 1: Adzuna Job Adverts (last 24h)")
    import subprocess
    result = subprocess.run(
        ['python3', str(Path(__file__).parent / 'job-board-scanner.py')],
        capture_output=True, text=True, timeout=180
    )
    print(result.stdout[-500:] if result.stdout else "(no output)")
    if result.returncode != 0:
        print("Scanner error:", result.stderr[-200:])
        return 0

    # Now run enrichment for 24h window
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    
    conn = db_connect()
    cur = conn.cursor()
    
    # Gold Coast + Brisbane, last 24h with URLs
    cur.execute('''SELECT id, title, created_at, location, content, url 
                   FROM job_adverts 
                   WHERE (location LIKE '%Gold Coast%' OR location LIKE '%Brisbane%' OR location LIKE '%Queensland%')
                   AND url IS NOT NULL AND url != '' AND url != 'None'
                   AND datetime(created_at) > datetime('now', '-24 hours')
                   ORDER BY created_at DESC''')
    adverts = cur.fetchall()
    conn.close()
    
    print(f"  Found {len(adverts)} new adverts in last 24h")
    
    # Import enrichment functions from advert-to-leads-v2
    import importlib.util
    spec = importlib.util.spec_from_file_location("advert_enricher", 
           str(Path(__file__).parent / "advert-to-leads-v2.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    created = 0
    for advert in adverts:
        title = advert['title']
        location_raw = advert['location'] or ''
        content = advert['content'] or ''
        
        # Agency detection
        AGENCY_KEYWORDS = ['recruit', 'staffing', 'search', 'talent', 'resourcing', '360', 'frontline',
                           'hays', 'randstad', 'michael page', 'people2people', 'manpower', 'hudson',
                           'sharp & carter', 'sharp and carter', 'people group', 'cv services', 
                           'cv2me', 'awx', 'horner', 'veritas', 'fuse recruitment']
        NON_CONSTRUCTION = ['westpac', 'anz', 'nab', 'cba', 'bank', 'hotel', 'hospitality', 'cafe',
                            'accor', 'hyatt', 'sofitel', 'university', 'griffith', 'retail', 'bunnings',
                            'flight centre', 'travel', 'tourism', 'airline', 'retirement', 'superannuation',
                            'insurance', 'aged care', 'aged-care', 'childcare', 'child care',
                            'fusion5', 'endeavour group', 'aequalis',
                            'fitness', 'lifestyle group', 'gym', 'health club', 
                            'origin energy', 'consolidated power', 'renewables', 'energy group',
                            'solar', 'wind farm', 'power projects',
                            'cv2me', 'people group', 'awx']
        # Senior $150k+ roles only — no estimators, no juniors
        KEEP_ROLES = ['project manager', 'construction manager', 'commercial manager',
                      'quantity surveyor', 'project director', 'contracts manager', 'contract manager',
                      'senior project', 'general manager', 'operations manager', 'regional manager',
                      'program manager', 'programme manager', 'construction director']
        EXCLUDE_ROLES = ['business development', 'civil designer', 'water resources', 'graduate', 
                         'cadet', 'coordinator', 'administrator', 'sales manager', 'account manager',
                         'estimator', 'site manager', 'foreman', 'supervisor', 'superintendent']
        
        def detect_sector(title, content):
            t = (title + ' ' + content).lower()
            if any(x in t for x in ['civil infra', 'road', 'bridge', 'rail', 'pipeline', 'water main', 'sewer', 'earthworks', 'civil contractor']):
                return 'Civil Infrastructure'
            if any(x in t for x in ['government', 'dept', 'department', 'council', 'state', 'federal', 'tmr', 'qld gov']):
                return 'Government'
            if any(x in t for x in ['residential', 'apartment', 'townhouse', 'house', 'dwelling', 'villa', 'estate']):
                return 'Residential'
            if any(x in t for x in ['mixed use', 'mixed-use', 'retail podium', 'hotel tower']):
                return 'Mixed-Use'
            if any(x in t for x in ['industrial', 'warehouse', 'logistics', 'distribution centre', 'factory', 'manufacturing']):
                return 'Industrial'
            if any(x in t for x in ['commercial', 'office', 'data centre', 'fitout', 'retail']):
                return 'Commercial'
            return 'Construction'
        
        title_lower = title.lower()
        if not any(r in title_lower for r in KEEP_ROLES):
            continue
        if any(r in title_lower for r in EXCLUDE_ROLES):
            continue
        
        # Extract company from content
        company_match = re.search(r'(?:DIRECT EMPLOYER|VIA AGENCY)\s+—\s+(.+?)(?:\n|$)', content.split('\n')[0])
        if not company_match:
            continue
        
        raw_company = company_match.group(1).strip()
        
        if any(kw in raw_company.lower() for kw in NON_CONSTRUCTION):
            continue
        if any(kw in raw_company.lower() for kw in AGENCY_KEYWORDS):
            continue
        
        # Extract suburb
        suburbs = ["Surfers Paradise", "Broadbeach", "Mermaid Beach", "Carrara", "Southport",
                   "Robina", "Varsity Lakes", "Coomera", "Miami", "Ormeau", "Gold Coast",
                   "Brisbane CBD", "Brisbane", "Ipswich", "Logan"]
        location = "Gold Coast"
        for s in suburbs:
            if s.lower() in location_raw.lower():
                location = s
                break
        
        # Extract role
        role = title
        for r in KEEP_ROLES:
            if r in title_lower:
                role = r.title()
                break
        
        what_it_means = f"Actively hiring: {role} in {location}"
        
        conn = db_connect()
        cur = conn.cursor()
        try:
            # Dedup: skip if same company + role already exists in last 7 days
            cur.execute('''SELECT id FROM leads 
                           WHERE company = ? AND intel_type = ?
                           AND datetime(created_at) > datetime('now', '-7 days')''',
                       (raw_company, f"Job Advert ({role})"))
            if cur.fetchone():
                conn.close()
                continue
            
            sector = detect_sector(title, content)
            cur.execute('''INSERT INTO leads (date, company, intel_type, source, what_it_means, 
                           action_trigger, created_at, job_advert_id, location, sector)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                       (today(), raw_company, f"Job Advert ({role})", "Adzuna", what_it_means,
                        f"Call {raw_company} about {location} {role}", 
                        datetime.now().isoformat(), advert['id'], location, sector))
            conn.commit()
            created += 1
        except Exception as e:
            print(f"    Advert insert error: {e}")
        finally:
            conn.close()
    
    print(f"  Created {created} new job advert leads")
    return created


def run_news_scan():
    """Scan Google News RSS for Gold Coast & Brisbane construction project news"""
    print("\n📰 STEP 2: Construction News (Google News RSS)")
    
    SEARCH_QUERIES = [
        "Gold Coast construction project",
        "Gold Coast development approved",
        "Brisbane construction awarded",
        "SEQ infrastructure project",
        "Queensland builder awarded contract",
    ]
    
    # Keywords to extract company names
    BUILDER_KEYWORDS = ['by', 'developer', 'builder', 'group', 'constructions', 'developments', 
                        'properties', 'appointed', 'awarded', 'commences', 'breaks ground',
                        'completes', 'launches', 'unveils']
    
    # Skip these irrelevant news topics
    SKIP_KEYWORDS = ['trump', 'politics', 'murder', 'crime', 'police', 'accident', 'death',
                     'weather', 'flood', 'health care', 'hospital patient', 'school',
                     'election', 'council meeting', 'rates', 'parking']
    
    articles = []
    seen_urls = set()
    seen_topics = set()  # Deduplicate by key words to avoid 15x same story
    
    def topic_key(title):
        """Extract a short topic fingerprint to detect duplicate stories"""
        import re
        t = title.lower()
        # Extract 3-4 key nouns/proper nouns
        words = re.findall(r'\b[a-z]{4,}\b', t)
        # Filter common words
        stop = {'with', 'from', 'that', 'this', 'have', 'been', 'will', 'more', 'than',
                'gold', 'coast', 'brisbane', 'queensland', 'australia', 'project', 'construction'}
        keywords = [w for w in words if w not in stop][:3]
        return ' '.join(sorted(keywords))
    
    for query in SEARCH_QUERIES:
        try:
            encoded = urllib.parse.quote(query)
            url = f"https://news.google.com/rss/search?q={encoded}&hl=en-AU&gl=AU&ceid=AU:en"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=15) as response:
                xml_data = response.read().decode('utf-8')
            
            root = ET.fromstring(xml_data)
            channel = root.find('channel')
            if not channel:
                continue
            
            for item in channel.findall('item'):
                title_el = item.find('title')
                link_el = item.find('link')
                pub_el = item.find('pubDate')
                
                if title_el is None or link_el is None:
                    continue
                
                title = title_el.text or ''
                link = link_el.text or ''
                pub_date = pub_el.text if pub_el is not None else ''
                
                if link in seen_urls:
                    continue
                seen_urls.add(link)
                
                # Deduplicate by topic (same story from multiple outlets)
                tk = topic_key(title)
                if tk in seen_topics:
                    continue
                seen_topics.add(tk)
                
                # Skip irrelevant articles
                title_lower = title.lower()
                if any(skip in title_lower for skip in SKIP_KEYWORDS):
                    continue
                
                # Only keep construction/development relevant articles
                KEEP_NEWS = ['construction', 'develop', 'build', 'project', 'tower', 'apartment',
                             'infrastructure', 'rail', 'contract', 'awarded', 'commences', 
                             'approved', 'announces', 'begins', 'tops out', 'completes']
                if not any(k in title_lower for k in KEEP_NEWS):
                    continue
                
                articles.append({
                    'title': title,
                    'url': link,
                    'pub_date': pub_date,
                    'query': query
                })
        
        except Exception as e:
            print(f"  Error fetching '{query}': {e}")
    
    print(f"  Found {len(articles)} relevant news articles")
    
    # Insert as leads with source = Google News
    created = 0
    # Prioritise actionable articles (contract awards, construction starts, major projects)
    ACTION_SIGNALS = ['awarded', 'commences', 'begins', 'breaks ground', 'approved', 
                      'appoints', 'wins contract', 'tops out', 'completes', 'launches',
                      'unveils', 'fast-tracks', 'milestone']
    articles.sort(key=lambda a: any(s in a['title'].lower() for s in ACTION_SIGNALS), reverse=True)
    
    for article in articles[:10]:  # cap at 10 per day to avoid noise
        title = article['title']
        url = article['url']
        
        # Try to extract location
        location = "Gold Coast"
        if "brisbane" in title.lower():
            location = "Brisbane"
        elif "gold coast" in title.lower():
            location = "Gold Coast"
        elif "logan" in title.lower():
            location = "Logan"
        elif "ipswich" in title.lower():
            location = "Ipswich"
        
        # Clean up title (remove " - Source Name" suffix)
        clean_title = re.sub(r'\s*-\s*[^-]+$', '', title).strip()
        
        # Extract company hint from title
        company = "SEQ Market Intel"
        
        # Common patterns: "Company does X" or "X by Company"
        company_match = re.search(r'^([A-Z][A-Za-z\s&\']+(?:Group|Corp|Property|Construction|Contractors|Developments|Holdings|Equity|Projects|Builders|Developments))', clean_title)
        if company_match:
            company = company_match.group(1).strip()
        
        conn = db_connect()
        cur = conn.cursor()
        try:
            # Check if we already have this article (by title)
            cur.execute('SELECT id FROM leads WHERE what_it_means = ?', (clean_title,))
            if cur.fetchone():
                conn.close()
                continue
            
            # Detect sector from article title
            tl = clean_title.lower()
            if any(x in tl for x in ['rail', 'road', 'bridge', 'infrastructure', 'pipeline', 'tunnel', 'highway', 'motorway', 'faster rail']):
                news_sector = 'Civil Infrastructure'
            elif any(x in tl for x in ['apartment', 'tower', 'residential', 'townhouse', 'units', 'luxury', 'penthouse']):
                news_sector = 'Residential'
            elif any(x in tl for x in ['mixed use', 'mixed-use', 'precinct', 'masterplan']):
                news_sector = 'Mixed-Use'
            elif any(x in tl for x in ['industrial', 'warehouse', 'logistics']):
                news_sector = 'Industrial'
            elif any(x in tl for x in ['commercial', 'office', 'fitout']):
                news_sector = 'Commercial'
            elif any(x in tl for x in ['government', 'council', 'hospital', 'school']):
                news_sector = 'Government'
            else:
                news_sector = 'Construction'
            
            cur.execute('''INSERT INTO leads (date, company, intel_type, source, what_it_means,
                           action_trigger, created_at, location, sector)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                       (today(), company, "Project Intel", "Google News", clean_title,
                        url, datetime.now().isoformat(), location, news_sector))
            conn.commit()
            created += 1
        except Exception as e:
            print(f"    News insert error: {e}")
        finally:
            conn.close()
    
    print(f"  Created {created} new project intel leads")
    return created


def main():
    print(f"\n{'='*60}")
    print(f"🦄 Daily Intel Scanner — {datetime.now().strftime('%Y-%m-%d %H:%M AEST')}")
    print(f"{'='*60}")
    
    job_leads = run_adzuna_scan()
    news_leads = run_news_scan()
    careers_leads = run_careers_scan_integrated()
    
    total = job_leads + news_leads + careers_leads
    
    print(f"\n{'='*60}")
    print(f"✅ Done: {total} new leads added")
    print(f"   Job adverts: {job_leads}")
    print(f"   News intel:  {news_leads}")
    print(f"   Careers:     {careers_leads}")
    print(f"{'='*60}\n")
    
    return total


def run_careers_scan_integrated():
    """Run careers scan as part of daily intel"""
    print("\n🏢 STEP 3: Company Careers Pages (Seek/LinkedIn direct)")
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("careers", 
               str(Path(__file__).parent / "careers-scraper.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.run_careers_scan()
    except Exception as e:
        print(f"  Careers scan error: {e}")
        return 0

if __name__ == "__main__":
    main()
