#!/usr/bin/env python3
"""
Contract Win Monitor — SEQ Construction
Monitors news for construction contract wins in SEQ.
Fires Telegram alerts for NEW wins. Auto-creates HIGH PRIORITY leads in CRM.
"""
import warnings; warnings.filterwarnings("ignore")
import json, re, os, sqlite3
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

from exa_py import Exa

# ─── Config ───────────────────────────────────────────────────────────────────
EXA_API_KEY = "ab647372-46fd-423f-86ed-fcb9df6045a7"

CRM_DB = os.path.expanduser("~/.openclaw/workspace/seq-crm/crm.db")
CRON_RESULTS_DIR = os.path.expanduser("~/.openclaw/workspace/cron-results")
AEST = timezone(timedelta(hours=10))
TODAY = datetime.now(AEST).strftime("%Y-%m-%d")
OUTPUT_FILE = os.path.join(CRON_RESULTS_DIR, f"contract-wins-{TODAY}.json")

SEARCH_QUERIES = [
    '"awarded" AND construction AND "Gold Coast"',
    '"awarded" AND construction AND Brisbane',
    '"wins contract" AND construction AND Queensland',
    '"appointed as head contractor" AND construction',
    '"construction contract" AND Queensland AND wins',
    'head contractor appointed AND SEQ construction',
]

SEQ_REGIONS = ["gold coast", "brisbane", "sunshine coast", "ipswich", "logan",
               "toowoomba", "moreton bay", "redland", "queensland"]

NOISE_NAMES = [
    "infrastructure queensland", "queensland government", "abc news",
    "minister for transport", "department of infrastructure",
    "expressions of interest", "urban developer", "inside construction",
    "built com", "news com au", "mirage news", "gympie arterial",
    "beams road", "carseldine", "the urban developer",
    "consortium", "preferred consortium", "global consortium",
    "rail journal", "international railway journal",
]

GENERIC_COMPANY_PATTERNS = [
    r"^(the\s+)?consortium$", r"^(a|an)\s+consortium",
    r"^preferred\s+consortium", r"^global\s+consortium", r"^new\s+consortium",
]

# ─── CRM Helpers ──────────────────────────────────────────────────────────────
def company_in_crm(name):
    if not name:
        return False
    db = sqlite3.connect(CRM_DB)
    cur = db.execute("SELECT id FROM companies WHERE LOWER(name) LIKE ?", (f"%{name.lower()}%",))
    result = cur.fetchone()
    db.close()
    return result is not None

def lead_exists_in_crm(company, project):
    """Check if this company + project combo already exists as a lead."""
    db = sqlite3.connect(CRM_DB)
    cur = db.execute(
        "SELECT id FROM leads WHERE LOWER(company) LIKE ? AND LOWER(what_it_means) LIKE ? LIMIT 1",
        (f"%{company.lower()}%", f"%{project[:30].lower()}%")
    )
    result = cur.fetchone()
    db.close()
    return result is not None

def insert_lead(win):
    db = sqlite3.connect(CRM_DB)
    cur = db.cursor()
    cur.execute(
        """SELECT id FROM leads WHERE LOWER(company)=? AND LOWER(COALESCE(what_it_means,'')) LIKE ? AND created_at>=datetime('now','-7 days')""",
        (win["company"].lower(), f"%{win.get('project','').lower()}%")
    )
    if cur.fetchone():
        db.close(); return False
    cur.execute(
        """INSERT INTO leads (company,source,priority,status,location,what_it_means,action_trigger,created_at)
           VALUES (?,?,?,?,?,?,?,?)""",
        (win["company"], "Contract Win Alert", "high", "new", win.get("location","SEQ"),
         f"[CONTRACT WIN] {win['headline']}",
         f"Contact {win['company']} — {win['project']} | Value: {win['value']}",
         datetime.now(AEST).strftime("%Y-%m-%d %H:%M:%S"))
    )
    db.commit(); db.close()
    return True

# ─── Extraction Helpers ────────────────────────────────────────────────────────
def get_value(text):
    for pat in [
        r'\$[\d,]+(?:\.\d+)?\s*[MBmb](?:\s*(?:project|contract|upgrade))?',
        r'[\d,]+(?:\.\d+)?\s*[MBmb]\s*(?:project|contract|upgrade)',
        r'\$[\d,]+(?:\.\d+)?\s*(?:project|contract|upgrade)',
    ]:
        m = re.search(pat, text, re.I)
        if m:
            return re.sub(r'\s+', ' ', m.group(0)).strip()
    return ""

def get_project(text):
    text = re.sub(r'\s*[-|]\s*(The Urban Developer|Built|News|Com\.au|Inside Construction|Mirage News|ABC News|Industry News|Rail Journal|Urban Developer).*$', '', text, flags=re.I).strip()
    text = re.sub(r'^(News|Update|BREAKING|Exclusive):\s*', '', text, flags=re.I).strip()
    m = re.search(r'"([^"]+)"', text)
    if m:
        return m.group(1).strip()[:100]
    for kw in ['to build','builds','construction of','appointed for','contract for','wins','awarded']:
        idx = text.lower().find(kw)
        if idx != -1:
            seg = text[idx+len(kw):].strip()
            m = re.match(r'([^-"(]+?)(?:\s*[-(]|\s+in\s)', seg)
            if m:
                return m.group(1).strip()[:100]
    return text[:80].strip()

def clean_company_name(name):
    """Remove trailing punctuation and clean up."""
    if not name:
        return ""
    name = re.sub(r'\s+', ' ', name).strip()
    name = re.sub(r'[\s\-]+$', '', name)
    return name

def extract_company(headline, snippet=""):
    """Extract winning company from headline + snippet."""
    combined = f"{headline} {snippet}"
    # Clean headline trailing source
    h = re.sub(r'\s*[-|]\s*(The Urban Developer|Built|News|Com\.au|Inside Construction|Mirage News|ABC News|Industry News|Rail Journal|Urban Developer).*$', '', headline, flags=re.I).strip()
    # CNAME pattern
    C = r"[A-Za-z0-9][A-Za-z0-9\s&\.\-']*"

    # P1: X Awarded Y
    m = re.match(f"^({C})\s+(?:has\s+)?Awarded\s+", h)
    if m: return clean_company_name(m.group(1))

    # P2: X wins Y
    m = re.match(f"^({C})\s+wins\s+", h, re.I)
    if m: return clean_company_name(m.group(1))

    # P3: X appointed
    m = re.match(f"^({C})\s+appointed", h, re.I)
    if m: return clean_company_name(m.group(1))

    # P4: X selected
    m = re.match(f"^({C})\s+selected", h, re.I)
    if m: return clean_company_name(m.group(1))

    # P5: X named
    m = re.match(f"^({C})\s+named", h, re.I)
    if m: return clean_company_name(m.group(1))

    # P6: X secures
    m = re.match(f"^({C})\s+secures", h, re.I)
    if m: return clean_company_name(m.group(1))

    # P7: awarded to X (anywhere)
    m = re.search(f"awarded to\\s+({C})", combined, re.I)
    if m: return clean_company_name(m.group(1))

    # P8: consortium led by X
    m = re.search(f"consortium led by\\s+({C})", combined, re.I)
    if m: return clean_company_name(m.group(1))

    # P9: X Group/Corp/Holdings awarded/wins (anywhere)
    m = re.search(f"({C}(?:Group|Corp|Holdings|Builders|Constructions|Engineering|Projects))\\s+(?:awarded|wins|appointed|selected)", combined, re.I)
    if m: return clean_company_name(m.group(1))

    # P10: X has been awarded (mid-text)
    m = re.search(f"({C})(?:\\s+has been|\\s+was|\\s+has)\\s+awarded", combined, re.I)
    if m: return clean_company_name(m.group(1))

    return ""

def is_noise(name):
    if not name: return True
    nl = name.lower()
    if any(n in nl for n in NOISE_NAMES): return True
    for p in GENERIC_COMPANY_PATTERNS:
        if re.match(p, nl): return True
    if len(name) < 4: return True
    return False

def is_seq(text):
    return any(r in text.lower() for r in SEQ_REGIONS)

# ─── Exa Search ────────────────────────────────────────────────────────────────
def exa_search(query, n=10):
    try:
        exa = Exa(EXA_API_KEY)
        res = exa.search(query, num_results=n,
            start_published_date=(datetime.now(AEST)-timedelta(days=14)).strftime("%Y-%m-%d"),
            end_published_date=TODAY,
            contents={"text": True})
        items = []
        for r in (res.results or []):
            url = getattr(r, 'url', '') or ''
            title = getattr(r, 'title', '') or ''
            text = getattr(r, 'text', '') or ''
            text = re.sub(r'^(Search|News|Advertisement|Australian|World|#)\s*', '', text, flags=re.I).strip()
            text = re.sub(r'https?://\S+', '', text).strip()
            date = str(getattr(r, 'published_date', '') or '').split('T')[0]
            src = re.sub(r'^https?://(www\.)?', '', url).split('/')[0]
            src = re.sub(r'\.(com\.au|net\.au|org\.au)$', '', src, flags=re.I).title()
            items.append({"title": title, "url": url, "snippet": text[:500], "date": date, "source": src or "News"})
        return items
    except Exception as e:
        print(f"  ⚠️ Exa error for '{query[:50]}': {e}")
        return []

# ─── Main ──────────────────────────────────────────────────────────────────────
def main():
    print(f"🔍 Contract Win Monitor — {TODAY}")
    print("=" * 50)

    # Run searches
    print("\n🌐 Searching Exa...")
    all_results = []
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = {ex.submit(exa_search, q): q for q in SEARCH_QUERIES}
        for f in as_completed(futs):
            q = futs[f]
            try:
                rs = f.result()
                print(f"  '{q[:55]}...' → {len(rs)} results")
                all_results.extend(rs)
            except Exception as e:
                print(f"  ⚠️ Error: {e}")
    print(f"\n  Total raw: {len(all_results)}")

    # Deduplicate and enrich
    print("\n📋 Processing results...")
    seen_urls, wins = set(), []
    for item in all_results:
        title, url = item["title"], item["url"]
        if url in seen_urls: continue
        seen_urls.add(url)
        combined = title + " " + item["snippet"]
        if not is_seq(combined): continue
        if not any(k in combined.lower() for k in [
            "awarded","wins contract","appointed","head contractor",
            "preferred consortium","global consortium","selected for",
            "contract awarded","construction contract","named preferred","secures"
        ]): continue

        company = extract_company(title, item["snippet"])
        if is_noise(company): continue
        project = get_project(title)
        value = get_value(combined) or "Undisclosed"

        location = "SEQ"
        for reg in ["gold coast","brisbane","sunshine coast","ipswich","logan"]:
            if reg in combined.lower():
                location = reg.title(); break

        wins.append({
            "company": company, "project": project, "value": value,
            "headline": title, "url": url, "source": item["source"],
            "date": item["date"], "location": location, "is_new": True
        })

    print(f"  Contract wins after filtering: {len(wins)}")
    for w in wins:
        print(f"  • [{w['company']}] {w['project'][:50]} ({w['value']}) — {w['source']}")

    # Check CRM
    print("\n🔎 Checking CRM...")
    new_wins = []
    for win in wins:
        if company_in_crm(win["company"]) or lead_exists_in_crm(win["company"], win["project"]):
            win["is_new"] = False
            reason = "in companies table" if company_in_crm(win["company"]) else "lead already exists"
            print(f"  ⏭️  '{win['company']}' — {reason}")
        else:
            new_wins.append(win)
            print(f"  🆕 '{win['company']}' — NEW lead!")

    # Insert leads
    print("\n💾 Inserting leads...")
    inserted = []
    for win in new_wins:
        if insert_lead(win):
            inserted.append(win)
            print(f"  ✅ {win['company']} — {win['project'][:60]}")
        else:
            print(f"  ⏭️  Duplicate: {win['company']}")

    # Save JSON
    os.makedirs(CRON_RESULTS_DIR, exist_ok=True)
    output = {"date": TODAY, "total_found": len(wins), "new_leads": len(inserted), "wins": wins}
    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)

    # Summary
    print(f"\n{'=' * 50}")
    print(f"📋 CONTRACT WIN SUMMARY — {TODAY}")
    print(f"Total wins: {len(wins)} | New leads: {len(inserted)}")
    for w in inserted:
        print(f"  🚨 {w['company']} — {w['project'][:60]} ({w['value']})")
    print(f"\n✅ {len(inserted)} new contract wins saved to CRM")
    print(f"\nResults: {OUTPUT_FILE}")
    print("✅ Done!")
    return output

if __name__ == "__main__":
    main()
