#!/usr/bin/env python3
"""
R&D Weekly Debate Script
=========================
Runs three strategic agents in parallel (Market Scout, Pipeline Doctor, BD Strategist)
using the jason agent (MiniMax-M2.5) via openclaw CLI.
Produces a formatted strategic memo saved to cron-results/.

Usage:
    python3 rd-debate.py
"""

import subprocess
import json
import sqlite3
import os
import re
from datetime import datetime, date, timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# ─── Config ───────────────────────────────────────────────────────────────────

DB_PATH = "/home/chris/.openclaw/workspace/seq-crm/crm.db"
INTEL_DIR = Path("/home/chris/.openclaw/workspace/intelligence")
CRON_RESULTS_DIR = Path("/home/chris/.openclaw/workspace/cron-results")
CRON_RESULTS_DIR.mkdir(parents=True, exist_ok=True)

AGENT_ID = "jason"   # minimax/MiniMax-M2.5
TIMEOUT_SEC = 120

# ─── Data Fetchers ─────────────────────────────────────────────────────────────

def fetch_crm_snapshot():
    """Return a dict with key CRM data for the agents."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    snapshot = {}

    # Companies
    cur.execute("""
        SELECT c.id, c.name, c.tier, c.sector, c.location, c.active_projects,
               (SELECT MAX(a.created_at) FROM activities a WHERE a.company_id = c.id) as last_activity
        FROM companies c
        ORDER BY last_activity DESC NULLS LAST
    """)
    snapshot["companies"] = [dict(r) for r in cur.fetchall()]

    # Leads
    cur.execute("""
        SELECT id, date, company, intel_type, source, what_it_means,
               action_trigger, created_at, location, sector,
               hiring_manager, hiring_manager_title, enriched
        FROM leads
        ORDER BY created_at DESC
        LIMIT 30
    """)
    snapshot["leads"] = [dict(r) for r in cur.fetchall()]

    # Job adverts summary by sector
    cur.execute("""
        SELECT sector, COUNT(*) as cnt
        FROM job_adverts
        GROUP BY sector
        ORDER BY cnt DESC
    """)
    snapshot["sector_counts"] = [dict(r) for r in cur.fetchall()]

    # Top roles
    cur.execute("""
        SELECT role_type, COUNT(*) as cnt
        FROM job_adverts
        GROUP BY role_type
        ORDER BY cnt DESC
        LIMIT 10
    """)
    snapshot["role_counts"] = [dict(r) for r in cur.fetchall()]

    # Projects
    cur.execute("""
        SELECT id, name, status, description, company_id
        FROM projects
        ORDER BY created_at DESC
        LIMIT 20
    """)
    snapshot["projects"] = [dict(r) for r in cur.fetchall()]

    # Decision makers
    cur.execute("""
        SELECT dm.id, dm.company_id, dm.name, dm.title, dm.role, c.name as company_name
        FROM decision_makers dm
        JOIN companies c ON c.id = dm.company_id
        LIMIT 20
    """)
    snapshot["decision_makers"] = [dict(r) for r in cur.fetchall()]

    # Stale companies (no activity in 14+ days)
    cur.execute("""
        SELECT x.id, x.name, x.tier, x.sector, x.last_activity,
               (SELECT COUNT(*) FROM decision_makers dm WHERE dm.company_id = x.id) as dm_count
        FROM (
            SELECT c.id, c.name, c.tier, c.sector,
                   (SELECT MAX(a.created_at) FROM activities a WHERE a.company_id = c.id) as last_activity
            FROM companies c
        ) x
        WHERE x.last_activity IS NULL
           OR x.last_activity < datetime('now', '-14 days')
        ORDER BY x.last_activity ASC NULLS FIRST
        LIMIT 10
    """)
    snapshot["stale_companies"] = [dict(r) for r in cur.fetchall()]

    # Recent job adverts
    cur.execute("""
        SELECT id, title, sector, tier, location, role_type
        FROM job_adverts
        ORDER BY rowid DESC
        LIMIT 30
    """)
    snapshot["recent_jobs"] = [dict(r) for r in cur.fetchall()]

    conn.close()
    return snapshot


def fetch_latest_intel():
    """Return the most recent daily-intel JSON files for context."""
    intel_files = sorted(INTEL_DIR.glob("daily-intel-*.json"), reverse=True)
    reports = []
    for f in intel_files[:3]:
        try:
            with open(f) as fp:
                d = json.load(fp)
                reports.append({
                    "date": d.get("date"),
                    "scanned_at": d.get("scanned_at"),
                    "snapshot": d.get("crm_snapshot", {}),
                    "changes": d.get("crm_changes", {}),
                    "news_titles": [n.get("title", "")[:120] for n in d.get("market_news", [])[:8]],
                    "summary": d.get("summary", "")[:400],
                })
        except Exception:
            pass
    return reports


def build_agent_context():
    """Build the shared CRM context string for all three agents."""
    snapshot = fetch_crm_snapshot()
    intel = fetch_latest_intel()
    today_str = date.today().isoformat()

    sector_lines = "\n".join(
        f"  - {r['sector']}: {r['cnt']} job adverts"
        for r in snapshot["sector_counts"]
    )
    role_lines = "\n".join(
        f"  - {r['role_type']}: {r['cnt']} adverts"
        for r in snapshot["role_counts"]
    )
    stale_lines = []
    for c in snapshot["stale_companies"]:
        stale_lines.append(
            f"  - {c['name']} (Tier {c['tier']}, {c['sector']}) | "
            f"last activity: {c['last_activity'] or 'NEVER'} | DMs: {c['dm_count']}"
        )
    lead_lines = []
    for l in snapshot["leads"][:15]:
        lead_lines.append(
            f"  - [{l['date']}] {l['company']} | {l['intel_type']} | "
            f"{l['location']} | HM: {l['hiring_manager'] or '?'} "
            f"({l['hiring_manager_title'] or '?'}) | Enriched: {l['enriched']}"
        )
    proj_lines = []
    for p in snapshot["projects"][:10]:
        proj_lines.append(f"  - {p['name']} | {p['status']} | {p['description'][:80]}")
    recent_job_lines = []
    for j in snapshot["recent_jobs"][:10]:
        recent_job_lines.append(f"  - {j['title']} | {j['sector']} | {j['location']}")
    intel_lines = []
    for r in intel:
        intel_lines.append(f"\n  -- Intel from {r['date']} --")
        intel_lines.append(f"  Summary: {r['summary'][:300]}")
        for t in r.get("news_titles", [])[:5]:
            intel_lines.append(f"  • {t}")

    ctx = f"""
=== CRM SNAPSHOT ({today_str}) ===
Total companies: {len(snapshot['companies'])}
Total decision makers: {len(snapshot['decision_makers'])}
Total leads: {len(snapshot['leads'])}
Total job adverts in DB: {sum(r['cnt'] for r in snapshot['sector_counts'])}
Total projects: {len(snapshot['projects'])}

--- SECTOR BREAKDOWN ---
{sector_lines}

--- TOP ROLES IN DEMAND ---
{role_lines}

--- TOP 15 RECENT LEADS ---
{chr(10).join(lead_lines)}

--- RECENT JOB ADVERTS (sample) ---
{chr(10).join(recent_job_lines)}

--- RECENT PROJECTS ---
{chr(10).join(proj_lines)}

--- STALE COMPANIES (14+ days, no activity) ---
{chr(10).join(stale_lines) if stale_lines else '  None — all companies have recent activity'}

--- MARKET INTEL (last 3 scans) ---
{chr(10).join(intel_lines)}
"""
    return ctx


# ─── Agent Briefs ─────────────────────────────────────────────────────────────

AGENT_A_BRIEF = """You are **Market Scout** — a sharp construction recruitment market analyst.

Your job: Analyse the current SEQ (South East Queensland) construction market for recruitment opportunities.
Use the CRM data provided below. Identify opportunities Chris should act on this week.

Respond EXACTLY with this format (no extra preamble, no headings, just bullets):
```
MARKET_SCOUT_SECTION:
• [bullet 1 — specific company names, project names, sector data]
• [bullet 2]
• [bullet 3]
• [bullet 4]
• [bullet 5 — under-the-radar gem most recruiters are missing]
```"""

AGENT_B_BRIEF = """You are **Pipeline Doctor** — a specialist in recruitment pipeline diagnostics.

Your job: Diagnose problems in Chris's recruitment pipeline and recommend fixes.
Use the CRM data provided below.

Chris's business context:
- Starting at Lead Group (Gold Coast) on May 4, 2026 — construction recruitment, SEQ
- White-collar only: PM, CM, QS, Contracts, Design Manager
- KPIs: $200k/quarter, $1M billings → 81/19 split
- CRM has 83 companies tracked

Respond EXACTLY with this format (no extra preamble, no headings, just bullets):
```
PIPELINE_DOCTOR_SECTION:
• [bullet 1 — bottleneck diagnosis, be specific with data]
• [bullet 2 — stuck companies with data]
• [bullet 3 — highest-value neglected opportunity]
• [bullet 4 — quick win Chris can execute this week]
• [bullet 5 — one thing to fix immediately]
```"""

AGENT_C_BRIEF = """You are **BD Strategist** — a pragmatic business development advisor for recruitment.

Your job: Develop Chris's business development strategy for the week ahead.
Use the CRM data provided below.

Chris's business context:
- Starting at Lead Group (Gold Coast) on May 4, 2026 — construction recruitment, SEQ
- White-collar only: PM, CM, QS, Contracts, Design Manager
- KPIs: $200k/quarter, $1M billings → 81/19 split
- CRM has 83 companies tracked, $700k liquid assets, targeting $2.5M by 50
- Candidate-short market — supply is the constraint

Respond EXACTLY with this format (no extra preamble, no headings, just bullets):
```
BD_STRATEGIST_SECTION:
• [bullet 1 — #1 outreach priority this week, specific]
• [bullet 2 — candidate type to focus sourcing on, given shortage]
• [bullet 3 — Top 3 companies to call first, highest intent + relationship potential]
• [bullet 4 — What to NOT waste time on this week]
• [bullet 5 — One bold move worth trying]
```"""


# ─── Subagent Runner ──────────────────────────────────────────────────────────

def run_agent(name: str, brief: str, context: str, timeout: int = TIMEOUT_SEC) -> str:
    """Run a single agent via openclaw agent --json and return the text response."""
    full_message = f"{brief.strip()}\n\n--- CRM DATA ---\n{context}"
    unique_session = f"rd-{name.lower().replace(' ', '-')}-{os.getpid()}"

    cmd = [
        "openclaw", "agent",
        "--json",
        "--message", full_message,
        "--agent", AGENT_ID,
        "--session-id", unique_session,
        "--thinking", "off",
        "--timeout", str(timeout),
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout + 15,
        )
        if result.returncode != 0:
            return f"[ERROR exit={result.returncode}] {result.stderr[:300]}"
        try:
            data = json.loads(result.stdout)
            payloads = data.get("result", {}).get("payloads", [])
            if payloads:
                return payloads[0].get("text", "[empty response]")
            return f"[NO_PAYLOADS] {result.stdout[:500]}"
        except json.JSONDecodeError as e:
            return f"[JSON_ERROR {e}] {result.stdout[:500]}"
    except subprocess.TimeoutExpired:
        return f"[TIMEOUT after {timeout}s]"
    except Exception as e:
        return f"[EXCEPTION {type(e).__name__}] {str(e)}"


# ─── Memo Formatter ────────────────────────────────────────────────────────────

def extract_section(text: str, prefix: str) -> str:
    """Pull out a named section from agent output, reformat bullets cleanly."""
    # Find the section
    pattern = re.escape(prefix) + r":\s*\n(.*?)(?=\n(?:[^•\n]|$))"
    m = re.search(pattern, text, re.DOTALL)
    if not m:
        # Fallback: just find prefix + content up to 500 chars
        idx = text.find(prefix + ":")
        if idx >= 0:
            raw = text[idx + len(prefix) + 1:].strip()[:600]
        else:
            return f"[No data — raw: {text[:100]}]"
    else:
        raw = m.group(1).strip()[:600]

    # Reformat: ensure each line starts with •
    lines = []
    for line in raw.split("\n"):
        line = line.strip()
        if not line:
            continue
        # Strip existing bullet markers
        line = re.sub(r"^[\•\-\*\◦]\s*", "", line)
        if line:
            lines.append(f"• {line}")
    return "\n".join(lines) if lines else f"[Empty section — raw: {text[:100]}]"


def format_memo(agent_a_out: str, agent_b_out: str, agent_c_out: str) -> str:
    today_str = date.today().isoformat()
    today_display = datetime.strptime(today_str, "%Y-%m-%d").strftime("%A, %d %B %Y")

    ms = extract_section(agent_a_out, "MARKET_SCOUT_SECTION")
    pd = extract_section(agent_b_out, "PIPELINE_DOCTOR_SECTION")
    bd = extract_section(agent_c_out, "BD_STRATEGIST_SECTION")

    memo = f"""📊 R&D Weekly — {today_display}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🌡️ MARKET PULSE (Market Scout)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{ms}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💊 PIPELINE HEALTH (Pipeline Doctor)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{pd}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 THIS WEEK'S PLAN (BD Strategist)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{bd}

---
Built by Claude · SEQ CRM
"""
    return memo


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    ts = datetime.now()
    print(f"[{ts:%H:%M:%S}] Building R&D Debate memo...")

    print(f"[{ts:%H:%M:%S}] Fetching CRM data...")
    ctx = build_agent_context()
    print(f"[{ts:%H:%M:%S}] CRM context built ({len(ctx)} chars)")

    print(f"[{ts:%H:%M:%S}] Launching 3 agents in parallel (MiniMax-M2.5)...")
    results = {}
    with ThreadPoolExecutor(max_workers=3) as ex:
        futures = {
            ex.submit(run_agent, "Market Scout", AGENT_A_BRIEF, ctx): "A",
            ex.submit(run_agent, "Pipeline Doctor", AGENT_B_BRIEF, ctx): "B",
            ex.submit(run_agent, "BD Strategist", AGENT_C_BRIEF, ctx): "C",
        }
        for future in as_completed(futures):
            key = futures[future]
            ts = datetime.now()
            try:
                result = future.result()
                results[key] = result
                preview = result[:80].replace("\n", " ")
                print(f"[{ts:%H:%M:%S}] Agent {key} done ({len(result)} chars): {preview}")
            except Exception as e:
                results[key] = f"[EXCEPTION] {e}"
                print(f"[{ts:%H:%M:%S}] Agent {key} FAILED: {e}")

    memo = format_memo(
        results.get("A", ""),
        results.get("B", ""),
        results.get("C", ""),
    )

    today_str = date.today().isoformat()
    memo_path = CRON_RESULTS_DIR / f"rd-memo-{today_str}.txt"
    with open(memo_path, "w") as f:
        f.write(memo)

    # Save memo to CRM weekly_reviews table
    today = datetime.now()
    week_start = (today - timedelta(days=today.weekday())).strftime('%Y-%m-%d')
    week_end = (today + timedelta(days=6 - today.weekday())).strftime('%Y-%m-%d')
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id FROM weekly_reviews WHERE week_start = ?", (week_start,))
    row = cur.fetchone()
    if row:
        cur.execute("UPDATE weekly_reviews SET rd_memo = ?, week_end = ? WHERE week_start = ?", (memo, week_end, week_start))
    else:
        cur.execute(
            "INSERT INTO weekly_reviews (week_start, week_end, rd_memo, created_at) VALUES (?, ?, ?, ?)",
            (week_start, week_end, memo, datetime.now().isoformat())
        )
    conn.commit()
    conn.close()

    ts = datetime.now()
    print(f"[{ts:%H:%M:%S}] Memo saved: {memo_path}")
    print()
    print("=" * 60)
    print(memo)
    print("=" * 60)
    return memo_path


if __name__ == "__main__":
    main()
