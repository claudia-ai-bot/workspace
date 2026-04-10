#!/usr/bin/env python3
"""
DM Email Guesser — Innovative solution for the 0-email problem
For real named DMs with a company website: generate first.last@domain emails.
Marks all as 'guessed' (unverified) — Chris can validate before using.
"""
import sqlite3, re, time
from pathlib import Path

DB = '/home/chris/.openclaw/workspace/seq-crm/crm.db'

def extract_domain(website):
    """Extract clean domain from website URL."""
    if not website or website == 'None':
        return None
    m = re.search(r'(?:https?://)?(?:www\.)?(.+?\.(?:com\.au|com|co\.nz|net|org))', website.lower())
    return m.group(1) if m else None

def build_email(name, domain):
    """Build email from name + domain, handling multi-part names."""
    parts = name.strip().split()
    if len(parts) < 2:
        return None
    first = parts[0].lower()
    last = parts[-1].lower()
    # Handle hyphenated/titled names
    last_clean = re.sub(r"[^a-z]", "", last)
    first_clean = re.sub(r"[^a-z]", "", first)
    if not first_clean or not last_clean:
        return None
    return f"{first_clean}.{last_clean}@{domain}"

def is_real_person(name):
    """Return False if it's a TBC/placeholder name."""
    tbc_patterns = ['tbc', 't.b.c', 'to be confirmed', 'research needed',
                    'unknown', ' leadership', ' team', ' executive',
                    ' group', ' construction', ' manager', ' director']
    n = name.lower()
    if any(p in n for p in tbc_patterns):
        return False
    # Single word names that are company names
    if len(name.split()) == 1:
        return False
    return True

def main():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        SELECT dm.id, dm.name, dm.title, c.name as company, c.website, c.tier
        FROM decision_makers dm
        JOIN companies c ON c.id = dm.company_id
        WHERE (dm.email IS NULL OR dm.email = '')
        ORDER BY c.tier DESC, c.name
    """)
    dms = cur.fetchall()
    
    # Count real people vs TBC
    real = [d for d in dms if is_real_person(d['name'])]
    tbc = [d for d in dms if not is_real_person(d['name'])]
    
    print(f"DM Email Guesser")
    print(f"{'='*60}")
    print(f"Total DMs without email: {len(dms)}")
    print(f"  Real people (will process): {len(real)}")
    print(f"  TBC/placeholder (skipping): {len(tbc)}")
    print()

    updated = 0
    skipped_no_domain = 0
    skipped_tbc = 0
    
    # Preview table
    print(f"{'NAME':<30} {'COMPANY':<28} {'GUESSED EMAIL':<42} {'STATUS'}")
    print("-" * 110)

    for r in real:
        web = r['website']
        domain = extract_domain(web)
        email = build_email(r['name'], domain) if domain else None
        company = r['company'][:27]
        
        if email:
            # Write guessed email to DB
            cur.execute(
                "UPDATE decision_makers SET email = ?, notes = ? WHERE id = ?",
                (email, f"[GUESSED - needs verification] company domain: {domain}", r['id'])
            )
            updated += 1
            status = "✅ guessed"
        else:
            status = "⚠️ no domain" if not domain else "❌ failed"
            skipped_no_domain += 1
        
        display_email = email or '(no domain)'
        print(f"{r['name']:<30} {company:<28} {display_email:<42} {status}")

    conn.commit()
    
    print()
    print(f"Done: {updated} emails guessed, {skipped_no_domain} skipped (no domain)")
    print(f"TBC entries left as-is (not real people): {len(tbc)}")
    
    # Summary
    cur.execute("SELECT COUNT(*) FROM decision_makers WHERE email IS NOT NULL AND email != ''")
    total_with_email = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM decision_makers WHERE email LIKE '[GUESSED%'")
    guessed = cur.fetchone()[0]
    print(f"\nCRM now has: {total_with_email} DMs with email ({guessed} guessed)")
    
    conn.close()

if __name__ == '__main__':
    main()
