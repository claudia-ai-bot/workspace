#!/usr/bin/env python3
"""
SEQ Lead Intelligence Tool
Unified lead research + CRM tool for construction recruitment.

Usage:
    python3 lead-intelligence.py                     # Show strategic brief
    python3 lead-intelligence.py --brief             # Same as above
    python3 lead-intelligence.py --update-crm        # Update CRM with brief
    python3 lead-intelligence.py "Company Name"      # Research & add single company
    python3 lead-intelligence.py --list              # List companies needing research
    python3 lead-intelligence.py --enrich <id>       # Enrich company with web research
    python3 lead-intelligence.py --enrich-all        # Enrich all companies needing research
    python3 lead-intelligence.py --seek-scan         # Scan Seek.com.au for construction jobs
    python3 lead-intelligence.py --stale             # Show stale contacts & gaps
    python3 lead-intelligence.py --projects          # Show project timeline/phases
    python3 lead-intelligence.py --set-phase <id> <phase>  # Set project phase
"""

import json
import os
import re
import sqlite3
import subprocess
import sys
from datetime import datetime, timedelta
from urllib.parse import quote, quote_plus
from html.parser import HTMLParser

DB_PATH = '/home/chris/.openclaw/workspace/seq-crm/crm.db'

# ─── Strategic targets ───────────────────────────────────────────────────────

TARGET_COMPANIES = [
    # Tier 1 - Head contractors (major projects)
    {"name": "Multiplex", "project": "Coomera Hospital", "value": "$1.1B", "tier": "Tier 1", "type": "Head Contractor"},
    {"name": "John Holland", "project": "Light Rail Stage 3", "value": "$1.2B", "tier": "Tier 1", "type": "Head Contractor"},
    {"name": "Hutchinson Builders", "project": "Royale, Lagoon, Sea Glass", "value": "$500M+", "tier": "Tier 1", "type": "Head Contractor"},
    {"name": "Icon Co", "project": "Gold Coast residential", "value": "$150M", "tier": "Tier 1", "type": "Head Contractor"},
    {"name": "CPB Contractors", "project": "Faster Rail Alliance", "value": "$5.75B", "tier": "Tier 1", "type": "Head Contractor"},
    {"name": "Fulton Hogan", "project": "Coomera Connector", "value": "$3.4B", "tier": "Tier 1", "type": "Head Contractor"},
    {"name": "ADCO Constructions", "project": "Gold Coast active", "value": "TBC", "tier": "Tier 1", "type": "Head Contractor"},

    # Tier 2 - Head contractors (smaller/fewer projects)
    {"name": "SIERA Group", "project": "Tapestry, Exhale", "value": "$80M+", "tier": "Tier 2", "type": "Head Contractor"},
    {"name": "Mosaic Property Group", "project": "Sophia + 3 others", "value": "$500M+", "tier": "Tier 2", "type": "Developer"},
    {"name": "Seymour Whyte", "project": "Coomera Connector South", "value": "$410M", "tier": "Tier 2", "type": "Head Contractor"},
    {"name": "McNab", "project": "Awaken Residences", "value": "TBC", "tier": "Tier 2", "type": "Head Contractor"},
    {"name": "Mayd Group", "project": "Burleigh 17-storey", "value": "TBC", "tier": "Tier 2", "type": "Head Contractor"},

    # Subcontractors
    {"name": "A.G. Coombs", "project": "Mechanical services (HVAC)", "value": "TBC", "tier": "Tier 2", "type": "Subcontractor - Mechanical"},
    {"name": "Stowe Australia", "project": "Electrical services", "value": "TBC", "tier": "Tier 2", "type": "Subcontractor - Electrical"},
    {"name": "Fredon", "project": "Electrical & comms services", "value": "TBC", "tier": "Tier 2", "type": "Subcontractor - Electrical/Comms"},
    {"name": "Cardno/Stantec", "project": "Engineering consultancy", "value": "TBC", "tier": "Tier 2", "type": "Engineering Consultancy"},
    {"name": "Aurecon", "project": "Engineering consultancy", "value": "TBC", "tier": "Tier 2", "type": "Engineering Consultancy"},
]

# Known websites for enrichment
COMPANY_WEBSITES = {
    "Multiplex": "https://www.multiplex.global",
    "John Holland": "https://www.johnholland.com.au",
    "Hutchinson Builders": "https://www.hutchinsonbuilders.com.au",
    "Icon Co": "https://www.icon.co",
    "CPB Contractors": "https://www.cpbcon.com.au",
    "Fulton Hogan": "https://www.fultonhogan.com.au",
    "ADCO Constructions": "https://www.adcoconstructions.com.au",
    "SIERA Group": "https://www.sieragroup.com.au",
    "Mosaic Property Group": "https://www.mosaicproperty.com.au",
    "Seymour Whyte": "https://www.seymourwhyte.com.au",
    "McNab": "https://www.mcnab.com.au",
    "Mayd Group": "https://www.mayd.com.au",
    "A.G. Coombs": "https://www.agcoombs.com.au",
    "Stowe Australia": "https://www.stoweaustralia.com.au",
    "Fredon": "https://www.fredon.com.au",
    "Cardno/Stantec": "https://www.stantec.com",
    "Aurecon": "https://www.aurecongroup.com",
}

KEY_ROLES = [
    "Project Manager", "Site Manager", "Construction Manager", "Contracts Manager",
    "Project Engineer", "Site Engineer", "Supervisor", "Foreman",
    "Quantity Surveyor", "Estimator", "Structural Engineer", "Civil Engineer",
    "Project Director", "Senior Project Manager",
]

DM_TEMPLATES = [
    {"title": "Managing Director", "role": "Leadership", "notes": "Final decision maker"},
    {"title": "Construction Manager", "role": "Construction", "notes": "Direct hiring authority"},
    {"title": "Project Manager", "role": "Operations", "notes": "Project-level decisions"},
    {"title": "People & Culture Manager", "role": "HR", "notes": "Handles recruitment"},
    {"title": "Senior Project Manager", "role": "Operations", "notes": "Large project oversight"},
]

# Project phases
PHASES = ["Design", "Tender", "Construction", "Completion"]
PHASE_EMOJI = {"Design": "📐", "Tender": "📋", "Construction": "🏗️", "Completion": "✅"}

# ─── Database helpers ─────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_schema():
    """Add new columns if they don't exist."""
    conn = get_db()
    c = conn.cursor()

    # Add phase & estimated_start to projects if missing
    cols = [r[1] for r in c.execute("PRAGMA table_info(projects)").fetchall()]
    if "phase" not in cols:
        c.execute("ALTER TABLE projects ADD COLUMN phase TEXT DEFAULT 'Construction'")
    if "estimated_start" not in cols:
        c.execute("ALTER TABLE projects ADD COLUMN estimated_start TEXT")
    if "estimated_end" not in cols:
        c.execute("ALTER TABLE projects ADD COLUMN estimated_end TEXT")
    if "value" not in cols:
        c.execute("ALTER TABLE projects ADD COLUMN value TEXT")
    if "staffing_needs" not in cols:
        c.execute("ALTER TABLE projects ADD COLUMN staffing_needs TEXT")

    # Add website & enriched_at to companies if missing
    cols = [r[1] for r in c.execute("PRAGMA table_info(companies)").fetchall()]
    if "website" not in cols:
        c.execute("ALTER TABLE companies ADD COLUMN website TEXT")
    if "enriched_at" not in cols:
        c.execute("ALTER TABLE companies ADD COLUMN enriched_at TEXT")
    if "company_type" not in cols:
        c.execute("ALTER TABLE companies ADD COLUMN company_type TEXT")

    conn.commit()
    conn.close()


# ─── Simple HTML text extractor ──────────────────────────────────────────────

class HTMLTextExtractor(HTMLParser):
    """Extract readable text from HTML, skip scripts/styles."""
    def __init__(self):
        super().__init__()
        self._text = []
        self._skip = False
        self._skip_tags = {'script', 'style', 'noscript', 'svg', 'path'}

    def handle_starttag(self, tag, attrs):
        if tag.lower() in self._skip_tags:
            self._skip = True

    def handle_endtag(self, tag):
        if tag.lower() in self._skip_tags:
            self._skip = False

    def handle_data(self, data):
        if not self._skip:
            text = data.strip()
            if text:
                self._text.append(text)

    def get_text(self):
        return ' '.join(self._text)


def extract_text_from_html(html):
    """Extract readable text from HTML string."""
    parser = HTMLTextExtractor()
    try:
        parser.feed(html)
    except Exception:
        pass
    return parser.get_text()


# ─── Web fetching ────────────────────────────────────────────────────────────

def fetch_url(url, timeout=15):
    """Fetch a URL using curl. Returns text content or None."""
    try:
        result = subprocess.run(
            ['curl', '-sL', '--max-time', str(timeout),
             '-H', 'User-Agent: Mozilla/5.0 (compatible; LeadIntel/1.0)',
             url],
            capture_output=True, text=True, timeout=timeout + 5
        )
        if result.returncode == 0 and result.stdout:
            return result.stdout
        return None
    except Exception as e:
        print(f"  ⚠️ Fetch error for {url}: {e}")
        return None


def extract_company_intel(html_text, company_name):
    """Extract useful intelligence from website text."""
    text = extract_text_from_html(html_text) if '<html' in html_text.lower()[:200] else html_text
    
    # Limit to first 15000 chars for processing
    text = text[:15000]
    intel = {
        "people": [],
        "projects": [],
        "services": [],
        "locations": [],
        "summary_lines": [],
    }

    text_lower = text.lower()

    # Extract mentions of QLD/GC locations
    qld_patterns = [
        r'Gold Coast', r'Brisbane', r'Sunshine Coast', r'Queensland',
        r'Surfers Paradise', r'Broadbeach', r'Southport', r'Robina',
        r'Coomera', r'Burleigh', r'Coolangatta', r'Palm Beach',
        r'Tweed', r'Logan', r'Ipswich', r'Toowoomba',
    ]
    for pat in qld_patterns:
        if re.search(pat, text, re.IGNORECASE):
            intel["locations"].append(pat)

    # Look for project-like references
    project_patterns = [
        r'(?:project|development|construction of|building|tower|hospital|rail|road|bridge)[\s:]+([A-Z][A-Za-z0-9\s\-,]{5,60})',
    ]
    for pat in project_patterns:
        matches = re.findall(pat, text)
        for m in matches[:5]:
            clean = m.strip().rstrip(',.')
            if len(clean) > 8 and clean not in intel["projects"]:
                intel["projects"].append(clean)

    # Look for people with titles
    title_patterns = [
        r'((?:CEO|CFO|COO|CTO|Managing Director|General Manager|Director|'
        r'Regional Director|State Manager|Project Director|Construction Manager|'
        r'Head of|National Manager|QLD Manager|Queensland Manager)[,\s\-:]+[A-Z][a-z]+\s[A-Z][a-z]+)',
    ]
    for pat in title_patterns:
        matches = re.findall(pat, text)
        for m in matches[:5]:
            if m not in intel["people"]:
                intel["people"].append(m.strip())

    # Reverse pattern: Name, Title
    name_title = re.findall(
        r'([A-Z][a-z]+\s[A-Z][a-z]+)\s*[-–,]\s*'
        r'((?:CEO|CFO|Managing Director|Director|General Manager|'
        r'Project Director|Construction Manager|Regional Director|'
        r'State Manager|Head of\s\w+))',
        text
    )
    for name, title in name_title[:5]:
        entry = f"{title}: {name}"
        if entry not in intel["people"]:
            intel["people"].append(entry)

    # Look for services
    service_keywords = [
        "mechanical", "electrical", "HVAC", "plumbing", "fire protection",
        "civil", "structural", "geotechnical", "environmental",
        "project management", "design", "engineering", "fit-out",
        "residential", "commercial", "industrial", "infrastructure",
    ]
    for kw in service_keywords:
        if kw.lower() in text_lower:
            intel["services"].append(kw)

    # Grab first meaningful paragraph as summary
    paragraphs = [p.strip() for p in text.split('\n') if len(p.strip()) > 50]
    for p in paragraphs[:3]:
        if company_name.split()[0].lower() in p.lower():
            intel["summary_lines"].append(p[:200])
            break

    return intel


# ─── Core functions ───────────────────────────────────────────────────────────

def generate_strategic_brief():
    """Show strategic targeting brief."""
    print("=" * 60)
    print("🎯 SEQ CONSTRUCTION LEAD BRIEF")
    print("=" * 60)

    # Group by type
    head_t1 = [c for c in TARGET_COMPANIES if c["tier"] == "Tier 1" and c["type"] == "Head Contractor"]
    head_t2 = [c for c in TARGET_COMPANIES if c["tier"] == "Tier 2" and c["type"] in ("Head Contractor", "Developer")]
    subs = [c for c in TARGET_COMPANIES if "Subcontractor" in c.get("type", "") or "Consultancy" in c.get("type", "")]

    print("\n📋 TIER 1 - HEAD CONTRACTORS:\n")
    for i, co in enumerate(head_t1, 1):
        print(f"  {i}. {co['name']}")
        print(f"     📍 {co['project']}  |  💰 {co['value']}")

    print(f"\n📋 TIER 2 - HEAD CONTRACTORS & DEVELOPERS:\n")
    for i, co in enumerate(head_t2, 1):
        print(f"  {i}. {co['name']} ({co['type']})")
        print(f"     📍 {co['project']}  |  💰 {co['value']}")

    print(f"\n🔧 SUBCONTRACTORS & CONSULTANCIES:\n")
    for co in subs:
        print(f"  • {co['name']} — {co['type']}")
        print(f"    {co['project']}")

    print("\n🎯 KEY ROLES TO PLACE:")
    for role in KEY_ROLES[:8]:
        print(f"   • {role}")
    print()


def add_company_to_crm(name, sector="Construction", location="Gold Coast",
                       active_projects="", upcoming_projects="", notes="",
                       tier="Tier 2", website="", company_type=""):
    """Add/update a company in the CRM."""
    ensure_schema()
    conn = get_db()
    c = conn.cursor()
    now = datetime.now().isoformat()

    c.execute('SELECT id, notes FROM companies WHERE name = ?', (name,))
    existing = c.fetchone()

    if existing:
        company_id = existing['id']
        existing_notes = existing['notes'] or ""
        new_notes = f"{existing_notes}\n\n{notes}" if existing_notes and notes else (notes or existing_notes)
        updates = {
            'tier': tier, 'sector': sector, 'location': location,
            'active_projects': active_projects, 'upcoming_projects': upcoming_projects,
            'notes': new_notes, 'updated_at': now,
        }
        if website:
            updates['website'] = website
        if company_type:
            updates['company_type'] = company_type

        set_clause = ', '.join(f'{k}=?' for k in updates)
        c.execute(f'UPDATE companies SET {set_clause} WHERE id=?',
                  list(updates.values()) + [company_id])
        print(f"  ✅ Updated: {name}")
    else:
        c.execute('''
            INSERT INTO companies (name, tier, sector, location, active_projects, upcoming_projects,
                                   competitors, notes, website, company_type, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, '', ?, ?, ?, ?, ?)
        ''', (name, tier, sector, location, active_projects, upcoming_projects,
              notes, website, company_type, now, now))
        company_id = c.lastrowid
        print(f"  ✅ Added: {name}")

    conn.commit()
    conn.close()
    return company_id


def add_decision_maker(company_id, name, title, role, notes=""):
    """Add a decision maker to a company."""
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        INSERT INTO decision_makers (company_id, name, title, role, phone, email, linkedin,
                                     hiring_signals, relationship_score, last_contact, next_action, notes)
        VALUES (?, ?, ?, ?, NULL, NULL, NULL, NULL, 1, NULL, 'Research contact', ?)
    ''', (company_id, name, title, role, notes))
    dm_id = c.lastrowid
    conn.commit()
    conn.close()
    return dm_id


def research_and_add_company(company_name, sector="Construction", location="Gold Coast", tier="Tier 2"):
    """Research a company and add to CRM with decision maker slots."""
    print(f"\n{'='*50}")
    print(f"🔍 RESEARCHING: {company_name}")
    print(f"{'='*50}")

    website = COMPANY_WEBSITES.get(company_name, "")
    company_type = ""
    for tc in TARGET_COMPANIES:
        if tc["name"] == company_name:
            company_type = tc.get("type", "")
            break

    company_id = add_company_to_crm(
        name=company_name, sector=sector, location=location, tier=tier,
        website=website, company_type=company_type,
        notes=f"Added via lead-intelligence.py - {datetime.now().strftime('%Y-%m-%d')}"
    )

    print(f"  Adding decision maker slots...")
    for dm in DM_TEMPLATES:
        add_decision_maker(company_id, f"TBC - {dm['title']}", dm['title'], dm['role'], dm['notes'])

    print(f"\n✅ {company_name} added with {len(DM_TEMPLATES)} decision maker slots")
    print(f"   Next step: Run --enrich {company_id} to find actual contacts")
    return company_id


def update_crm_from_brief():
    """Update CRM with strategic brief companies (including subcontractors)."""
    ensure_schema()
    print("\n📥 Importing strategic brief to CRM...\n")

    for co in TARGET_COMPANIES:
        name = co["name"]
        website = COMPANY_WEBSITES.get(name, "")
        company_id = add_company_to_crm(
            name=name, sector="Construction", location="Gold Coast/SEQ",
            active_projects=co["project"], tier=co["tier"],
            website=website, company_type=co.get("type", ""),
            notes=f"🎯 {co['project']} ({co['value']})"
        )

    print(f"\n✅ {len(TARGET_COMPANIES)} companies imported to CRM!")


def list_companies_needing_research():
    """List companies that need decision maker research."""
    ensure_schema()
    conn = get_db()
    c = conn.cursor()

    # Companies with no DMs or TBC DMs
    c.execute('''
        SELECT c.id, c.name, c.tier, c.company_type, c.enriched_at,
               COUNT(d.id) as dm_count,
               SUM(CASE WHEN d.name LIKE 'TBC%' THEN 1 ELSE 0 END) as tbc_count
        FROM companies c
        LEFT JOIN decision_makers d ON c.id = d.company_id
        GROUP BY c.id
        ORDER BY 
            CASE WHEN c.tier LIKE 'Tier 1%' OR c.tier = 'T1' THEN 0 ELSE 1 END,
            c.updated_at DESC
        LIMIT 25
    ''')

    rows = c.fetchall()
    print("\n🏢 COMPANIES IN CRM:")
    print("-" * 70)
    print(f"{'ID':>4}  {'Company':<30} {'Tier':<8} {'DMs':>4} {'TBC':>4}  Status")
    print("-" * 70)

    for row in rows:
        dm_count = row['dm_count'] or 0
        tbc_count = row['tbc_count'] or 0
        enriched = "✅" if row['enriched_at'] else "❌"

        if dm_count == 0:
            status = f"❌ No DMs  Enriched: {enriched}"
        elif tbc_count > 0:
            status = f"⚠️ {tbc_count} TBC  Enriched: {enriched}"
        else:
            status = f"✅ Done    Enriched: {enriched}"

        print(f"[{row['id']:>3}] {row['name']:<30} {(row['tier'] or '?'):<8} {dm_count:>4} {tbc_count:>4}  {status}")

    conn.close()


# ─── ENRICH (the real deal) ──────────────────────────────────────────────────

def enrich_company(company_id):
    """Enrich a company by fetching its website and extracting intelligence."""
    ensure_schema()
    conn = get_db()
    c = conn.cursor()

    c.execute('SELECT id, name, website, notes FROM companies WHERE id = ?', (company_id,))
    row = c.fetchone()
    if not row:
        print(f"❌ Company ID {company_id} not found")
        conn.close()
        return

    company_name = row['name']
    website = row['website'] or COMPANY_WEBSITES.get(company_name, "")
    existing_notes = row['notes'] or ""

    print(f"\n🔍 Enriching: {company_name}")
    print(f"   Website: {website or '(none known)'}")

    all_intel = {"people": [], "projects": [], "services": [], "locations": [], "summary_lines": []}

    # 1. Fetch company website
    if website:
        print(f"   📡 Fetching website...")
        html = fetch_url(website)
        if html:
            intel = extract_company_intel(html, company_name)
            for k in all_intel:
                all_intel[k].extend(intel[k])
            print(f"      Found: {len(intel['people'])} people, {len(intel['projects'])} projects, {len(intel['services'])} services")

            # Try /about and /projects pages
            for subpage in ['/about', '/about-us', '/projects', '/our-projects', '/careers']:
                sub_url = website.rstrip('/') + subpage
                print(f"   📡 Trying {subpage}...")
                sub_html = fetch_url(sub_url, timeout=10)
                if sub_html and len(sub_html) > 500:
                    sub_intel = extract_company_intel(sub_html, company_name)
                    for k in all_intel:
                        all_intel[k].extend(sub_intel[k])
        else:
            print(f"      ⚠️ Could not fetch website")

    # 2. Google News search for recent activity
    search_query = f"{company_name} construction Gold Coast Queensland 2026"
    search_url = f"https://www.google.com/search?q={quote_plus(search_query)}&tbm=nws"
    print(f"   📡 Searching news...")
    news_html = fetch_url(f"https://html.duckduckgo.com/html/?q={quote_plus(search_query)}", timeout=10)
    if news_html:
        news_intel = extract_company_intel(news_html, company_name)
        all_intel["projects"].extend(news_intel["projects"])
        all_intel["summary_lines"].extend(news_intel["summary_lines"])

    # Deduplicate
    for k in all_intel:
        all_intel[k] = list(dict.fromkeys(all_intel[k]))

    # Build enrichment notes
    enrich_lines = [f"\n--- ENRICHMENT {datetime.now().strftime('%Y-%m-%d')} ---"]
    if all_intel["summary_lines"]:
        enrich_lines.append(f"• Summary: {all_intel['summary_lines'][0]}")
    if all_intel["services"]:
        enrich_lines.append(f"• Services: {', '.join(all_intel['services'][:8])}")
    if all_intel["locations"]:
        enrich_lines.append(f"• QLD Locations: {', '.join(all_intel['locations'][:6])}")
    if all_intel["projects"]:
        for p in all_intel["projects"][:5]:
            enrich_lines.append(f"• Project: {p}")
    if all_intel["people"]:
        for p in all_intel["people"][:5]:
            enrich_lines.append(f"• Key Person: {p}")

    if len(enrich_lines) > 1:
        enrichment_text = '\n'.join(enrich_lines)
        new_notes = existing_notes + enrichment_text
        c.execute('UPDATE companies SET notes=?, enriched_at=?, updated_at=? WHERE id=?',
                  (new_notes, datetime.now().isoformat(), datetime.now().isoformat(), company_id))

        if website and not row['website']:
            c.execute('UPDATE companies SET website=? WHERE id=?', (website, company_id))

        conn.commit()
        print(f"\n   📝 Enrichment saved:")
        for line in enrich_lines[1:]:
            print(f"      {line}")
    else:
        # Still mark as enriched (attempted)
        c.execute('UPDATE companies SET enriched_at=?, updated_at=? WHERE id=?',
                  (datetime.now().isoformat(), datetime.now().isoformat(), company_id))
        conn.commit()
        print(f"\n   ⚠️ Limited intel found. Marked as enriched (attempted).")
        print(f"   💡 Tip: Add website manually, then re-enrich.")

    conn.close()
    print(f"\n✅ Enrichment complete for {company_name}")


def enrich_all():
    """Enrich all companies that haven't been enriched yet."""
    ensure_schema()
    conn = get_db()
    c = conn.cursor()

    c.execute('''
        SELECT id, name FROM companies
        WHERE enriched_at IS NULL
        ORDER BY
            CASE WHEN tier LIKE 'Tier 1%' OR tier = 'T1' THEN 0 ELSE 1 END,
            updated_at DESC
    ''')
    companies = c.fetchall()
    conn.close()

    if not companies:
        print("✅ All companies have been enriched!")
        return

    print(f"\n🔄 Enriching {len(companies)} companies...\n")
    for i, co in enumerate(companies, 1):
        print(f"\n[{i}/{len(companies)}] ", end="")
        enrich_company(co['id'])
        print()

    print(f"\n✅ Enrichment complete for {len(companies)} companies!")


# ─── SEEK SCAN ────────────────────────────────────────────────────────────────

def seek_scan():
    """Scan for construction jobs on the Gold Coast via Seek + DuckDuckGo fallback."""
    ensure_schema()

    search_terms = [
        "construction manager Gold Coast",
        "project manager construction Gold Coast",
        "site manager construction Gold Coast",
        "quantity surveyor Gold Coast",
        "project engineer construction Gold Coast",
    ]

    print("\n" + "=" * 70)
    print("🔍 CONSTRUCTION JOB SCAN - Gold Coast (Seek + Web)")
    print("=" * 70)

    # Get existing companies for matching
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT id, name FROM companies')
    crm_companies = {}
    for row in c.fetchall():
        crm_companies[row['name'].lower()] = row['id']
        # Also index first word for fuzzy matching
        first_word = row['name'].lower().split()[0]
        if len(first_word) > 3:
            crm_companies[first_word] = row['id']
    conn.close()

    all_jobs = []

    for search in search_terms:
        # Strategy 1: Try Seek directly with browser-like headers
        seek_url = f"https://www.seek.com.au/{search.replace(' ', '-')}-jobs"
        print(f"\n📡 Searching: {search}...")

        html = fetch_url(seek_url, timeout=15)
        jobs_found = 0

        if html and len(html) > 5000:
            # Try Seek's data attributes
            title_pattern = r'data-testid="job-card-title"[^>]*>([^<]+)<'
            company_pattern = r'data-testid="job-card-company"[^>]*>([^<]+)<'
            location_pattern = r'data-testid="job-card-location"[^>]*>([^<]+)<'

            titles = re.findall(title_pattern, html)
            companies_found = re.findall(company_pattern, html)
            locations = re.findall(location_pattern, html)

            # Fallback: look for role keywords in links
            if not titles:
                title_matches = re.findall(
                    r'<a[^>]+href="/job/[^"]*"[^>]*>([^<]*(?:Manager|Engineer|Supervisor|Estimator|Surveyor|Foreman|Director)[^<]*)</a>',
                    html, re.IGNORECASE
                )
                titles = title_matches[:10]

            for i, title in enumerate(titles[:10]):
                company = companies_found[i] if i < len(companies_found) else "Unknown"
                location = locations[i] if i < len(locations) else "Gold Coast"
                job = _make_job(title, company, location, crm_companies, search)
                if job and not any(j["title"] == job["title"] and j["company"] == job["company"] for j in all_jobs):
                    all_jobs.append(job)
                    jobs_found += 1

        # Strategy 2: DuckDuckGo search for Seek listings
        if jobs_found == 0:
            ddg_query = f"site:seek.com.au {search} 2026"
            ddg_url = f"https://html.duckduckgo.com/html/?q={quote_plus(ddg_query)}"
            ddg_html = fetch_url(ddg_url, timeout=10)

            if ddg_html:
                # Extract Seek job listings from DDG results
                # DDG result format: <a class="result__a" href="...">Title</a>
                result_links = re.findall(
                    r'class="result__a"[^>]*>([^<]+)</a>', ddg_html
                )
                result_snippets = re.findall(
                    r'class="result__snippet"[^>]*>(.*?)</a>', ddg_html, re.DOTALL
                )

                for i, link_text in enumerate(result_links[:8]):
                    snippet = result_snippets[i] if i < len(result_snippets) else ""
                    snippet_clean = re.sub(r'<[^>]+>', '', snippet).strip()

                    # Extract company from snippet or title
                    company = "Unknown"
                    # Common pattern: "Company Name - Gold Coast" in snippet
                    co_match = re.search(r'(?:at|with|for)\s+([A-Z][A-Za-z&\s]+?)(?:\s*[-–]|\s+in\s)', snippet_clean)
                    if co_match:
                        company = co_match.group(1).strip()
                    else:
                        # Try extracting from title "Role - Company"
                        parts = link_text.split(' - ')
                        if len(parts) >= 2:
                            company = parts[-1].strip()
                            if 'seek' in company.lower() or 'gold coast' in company.lower():
                                company = parts[1].strip() if len(parts) > 2 else "Unknown"

                    title = link_text.split(' - ')[0].strip() if ' - ' in link_text else link_text.strip()

                    # Only include construction-relevant results
                    relevance_words = ['manager', 'engineer', 'supervisor', 'estimator',
                                       'surveyor', 'foreman', 'director', 'construction',
                                       'project', 'site', 'contracts', 'quantity']
                    if any(w in title.lower() for w in relevance_words):
                        job = _make_job(title, company, "Gold Coast", crm_companies, search)
                        if job and not any(j["title"] == job["title"] and j["company"] == job["company"] for j in all_jobs):
                            all_jobs.append(job)
                            jobs_found += 1

        print(f"   Found {jobs_found} jobs")

    # Output report
    print(f"\n{'='*70}")
    print(f"📊 JOB SCAN RESULTS - {len(all_jobs)} jobs found")
    print(f"{'='*70}")

    if not all_jobs:
        print("\n⚠️ Limited results. Job sites may be blocking automated requests.")
        print("\n💡 MANUAL SCAN LINKS (open in browser):")
        for term in search_terms:
            url = f"https://www.seek.com.au/{term.replace(' ', '-')}-jobs"
            print(f"   {url}")
        print(f"\n   Then add companies: python3 lead-intelligence.py \"Company Name\"")
        return

    # Split into known vs new
    known = [j for j in all_jobs if j["in_crm"]]
    new = [j for j in all_jobs if not j["in_crm"]]

    if known:
        print(f"\n🟢 EXISTING CRM COMPANIES HIRING ({len(known)} jobs):")
        print("-" * 60)
        for j in known:
            print(f"  🏢 {j['company']} [CRM #{j['crm_id']}]")
            print(f"     📋 {j['title']}")
            print(f"     📍 {j['location']}")
            print()

    if new:
        print(f"\n🔴 NEW PROSPECTS - NOT IN CRM ({len(new)} jobs):")
        print("-" * 60)
        for j in new:
            print(f"  🆕 {j['company']}")
            print(f"     📋 {j['title']}")
            print(f"     📍 {j['location']}")
            print()

    # Summary
    unique_new_companies = list(set(j['company'] for j in new if j['company'] != 'Unknown'))
    if unique_new_companies:
        print(f"\n💡 NEW COMPANIES TO ADD:")
        for co in unique_new_companies[:10]:
            print(f'   python3 lead-intelligence.py "{co}"')

    print(f"\n📊 Summary: {len(known)} from CRM, {len(new)} new prospects")
    print(f"📅 Scan date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")


def _make_job(title, company, location, crm_companies, search):
    """Create a job dict and check CRM membership."""
    title = title.strip()
    company = company.strip()
    if not title or len(title) < 5:
        return None

    in_crm = False
    crm_id = None
    company_lower = company.lower()
    for crm_name, cid in crm_companies.items():
        if crm_name in company_lower or company_lower in crm_name:
            in_crm = True
            crm_id = cid
            break

    return {
        "title": title,
        "company": company,
        "location": location.strip() if location else "Gold Coast",
        "in_crm": in_crm,
        "crm_id": crm_id,
        "search": search,
    }


# ─── STALE CONTACTS ──────────────────────────────────────────────────────────

def show_stale():
    """Show stale contacts, TBC names, and companies with no DMs."""
    ensure_schema()
    conn = get_db()
    c = conn.cursor()
    today = datetime.now().date()

    print("\n" + "=" * 70)
    print("⏰ STALE CONTACTS & GAPS REPORT")
    print("=" * 70)

    # 1. Stale Tier 1 companies (no activity in 14+ days)
    print(f"\n🔴 TIER 1 - NO CONTACT IN 14+ DAYS:")
    print("-" * 60)
    c.execute('''
        SELECT c.id, c.name, c.active_projects,
               MAX(d.last_contact) as last_dm_contact,
               c.last_activity, c.updated_at
        FROM companies c
        LEFT JOIN decision_makers d ON c.id = d.company_id
        WHERE c.tier LIKE '%1%'
        GROUP BY c.id
        ORDER BY last_dm_contact ASC NULLS FIRST
    ''')
    tier1_stale = 0
    for row in c.fetchall():
        last = row['last_dm_contact'] or row['last_activity'] or row['updated_at']
        if last:
            try:
                last_date = datetime.fromisoformat(last.replace('Z', '')).date()
                days = (today - last_date).days
            except (ValueError, TypeError):
                days = 999
        else:
            days = 999

        if days >= 14:
            tier1_stale += 1
            days_str = f"{days}d ago" if days < 900 else "Never"
            print(f"  [{row['id']:>3}] {row['name']:<30} Last: {days_str}")
            if row['active_projects']:
                print(f"        📍 {row['active_projects'][:60]}")

    if tier1_stale == 0:
        print("  ✅ All Tier 1 companies contacted within 14 days!")

    # 2. Stale Tier 2 companies (no activity in 21+ days)
    print(f"\n🟡 TIER 2 - NO CONTACT IN 21+ DAYS:")
    print("-" * 60)
    c.execute('''
        SELECT c.id, c.name, c.active_projects,
               MAX(d.last_contact) as last_dm_contact,
               c.last_activity, c.updated_at
        FROM companies c
        LEFT JOIN decision_makers d ON c.id = d.company_id
        WHERE c.tier LIKE '%2%'
        GROUP BY c.id
        ORDER BY last_dm_contact ASC NULLS FIRST
    ''')
    tier2_stale = 0
    for row in c.fetchall():
        last = row['last_dm_contact'] or row['last_activity'] or row['updated_at']
        if last:
            try:
                last_date = datetime.fromisoformat(last.replace('Z', '')).date()
                days = (today - last_date).days
            except (ValueError, TypeError):
                days = 999
        else:
            days = 999

        if days >= 21:
            tier2_stale += 1
            days_str = f"{days}d ago" if days < 900 else "Never"
            print(f"  [{row['id']:>3}] {row['name']:<30} Last: {days_str}")

    if tier2_stale == 0:
        print("  ✅ All Tier 2 companies contacted within 21 days!")

    # 3. Decision makers with TBC names
    print(f"\n👤 DECISION MAKERS WITH TBC NAMES (need research):")
    print("-" * 60)
    c.execute('''
        SELECT d.id, d.name, d.title, c.name as company_name, c.id as company_id
        FROM decision_makers d
        JOIN companies c ON d.company_id = c.id
        WHERE d.name LIKE '%TBC%'
        ORDER BY c.tier, c.name
    ''')
    tbc_rows = c.fetchall()
    if tbc_rows:
        current_company = None
        for row in tbc_rows:
            if row['company_name'] != current_company:
                current_company = row['company_name']
                print(f"\n  🏢 {current_company} [#{row['company_id']}]:")
            print(f"     • {row['title']}: {row['name']}")
        print(f"\n  Total: {len(tbc_rows)} TBC contacts needing research")
    else:
        print("  ✅ No TBC decision makers!")

    # 4. Companies with NO decision makers at all
    print(f"\n🚫 COMPANIES WITH NO DECISION MAKERS:")
    print("-" * 60)
    c.execute('''
        SELECT c.id, c.name, c.tier, c.company_type
        FROM companies c
        LEFT JOIN decision_makers d ON c.id = d.company_id
        GROUP BY c.id
        HAVING COUNT(d.id) = 0
        ORDER BY
            CASE WHEN c.tier LIKE '%1%' THEN 0 ELSE 1 END,
            c.name
    ''')
    no_dm = c.fetchall()
    if no_dm:
        for row in no_dm:
            tier_str = row['tier'] or '?'
            type_str = f" ({row['company_type']})" if row['company_type'] else ""
            print(f"  [{row['id']:>3}] {row['name']:<35} {tier_str}{type_str}")
        print(f"\n  Total: {len(no_dm)} companies with zero DMs")
        print(f"  💡 Add DMs: python3 lead-intelligence.py \"Company Name\"")
    else:
        print("  ✅ All companies have decision makers!")

    # Summary
    print(f"\n{'='*70}")
    print(f"📊 SUMMARY:")
    print(f"   🔴 Tier 1 stale (14d+): {tier1_stale}")
    print(f"   🟡 Tier 2 stale (21d+): {tier2_stale}")
    print(f"   👤 TBC names:           {len(tbc_rows)}")
    print(f"   🚫 No DMs:             {len(no_dm)}")
    print(f"{'='*70}")

    conn.close()


# ─── PROJECT TIMELINE ────────────────────────────────────────────────────────

def show_projects():
    """Show project timeline with phases and staffing needs."""
    ensure_schema()
    conn = get_db()
    c = conn.cursor()

    print("\n" + "=" * 70)
    print("🏗️  PROJECT TIMELINE & STAFFING NEEDS")
    print("=" * 70)

    c.execute('''
        SELECT p.id, p.name, p.phase, p.status, p.estimated_start, p.estimated_end,
               p.value, p.staffing_needs, p.description,
               c.name as company_name, c.tier
        FROM projects p
        LEFT JOIN companies c ON p.company_id = c.id
        ORDER BY
            CASE p.phase
                WHEN 'Construction' THEN 0
                WHEN 'Tender' THEN 1
                WHEN 'Design' THEN 2
                WHEN 'Completion' THEN 3
                ELSE 4
            END,
            p.name
    ''')
    projects = c.fetchall()

    if not projects:
        print("\n  No projects in the database.")
        print("  Projects are tracked in the CRM web app or can be added here.")
        conn.close()
        _show_projects_from_companies(conn)
        return

    # Group by phase
    by_phase = {}
    for p in projects:
        phase = p['phase'] or 'Unknown'
        if phase not in by_phase:
            by_phase[phase] = []
        by_phase[phase].append(p)

    # Show each phase
    for phase in ["Construction", "Tender", "Design", "Completion", "Unknown"]:
        if phase not in by_phase:
            continue
        emoji = PHASE_EMOJI.get(phase, "❓")
        items = by_phase[phase]

        if phase == "Construction":
            header = f"{emoji} HIRING NOW — {phase.upper()} PHASE ({len(items)} projects)"
        elif phase == "Tender":
            header = f"{emoji} HIRING IN 1-3 MONTHS — {phase.upper()} PHASE ({len(items)} projects)"
        elif phase == "Design":
            header = f"{emoji} HIRING IN 3-6 MONTHS — {phase.upper()} PHASE ({len(items)} projects)"
        else:
            header = f"{emoji} {phase.upper()} ({len(items)} projects)"

        print(f"\n{header}")
        print("-" * 60)

        for p in items:
            company = p['company_name'] or "Unassigned"
            value = f" | 💰 {p['value']}" if p['value'] else ""
            timeline = ""
            if p['estimated_start'] or p['estimated_end']:
                start = p['estimated_start'] or '?'
                end = p['estimated_end'] or '?'
                timeline = f" | 📅 {start} → {end}"

            print(f"  [{p['id']:>3}] {p['name']}")
            print(f"        🏢 {company}{value}{timeline}")
            if p['staffing_needs']:
                print(f"        👷 Needs: {p['staffing_needs']}")

    conn.close()


def _show_projects_from_companies(conn_unused):
    """Fallback: show project info from company records."""
    conn = get_db()
    c = conn.cursor()

    print("\n📋 PROJECT INFO FROM COMPANY RECORDS:")
    print("-" * 60)

    c.execute('''
        SELECT id, name, tier, active_projects, upcoming_projects
        FROM companies
        WHERE active_projects != '' OR upcoming_projects != ''
        ORDER BY
            CASE WHEN tier LIKE '%1%' THEN 0 ELSE 1 END,
            name
    ''')
    rows = c.fetchall()
    for row in rows:
        print(f"\n  🏢 {row['name']} ({row['tier'] or '?'})")
        if row['active_projects']:
            print(f"     🏗️ Active: {row['active_projects']}")
        if row['upcoming_projects']:
            print(f"     📐 Upcoming: {row['upcoming_projects']}")

    conn.close()

    print(f"\n💡 Set project phases:")
    print(f"   python3 lead-intelligence.py --set-phase <project_id> Construction")
    print(f"   Phases: Design | Tender | Construction | Completion")


def set_project_phase(project_id, phase):
    """Set the phase for a project."""
    ensure_schema()
    if phase not in PHASES:
        print(f"❌ Invalid phase '{phase}'. Must be one of: {', '.join(PHASES)}")
        return

    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT name FROM projects WHERE id = ?', (project_id,))
    row = c.fetchone()
    if not row:
        print(f"❌ Project ID {project_id} not found")
        conn.close()
        return

    c.execute('UPDATE projects SET phase = ? WHERE id = ?', (phase, project_id))
    conn.commit()
    conn.close()

    emoji = PHASE_EMOJI.get(phase, "")
    print(f"✅ {row['name']} → {emoji} {phase}")


# ─── HELP ────────────────────────────────────────────────────────────────────

def show_usage():
    """Show usage instructions."""
    print("""
🎯 SEQ LEAD INTELLIGENCE TOOL
=============================

COMMANDS:
  python3 lead-intelligence.py                         Show this help
  python3 lead-intelligence.py --brief                 Show strategic brief

  COMPANY MANAGEMENT:
  python3 lead-intelligence.py "Company Name"          Research & add company
  python3 lead-intelligence.py --update-crm            Import all targets to CRM
  python3 lead-intelligence.py --list                  List companies & research gaps

  ENRICHMENT:
  python3 lead-intelligence.py --enrich <id>           Enrich company (web research)
  python3 lead-intelligence.py --enrich-all            Enrich all unenriched companies

  INTELLIGENCE:
  python3 lead-intelligence.py --seek-scan             Scan Seek.com.au for GC construction jobs
  python3 lead-intelligence.py --stale                 Show stale contacts & gaps

  PROJECTS:
  python3 lead-intelligence.py --projects              Show project timeline & phases
  python3 lead-intelligence.py --set-phase <id> <phase>  Set project phase
                                                       (Design|Tender|Construction|Completion)

EXAMPLES:
  # Morning routine
  python3 lead-intelligence.py --stale                 # Who needs attention?
  python3 lead-intelligence.py --seek-scan             # Who's hiring?

  # Add a new prospect
  python3 lead-intelligence.py "Hansen Yuncken"
  python3 lead-intelligence.py --enrich 42

  # Bulk enrich all companies
  python3 lead-intelligence.py --enrich-all

  # Check project pipeline
  python3 lead-intelligence.py --projects
""")


# ─── MAIN ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) == 1 or sys.argv[1] in ["--help", "-h"]:
        show_usage()
    elif sys.argv[1] == "--brief":
        generate_strategic_brief()
    elif sys.argv[1] == "--update-crm":
        update_crm_from_brief()
    elif sys.argv[1] == "--list":
        list_companies_needing_research()
    elif sys.argv[1] == "--enrich":
        if len(sys.argv) < 3:
            print("Usage: --enrich <company_id>")
        else:
            enrich_company(int(sys.argv[2]))
    elif sys.argv[1] == "--enrich-all":
        enrich_all()
    elif sys.argv[1] == "--seek-scan":
        seek_scan()
    elif sys.argv[1] == "--stale":
        show_stale()
    elif sys.argv[1] == "--projects":
        show_projects()
    elif sys.argv[1] == "--set-phase":
        if len(sys.argv) < 4:
            print("Usage: --set-phase <project_id> <phase>")
            print(f"Phases: {', '.join(PHASES)}")
        else:
            set_project_phase(int(sys.argv[2]), sys.argv[3])
    elif sys.argv[1].startswith("-"):
        print(f"Unknown option: {sys.argv[1]}")
        show_usage()
    else:
        company_name = " ".join(sys.argv[1:])
        research_and_add_company(company_name)
