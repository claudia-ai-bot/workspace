#!/usr/bin/env python3
"""
SEQ Construction CRM - Flask Web App
Market map database + web UI
Accessible via Tailscale
"""

import os
import sqlite3
import csv
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file, send_from_directory
import json

app = Flask(__name__)
app.config['DATABASE'] = os.path.expanduser("~/.openclaw/workspace/seq-crm/crm.db")

# Custom Jinja filter for human-readable dates
@app.template_filter('format_date')
def format_date(date_str):
    """Format date string to '23 Mar 2026' format - handles timestamps too"""
    if not date_str:
        return '—'
    s = str(date_str).strip()[:10]  # Just take YYYY-MM-DD portion
    try:
        dt = datetime.strptime(s, '%Y-%m-%d')
        return dt.strftime('%d %b %Y')
    except:
        return s

@app.template_filter('format_date_short')
def format_date_short(date_str):
    """Format date string to 'Mon 23 Mar' format (short)"""
    if not date_str:
        return '—'
    try:
        dt = datetime.strptime(str(date_str), '%Y-%m-%d')
        return dt.strftime('%d %b')
    except:
        return str(date_str)

@app.template_filter('days_ago')
def days_ago(date_str):
    """Calculate days ago from a date string"""
    if not date_str:
        return None
    try:
        dt = datetime.strptime(str(date_str)[:10], '%Y-%m-%d')
        return (datetime.now() - dt).days
    except:
        return None

# CORS headers for remote access
@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response

def get_db():
    """Get database connection"""
    db = sqlite3.connect(app.config['DATABASE'])
    db.row_factory = sqlite3.Row
    return db

def init_db():
    """Initialize database schema"""
    db = get_db()
    cursor = db.cursor()
    
    # Companies table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS companies (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            tier TEXT,
            sector TEXT,
            location TEXT,
            active_projects TEXT,
            upcoming_projects TEXT,
            competitors TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Decision Makers table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS decision_makers (
            id INTEGER PRIMARY KEY,
            company_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            title TEXT,
            role TEXT,
            phone TEXT,
            email TEXT,
            linkedin TEXT,
            hiring_signals TEXT,
            relationship_score INTEGER DEFAULT 1,
            last_contact DATE,
            next_action TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
        )
    ''')
    
    # Candidates table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS candidates (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            current_company TEXT,
            title TEXT,
            specialism TEXT,
            years_experience INTEGER,
            salary_band TEXT,
            location TEXT,
            mobility TEXT,
            flight_risk TEXT,
            known_offers TEXT,
            who_wants_them TEXT,
            relationship_score INTEGER DEFAULT 1,
            last_contact DATE,
            next_follow_up DATE,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Deals/Pipeline table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS deals (
            id INTEGER PRIMARY KEY,
            client TEXT NOT NULL,
            role TEXT NOT NULL,
            salary_value INTEGER,
            fee_value INTEGER,
            stage TEXT DEFAULT 'Prospect Identified',
            competition TEXT,
            probability INTEGER DEFAULT 50,
            next_action TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Jobs table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            company_id INTEGER,
            company TEXT,
            project_id INTEGER,
            status TEXT DEFAULT 'Open',
            job_type TEXT,
            location TEXT,
            salary_min INTEGER,
            salary_max INTEGER,
            description TEXT,
            requirements TEXT,
            source TEXT,
            contact_id INTEGER,
            fee_percentage REAL DEFAULT 15.0,
            estimated_fee REAL,
            date_received TEXT,
            date_filled TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (company_id) REFERENCES companies(id),
            FOREIGN KEY (project_id) REFERENCES projects(id),
            FOREIGN KEY (contact_id) REFERENCES contacts(id)
        )
    ''')
    
    # Add job_id column to submissions table (if not exists)
    try:
        cursor.execute('ALTER TABLE submissions ADD COLUMN job_id INTEGER REFERENCES jobs(id)')
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    db.commit()
    db.close()

@app.route('/today')
def today_view():
    """Today's action list - the most important view in the CRM"""
    from datetime import datetime, timedelta
    db = get_db()
    cursor = db.cursor()
    today = datetime.now().strftime('%Y-%m-%d')
    today_display = datetime.now().strftime('%A, %d %B %Y')
    
    # 1. Overdue contact follow-ups (next_touch_date < today)
    cursor.execute('''
        SELECT id, contact_name, company, type, next_touch_date, last_interaction
        FROM contacts 
        WHERE next_touch_date IS NOT NULL AND next_touch_date != '' AND next_touch_date < ?
        ORDER BY next_touch_date ASC
    ''', (today,))
    overdue_contacts_raw = cursor.fetchall()
    overdue_contacts = []
    for c in overdue_contacts_raw:
        row = dict(c)
        try:
            due = datetime.strptime(row['next_touch_date'], '%Y-%m-%d')
            row['days_overdue'] = (datetime.now() - due).days
        except:
            row['days_overdue'] = 0
        overdue_contacts.append(row)
    
    # 2. Overdue candidate follow-ups (next_follow_up < today)
    cursor.execute('''
        SELECT id, name, current_company, title, next_follow_up, last_contact
        FROM candidates 
        WHERE next_follow_up IS NOT NULL AND next_follow_up != '' AND next_follow_up < ?
        ORDER BY next_follow_up ASC
    ''', (today,))
    overdue_candidates_raw = cursor.fetchall()
    overdue_candidates = []
    for c in overdue_candidates_raw:
        row = dict(c)
        try:
            due = datetime.strptime(row['next_follow_up'], '%Y-%m-%d')
            row['days_overdue'] = (datetime.now() - due).days
        except:
            row['days_overdue'] = 0
        overdue_candidates.append(row)
    
    # 3. Stale Tier 1 contacts (last_interaction > 14 days ago) - from contacts table
    fourteen_days_ago = (datetime.now() - timedelta(days=14)).strftime('%Y-%m-%d')
    cursor.execute('''
        SELECT c.id, c.contact_name, c.company, c.last_interaction, c.type
        FROM contacts c
        LEFT JOIN companies co ON c.company = co.name
        WHERE co.tier = 'Tier 1' OR co.tier = '1'
        AND (c.last_interaction IS NULL OR c.last_interaction = '' OR c.last_interaction < ?)
    ''', (fourteen_days_ago,))
    stale_tier1_raw = cursor.fetchall()
    stale_tier1 = []
    for c in stale_tier1_raw:
        row = dict(c)
        try:
            if row['last_interaction']:
                last = datetime.strptime(row['last_interaction'], '%Y-%m-%d')
                days = (datetime.now() - last).days
                if days >= 14:
                    row['days_stale'] = days
                    stale_tier1.append(row)
            else:
                row['days_stale'] = 999
                stale_tier1.append(row)
        except:
            row['days_stale'] = 999
            stale_tier1.append(row)
    stale_tier1.sort(key=lambda x: -x['days_stale'])
    
    # 4. Stale Tier 2 contacts (last_interaction > 21 days ago)
    twenty_one_days_ago = (datetime.now() - timedelta(days=21)).strftime('%Y-%m-%d')
    cursor.execute('''
        SELECT c.id, c.contact_name, c.company, c.last_interaction, c.type
        FROM contacts c
        LEFT JOIN companies co ON c.company = co.name
        WHERE co.tier = 'Tier 2' OR co.tier = '2'
        AND (c.last_interaction IS NULL OR c.last_interaction = '' OR c.last_interaction < ?)
    ''', (twenty_one_days_ago,))
    stale_tier2_raw = cursor.fetchall()
    stale_tier2 = []
    for c in stale_tier2_raw:
        row = dict(c)
        try:
            if row['last_interaction']:
                last = datetime.strptime(row['last_interaction'], '%Y-%m-%d')
                days = (datetime.now() - last).days
                if days >= 21:
                    row['days_stale'] = days
                    stale_tier2.append(row)
            else:
                row['days_stale'] = 999
                stale_tier2.append(row)
        except:
            row['days_stale'] = 999
            stale_tier2.append(row)
    stale_tier2.sort(key=lambda x: -x['days_stale'])
    
    # 5. Deals stuck in same stage for 10+ days
    ten_days_ago = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')
    cursor.execute('''
        SELECT id, client, role, stage, fee_value, updated_at
        FROM deals 
        WHERE updated_at IS NOT NULL AND updated_at < ?
        AND stage NOT IN ('Placement', 'Closed', 'Lost', 'Withdrawn')
        ORDER BY updated_at ASC
    ''', (ten_days_ago,))
    stuck_deals_raw = cursor.fetchall()
    stuck_deals = []
    for d in stuck_deals_raw:
        row = dict(d)
        try:
            updated = datetime.strptime(row['updated_at'][:10], '%Y-%m-%d')
            row['days_stuck'] = (datetime.now() - updated).days
        except:
            row['days_stuck'] = 10
        stuck_deals.append(row)
    
    # 6. Visits due today
    cursor.execute('''
        SELECT v.id, v.visit_date, v.contact_name, v.notes, c.name as company_name
        FROM visits v
        LEFT JOIN companies c ON v.company_id = c.id
        WHERE v.visit_date = ?
    ''', (today,))
    visits_due = [dict(v) for v in cursor.fetchall()]
    
    # 7. Quick stats
    # Calls to make = overdue contacts + overdue candidates + stale contacts
    calls_to_make = len(overdue_contacts) + len(overdue_candidates)
    
    # Visits today
    visits_today_count = len(visits_due)
    
    # Follow-ups due (contacts due today + candidates due today)
    cursor.execute('''
        SELECT COUNT(*) as count FROM contacts 
        WHERE next_touch_date = ?
    ''', (today,))
    contacts_due_today = cursor.fetchone()['count']
    cursor.execute('''
        SELECT COUNT(*) as count FROM candidates 
        WHERE next_follow_up = ?
    ''', (today,))
    candidates_due_today = cursor.fetchone()['count']
    followups_due = contacts_due_today + candidates_due_today + len(overdue_contacts) + len(overdue_candidates)
    
    # Deals in pipeline
    cursor.execute('''
        SELECT COUNT(*) as count FROM deals 
        WHERE stage NOT IN ('Placement', 'Closed', 'Lost', 'Withdrawn')
    ''')
    deals_in_pipeline = cursor.fetchone()['count']
    
    # Counts for header
    overdue_count = len(overdue_contacts) + len(overdue_candidates)
    due_today_count = contacts_due_today + candidates_due_today + visits_today_count
    stale_count = len(stale_tier1) + len(stale_tier2)
    total_actions = overdue_count + due_today_count + stale_count + len(stuck_deals)
    
    db.close()
    
    return render_template('today.html',
        today_date=today_display,
        total_actions=total_actions,
        overdue_count=overdue_count,
        due_today_count=due_today_count,
        stale_count=stale_count,
        calls_to_make=calls_to_make,
        visits_today=visits_today_count,
        followups_due=followups_due,
        deals_in_pipeline=deals_in_pipeline,
        overdue_contacts=overdue_contacts,
        overdue_candidates=overdue_candidates,
        stale_tier1=stale_tier1,
        stale_tier2=stale_tier2,
        stuck_deals=stuck_deals,
        visits_due=visits_due
    )

@app.route('/api/today/snooze', methods=['POST'])
def api_today_snooze():
    """Snooze a follow-up by N days"""
    from datetime import datetime, timedelta
    data = request.json
    table = data.get('table')
    record_id = data.get('id')
    days = data.get('days', 1)
    
    new_date = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d')
    
    db = get_db()
    cursor = db.cursor()
    try:
        if table == 'contacts':
            cursor.execute('UPDATE contacts SET next_touch_date = ? WHERE id = ?', (new_date, record_id))
        elif table == 'candidates':
            cursor.execute('UPDATE candidates SET next_follow_up = ? WHERE id = ?', (new_date, record_id))
        else:
            return jsonify({'status': 'error', 'message': 'Invalid table'}), 400
        db.commit()
        db.close()
        return jsonify({'status': 'success'})
    except Exception as e:
        db.close()
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/api/today/done', methods=['POST'])
def api_today_done():
    """Mark a follow-up as done (set last contact to today, clear next date)"""
    from datetime import datetime
    data = request.json
    table = data.get('table')
    record_id = data.get('id')
    today = datetime.now().strftime('%Y-%m-%d')
    
    db = get_db()
    cursor = db.cursor()
    try:
        if table == 'contacts':
            cursor.execute('UPDATE contacts SET last_interaction = ?, next_touch_date = NULL WHERE id = ?', (today, record_id))
        elif table == 'candidates':
            cursor.execute('UPDATE candidates SET last_contact = ?, next_follow_up = NULL WHERE id = ?', (today, record_id))
        else:
            return jsonify({'status': 'error', 'message': 'Invalid table'}), 400
        db.commit()
        db.close()
        return jsonify({'status': 'success'})
    except Exception as e:
        db.close()
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/outreach')
def outreach_command():
    """Outreach Command - tactical outbound execution center"""
    return send_from_directory('.', 'outreach-command.html')

@app.route('/boolean')
def boolean_generator():
    """Boolean String Generator — construction recruitment sourcing"""
    return send_from_directory('.', 'boolean-generator.html')

@app.route('/territory-intelligence')
def territory_intelligence():
    """Territory Intelligence — market map with tier/sector/location views"""
    return send_from_directory('.', 'territory-intelligence.html')

@app.route('/lead-command')
def lead_command():
    """Lead Command — operational lead intelligence hub (pure Python HTML generation)"""
    import sqlite3, json as _json, re
    from collections import Counter
    CRM_DB = os.path.expanduser("~/.openclaw/workspace/seq-crm/crm.db")
    conn = sqlite3.connect(CRM_DB)
    cur = conn.cursor()
    cur.execute('''
        SELECT l.id, l.company, l.intel_type, l.source, l.what_it_means, l.action_trigger,
               l.hiring_manager, l.hiring_manager_title, l.hirer_email, l.hirer_linkedin,
               l.phone, l.sector, l.location, l.priority, l.status, l.lead_score, l.created_at
        FROM leads l ORDER BY l.lead_score DESC NULLS LAST
    ''')
    cols = [d[0] for d in cur.description]
    leads = [dict(zip(cols, r)) for r in cur.fetchall()]
    conn.close()

    total_leads = len(leads)
    active_leads = len([l for l in leads if l['status'] == 'active'])
    hot_leads = len([l for l in leads if l['lead_score'] and l['lead_score'] >= 70])
    warm_leads = len([l for l in leads if l['lead_score'] and 50 <= l['lead_score'] < 70])
    with_email = len([l for l in leads if l.get('hirer_email')])
    with_phone = len([l for l in leads if l.get('phone')])
    with_li = len([l for l in leads if l.get('hirer_linkedin')])
    full_contact = len([l for l in leads if l.get('hirer_email') and l.get('phone') and l.get('hirer_linkedin')])
    top5 = leads[:5]
    sector_counts = Counter(l['sector'] for l in leads if l['sector'])
    sector_breakdown = sorted(sector_counts.items(), key=lambda x: -x[1])
    sector_max = sector_breakdown[0][1] if sector_breakdown else 1
    sectors = sorted(set(l['sector'] for l in leads if l['sector']))
    sources = sorted(set(l['source'] for l in leads if l['source']))

    def esc(s):
        return str(s or '').replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('"','&quot;')

    def sc_class(s):
        s = s or 0
        return 'hot' if s >= 70 else 'warm' if s >= 50 else 'cool' if s >= 30 else 'cold'

    # Top 5 HTML
    top5_html = ''
    for i, l in enumerate(top5, 1):
        sc = sc_class(l['lead_score'])
        rank_cls = f'r{i}' if i <= 3 else ''
        intel = esc((l['what_it_means'] or '')[:80])
        top5_html += f'<div class="top5-item"><div class="top5-rank {rank_cls}">#{i}</div><div class="top5-content"><div class="top5-company">{esc(l["company"])}</div><div class="top5-intel">{intel}</div></div><div class="top5-score score {sc}">{l["lead_score"] or "—"}</div></div>'

    # Sector breakdown HTML
    sector_html = ''
    for name, count in sector_breakdown:
        bar_pct = int(count / sector_max * 100)
        sector_html += f'<div class="sector-item"><div class="sector-row"><span class="sector-name">{esc(name)}</span><span class="sector-count">{count}</span></div><div class="sector-bar-bg"><div class="sector-bar" style="width:{bar_pct}%"></div></div></div>'

    # Sector / Source options
    sectors_opts = ''.join(f'<option value="{esc(s)}">{esc(s)}</option>' for s in sectors)
    sources_opts = ''.join(f'<option value="{esc(s)}">{esc(s)}</option>' for s in sources)

    # Coverage HTML
    ep = lambda n: (n * 100 // total_leads) if total_leads else 0
    coverage_html = (
        f'<div class="coverage-item"><span class="coverage-label"><span class="coverage-icon">📧</span> Has Email</span><span class="coverage-value yes">{with_email} ({ep(with_email)}%)</span></div>'
        f'<div class="coverage-item"><span class="coverage-label"><span class="coverage-icon">📞</span> Has Phone</span><span class="coverage-value {"yes" if with_phone else "no"}">{with_phone} ({ep(with_phone)}%)</span></div>'
        f'<div class="coverage-item"><span class="coverage-label"><span class="coverage-icon">💼</span> Has LinkedIn</span><span class="coverage-value {"yes" if with_li else "no"}">{with_li} ({ep(with_li)}%)</span></div>'
        f'<div class="coverage-item"><span class="coverage-label"><span class="coverage-icon">✅</span> Full Contact</span><span class="coverage-value {"yes" if full_contact else "no"}">{full_contact} ({ep(full_contact)}%)</span></div>'
        f'<div class="coverage-item"><span class="coverage-label"><span class="coverage-icon">❌</span> No Contact</span><span class="coverage-value no">{total_leads - with_email}</span></div>'
    )

    # Lead rows HTML
    def render_row(l):
        sc = sc_class(l.get('lead_score'))
        sv = l.get('lead_score')
        has_email = bool(l.get('hirer_email'))
        has_phone = bool(l.get('phone'))
        has_li = bool(l.get('hirer_linkedin'))
        email = esc(l.get('hirer_email', ''))
        phone = esc(l.get('phone', ''))
        li = esc(l.get('hirer_linkedin', ''))
        email_badge = '<span class="badge-mini email">📧</span>' if has_email else '<span class="badge-mini missing">📧 —</span>'
        phone_badge = '<span class="badge-mini phone">📞</span>' if has_phone else '<span class="badge-mini missing">📞</span>'
        li_badge = '<span class="badge-mini li">💼</span>' if has_li else '<span class="badge-mini missing">💼 —</span>'
        email_href = f'mailto:{email}?subject=Construction+Recruitment+Partnership+—+{esc(l.get("company",""))}' if email else '#'
        phone_href = f'tel:{phone}' if phone else '#'
        action_email = f'<a href="{email_href}" class="btn-icon email-btn" target="_blank">📧</a>' if email else '<span class="btn-icon" style="opacity:0.3;cursor:not-allowed">📧</span>'
        action_phone = f'<a href="{phone_href}" class="btn-icon phone-btn" target="_blank">📞</a>' if phone else '<span class="btn-icon" style="opacity:0.3;cursor:not-allowed">📞</span>'
        action_li = f'<a href="{li}" class="btn-icon li-btn" target="_blank">💼</a>' if li else '<span class="btn-icon" style="opacity:0.3;cursor:not-allowed">💼</span>'
        sector_b = f'<span class="sector-badge">{esc(l.get("sector",""))}</span>' if l.get('sector') else ''
        source_b = f'<span class="source-badge">{esc(l.get("source",""))}</span>' if l.get('source') else ''
        intel_type = esc(l.get('intel_type', 'Intel'))
        what_means = esc(re.sub(r'<[^>]+>', '', l.get('what_it_means') or '')[:60])
        priority_dot = '<span class="priority-dot high"></span>' if l.get('priority') == 'high' else '<span class="priority-dot normal"></span>'
        return f'<tr><td>{priority_dot}<span class="score {sc}" style="margin-left:6px">{sv if sv is not None else "—"}</span></td><td><div class="company-cell"><span class="company-name">{esc(l.get("company",""))}</span><span class="intel-type"><span>{intel_type}</span>{what_means}</span></div></td><td><div class="company-cell"><span style="font-weight:600;font-size:0.83rem">{esc(l.get("hiring_manager") or "—")}</span><span style="font-size:0.72rem;color:var(--text2)">{esc(l.get("hiring_manager_title") or "")}</span></div></td><td><div class="contact-badges">{email_badge}{phone_badge}{li_badge}</div></td><td>{sector_b}</td><td>{source_b}</td><td><div class="action-btns">{action_email}{action_phone}{action_li}</div></td></tr>'

    rows_html = ''.join(render_row(l) for l in leads)
    leads_json = _json.dumps(leads)

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Lead Command | Lead Group SEQ</title>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
:root{{--bg:#0d1117;--bg2:#161b22;--bg3:#21262d;--border:#30363d;--cyan:#58a6ff;--green:#3fb950;--orange:#f0883e;--red:#f85149;--purple:#a371f7;--text:#c9d1d9;--text2:#8b949e;--text3:#484f58;--pink:#db61a2;}}
body{{font-family:'Space Grotesk',sans-serif;background:var(--bg);color:var(--text);min-height:100vh}}
a{{text-decoration:none;color:inherit}}
.header{{background:linear-gradient(135deg,var(--bg2),var(--bg3));border-bottom:1px solid var(--border);padding:18px 30px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:100;}}
.header-left{{display:flex;align-items:center;gap:20px}}
.logo{{font-size:1.35rem;font-weight:700;color:var(--cyan)}}
.logo span{{color:var(--orange)}}
.badge-live{{background:linear-gradient(135deg,var(--orange),var(--red));color:#fff;font-size:0.65rem;font-weight:700;padding:4px 12px;border-radius:20px;letter-spacing:1px;}}
.day-badge{{background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:8px 16px;font-size:0.8rem;color:var(--text2);}}
.day-badge strong{{color:var(--cyan)}}
.countdown{{background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:8px 16px;font-size:0.8rem;display:flex;align-items:center;gap:6px;}}
.countdown strong{{color:var(--green)}}
.main{{padding:24px 30px;max-width:1700px;margin:0 auto}}
.stats-row{{display:grid;grid-template-columns:repeat(6,1fr);gap:12px;margin-bottom:24px;}}
.stat-card{{background:var(--bg2);border:1px solid var(--border);border-radius:12px;padding:18px;position:relative;overflow:hidden;}}
.stat-card::before{{content:'';position:absolute;top:0;left:0;width:100%;height:3px;}}
.stat-card.cyan::before{{background:var(--cyan)}}
.stat-card.green::before{{background:var(--green)}}
.stat-card.orange::before{{background:var(--orange)}}
.stat-card.purple::before{{background:var(--purple)}}
.stat-card.red::before{{background:var(--red)}}
.stat-card.pink::before{{background:var(--pink)}}
.stat-value{{font-size:2rem;font-weight:700;margin-bottom:4px}}
.stat-card.cyan .stat-value{{color:var(--cyan)}}
.stat-card.green .stat-value{{color:var(--green)}}
.stat-card.orange .stat-value{{color:var(--orange)}}
.stat-card.purple .stat-value{{color:var(--purple)}}
.stat-card.red .stat-value{{color:var(--red)}}
.stat-card.pink .stat-value{{color:var(--pink)}}
.stat-label{{font-size:0.72rem;color:var(--text2);text-transform:uppercase;letter-spacing:1px}}
.stat-sub{{font-size:0.7rem;color:var(--text3);margin-top:4px}}
.layout{{display:grid;grid-template-columns:1fr 340px;gap:20px}}
.panel{{background:var(--bg2);border:1px solid var(--border);border-radius:12px;overflow:hidden;}}
.panel-header{{padding:14px 20px;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;}}
.panel-title{{font-size:0.95rem;font-weight:600;display:flex;align-items:center;gap:10px}}
.panel-title .icon{{font-size:1.1rem}}
.filter-bar{{padding:12px 20px;border-bottom:1px solid var(--border);display:flex;gap:10px;align-items:center;flex-wrap:wrap;}}
.filter-bar label{{font-size:0.75rem;color:var(--text2);text-transform:uppercase;letter-spacing:0.5px}}
select,input{{background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:7px 12px;border-radius:7px;font-size:0.82rem;font-family:'Space Grotesk',sans-serif;outline:none;}}
select:focus,input:focus{{border-color:var(--cyan)}}
select{{cursor:pointer}}
.search-input{{flex:1;min-width:180px}}
.table-wrap{{overflow-x:auto}}
table{{width:100%;border-collapse:collapse;font-size:0.82rem}}
thead th{{padding:11px 14px;text-align:left;font-size:0.72rem;text-transform:uppercase;letter-spacing:0.8px;color:var(--text2);border-bottom:1px solid var(--border);background:var(--bg);white-space:nowrap;cursor:pointer;user-select:none;}}
thead th:hover{{color:var(--text)}}
thead th .sort-icon{{margin-left:4px;opacity:0.4;font-size:0.65rem}}
thead th.sorted .sort-icon{{opacity:1;color:var(--cyan)}}
tbody tr{{border-bottom:1px solid var(--border);transition:background 0.15s}}
tbody tr:hover{{background:var(--bg3)}}
td{{padding:11px 14px;vertical-align:middle}}
.score{{font-weight:700;font-family:'JetBrains Mono',monospace;font-size:0.82rem;padding:3px 9px;border-radius:6px;display:inline-block;min-width:36px;text-align:center;}}
.score.hot{{background:rgba(63,185,80,0.15);color:var(--green)}}
.score.warm{{background:rgba(88,166,255,0.15);color:var(--cyan)}}
.score.cool{{background:rgba(240,136,62,0.15);color:var(--orange)}}
.score.cold{{background:rgba(248,81,73,0.15);color:var(--red)}}
.company-cell{{display:flex;flex-direction:column;gap:2px}}
.company-name{{font-weight:600;color:var(--text);white-space:nowrap}}
.intel-type{{font-size:0.72rem;color:var(--text2);white-space:nowrap}}
.intel-type span{{background:var(--bg3);padding:1px 7px;border-radius:10px;font-size:0.68rem;margin-right:4px;}}
.contact-badges{{display:flex;gap:4px;flex-wrap:wrap}}
.badge-mini{{font-size:0.65rem;padding:2px 8px;border-radius:10px;font-weight:600;}}
.badge-mini.email{{background:rgba(88,166,255,0.15);color:var(--cyan)}}
.badge-mini.phone{{background:rgba(63,185,80,0.15);color:var(--green)}}
.badge-mini.li{{background:rgba(163,113,247,0.15);color:var(--purple)}}
.badge-mini.missing{{background:rgba(72,79,88,0.3);color:var(--text3)}}
.action-btns{{display:flex;gap:6px}}
.btn-icon{{width:30px;height:30px;border-radius:7px;border:1px solid var(--border);background:var(--bg3);color:var(--text2);cursor:pointer;font-size:0.8rem;display:flex;align-items:center;justify-content:center;transition:all 0.2s;text-decoration:none;}}
.btn-icon:hover{{transform:translateY(-1px)}}
.btn-icon.email-btn:hover{{border-color:var(--cyan);color:var(--cyan);background:rgba(88,166,255,0.1)}}
.btn-icon.phone-btn:hover{{border-color:var(--green);color:var(--green);background:rgba(63,185,80,0.1)}}
.btn-icon.li-btn:hover{{border-color:var(--purple);color:var(--purple);background:rgba(163,113,247,0.1)}}
.source-badge{{font-size:0.68rem;padding:2px 8px;border-radius:10px;background:var(--bg3);color:var(--text2);white-space:nowrap;}}
.sector-badge{{font-size:0.68rem;padding:2px 8px;border-radius:10px;white-space:nowrap;background:rgba(88,166,255,0.08);color:var(--cyan);}}
.priority-dot{{width:8px;height:8px;border-radius:50%;display:inline-block;vertical-align:middle;margin-right:4px}}
.priority-dot.high{{background:var(--green);box-shadow:0 0 6px var(--green)}}
.priority-dot.normal{{background:var(--text3)}}
.sidebar{{display:flex;flex-direction:column;gap:16px}}
.top5-list{{padding:0}}
.top5-item{{padding:13px 18px;border-bottom:1px solid var(--border);display:flex;align-items:flex-start;gap:12px;transition:background 0.15s;}}
.top5-item:last-child{{border-bottom:none}}
.top5-item:hover{{background:var(--bg3)}}
.top5-rank{{font-size:1rem;font-weight:700;font-family:'JetBrains Mono',monospace;color:var(--text3);min-width:24px;text-align:center;margin-top:2px;}}
.top5-rank.r1{{color:var(--green)}}
.top5-rank.r2{{color:var(--cyan)}}
.top5-rank.r3{{color:var(--orange)}}
.top5-content{{flex:1}}
.top5-company{{font-weight:600;font-size:0.85rem;margin-bottom:3px}}
.top5-intel{{font-size:0.72rem;color:var(--text2);line-height:1.4}}
.top5-score{{margin-left:auto;font-family:'JetBrains Mono',monospace;font-weight:700;font-size:0.85rem}}
.sector-list{{padding:14px 18px;display:flex;flex-direction:column;gap:10px}}
.sector-item{{display:flex;flex-direction:column;gap:4px}}
.sector-row{{display:flex;justify-content:space-between;align-items:center;font-size:0.78rem}}
.sector-name{{color:var(--text2)}}
.sector-count{{font-weight:600;color:var(--text)}}
.sector-bar-bg{{height:5px;background:var(--bg);border-radius:10px;overflow:hidden}}
.sector-bar{{height:100%;background:var(--cyan);border-radius:10px}}
.coverage-list{{padding:14px 18px;display:flex;flex-direction:column;gap:10px}}
.coverage-item{{display:flex;justify-content:space-between;align-items:center;font-size:0.8rem}}
.coverage-label{{color:var(--text2);display:flex;align-items:center;gap:6px}}
.coverage-value{{font-weight:700}}
.coverage-value.yes{{color:var(--green)}}
.coverage-value.no{{color:var(--text3)}}
.empty-state{{padding:60px 20px;text-align:center;color:var(--text3);display:none}}
.empty-state .icon{{font-size:2.5rem;margin-bottom:12px}}
.back-link{{display:inline-flex;align-items:center;gap:6px;color:var(--text2);font-size:0.82rem;padding:6px 12px;background:var(--bg3);border:1px solid var(--border);border-radius:8px;transition:all 0.2s;}}
.back-link:hover{{color:var(--cyan);border-color:var(--cyan)}}
::-webkit-scrollbar{{width:6px;height:6px}}
::-webkit-scrollbar-track{{background:var(--bg)}}
::-webkit-scrollbar-thumb{{background:var(--border);border-radius:3px}}
::-webkit-scrollbar-thumb:hover{{background:var(--text3)}}
</style>
</head>
<body>

<div class="header">
  <div class="header-left">
    <div class="logo">Lead <span>Command</span></div>
    <span class="badge-live">LIVE</span>
    <a href="/" class="back-link">← CRM</a>
  </div>
  <div class="header-right">
    <div class="day-badge" id="dayBadge"></div>
    <div class="countdown"><span>⏱</span><span id="countdown"></span><strong>to Day 1</strong></div>
  </div>
</div>

<div class="main">
  <div class="stats-row">
    <div class="stat-card cyan"><div class="stat-value">{total_leads}</div><div class="stat-label">Total Leads</div><div class="stat-sub">all sources</div></div>
    <div class="stat-card green"><div class="stat-value">{active_leads}</div><div class="stat-label">Active</div><div class="stat-sub">open intel</div></div>
    <div class="stat-card orange"><div class="stat-value">{hot_leads}</div><div class="stat-label">🔥 Hot 70+</div><div class="stat-sub">priority targets</div></div>
    <div class="stat-card purple"><div class="stat-value">{warm_leads}</div><div class="stat-label">Warm 50-69</div><div class="stat-sub">good potential</div></div>
    <div class="stat-card pink"><div class="stat-value">{with_email}</div><div class="stat-label">📧 Email Ready</div><div class="stat-sub">can contact now</div></div>
    <div class="stat-card red"><div class="stat-value">{with_phone}</div><div class="stat-label">📞 Phone Ready</div><div class="stat-sub">can call directly</div></div>
  </div>

  <div class="layout">
    <div class="panel">
      <div class="panel-header">
        <div class="panel-title"><span class="icon">🎯</span> All Leads — Ranked by Score <span style="font-size:0.72rem;color:var(--text3);font-weight:400;margin-left:8px" id="visibleCount"></span></div>
      </div>
      <div class="filter-bar">
        <label>Search</label>
        <input type="text" id="searchInput" class="search-input" placeholder="Company, role, or contact..." oninput="applyFilters()">
        <label>Sector</label>
        <select id="filterSector" onchange="applyFilters()"><option value="">All</option>{sectors_opts}</select>
        <label>Score</label>
        <select id="filterScore" onchange="applyFilters()"><option value="">All</option><option value="hot">🔥 Hot 70+</option><option value="warm">Warm 50-69</option><option value="cool">Cool 30-49</option><option value="cold">Cold &lt;30</option></select>
        <label>Contact</label>
        <select id="filterContact" onchange="applyFilters()"><option value="">All</option><option value="full">📧+📞+LI</option><option value="email">📧 Email Only</option><option value="none">❌ No Contact</option></select>
        <label>Source</label>
        <select id="filterSource" onchange="applyFilters()"><option value="">All</option>{sources_opts}</select>
      </div>
      <div class="table-wrap">
        <table id="leadTable">
          <thead>
            <tr>
              <th data-sort="lead_score" onclick="sortTable('lead_score')">Score <span class="sort-icon">↕</span></th>
              <th data-sort="company" onclick="sortTable('company')">Company / Intel <span class="sort-icon">↕</span></th>
              <th data-sort="hiring_manager" onclick="sortTable('hiring_manager')">Hiring Manager <span class="sort-icon">↕</span></th>
              <th data-sort="contact" onclick="sortTable('contact')">Contacts <span class="sort-icon">↕</span></th>
              <th data-sort="sector" onclick="sortTable('sector')">Sector <span class="sort-icon">↕</span></th>
              <th data-sort="source" onclick="sortTable('source')">Source <span class="sort-icon">↕</span></th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody id="leadBody">{rows_html}</tbody>
        </table>
      </div>
      <div class="empty-state" id="emptyState"><div class="icon">🔍</div><p>No leads match your filters</p></div>
    </div>

    <div class="sidebar">
      <div class="panel">
        <div class="panel-header"><div class="panel-title"><span class="icon">🚀</span> Today's Top 5</div></div>
        <div class="top5-list">{top5_html}</div>
      </div>
      <div class="panel">
        <div class="panel-header"><div class="panel-title"><span class="icon">📊</span> Sector Breakdown</div></div>
        <div class="sector-list">{sector_html}</div>
      </div>
      <div class="panel">
        <div class="panel-header"><div class="panel-title"><span class="icon">📞</span> Contact Coverage</div></div>
        <div class="coverage-list">{coverage_html}</div>
      </div>
    </div>
  </div>
</div>

<script>
const ALL_LEADS = {leads_json};

let sortKey = 'lead_score';
let sortDir = -1;
const filters = {{search:'',sector:'',score:'',contact:'',source:''}};

function scClass(s){{
  s = s || 0;
  return s >= 70 ? 'hot' : s >= 50 ? 'warm' : s >= 30 ? 'cool' : 'cold';
}}

function escHtml(s){{ return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }}

function renderRow(l){{
  const sc = scClass(l.lead_score);
  const sv = l.lead_score;
  const hasEmail = !!l.hirer_email;
  const hasPhone = !!l.phone;
  const hasLi = !!l.hirer_linkedin;
  const email = escHtml(l.hirer_email);
  const phone = escHtml(l.phone);
  const li = escHtml(l.hirer_linkedin);
  const emailBadge = hasEmail ? '<span class="badge-mini email">📧</span>' : '<span class="badge-mini missing">📧 —</span>';
  const phoneBadge = hasPhone ? '<span class="badge-mini phone">📞</span>' : '<span class="badge-mini missing">📞</span>';
  const liBadge = hasLi ? '<span class="badge-mini li">💼</span>' : '<span class="badge-mini missing">💼 —</span>';
  const emailHref = hasEmail ? `mailto:${{email}}?subject=Construction+Recruitment+Partnership+—+${{escHtml(l.company||'')}}` : '#';
  const phoneHref = hasPhone ? `tel:${{phone}}` : '#';
  const liHref = li || '#';
  const actionEmail = hasEmail ? `<a href="${{emailHref}}" class="btn-icon email-btn" target="_blank" title="Send email">📧</a>` : `<span class="btn-icon" style="opacity:0.3;cursor:not-allowed">📧</span>`;
  const actionPhone = hasPhone ? `<a href="${{phoneHref}}" class="btn-icon phone-btn" target="_blank" title="Call">📞</a>` : `<span class="btn-icon" style="opacity:0.3;cursor:not-allowed">📞</span>`;
  const actionLi = hasLi ? `<a href="${{liHref}}" class="btn-icon li-btn" target="_blank" title="LinkedIn">💼</a>` : `<span class="btn-icon" style="opacity:0.3;cursor:not-allowed">💼</span>`;
  const sectorBadge = l.sector ? `<span class="sector-badge">${{escHtml(l.sector)}}</span>` : '';
  const sourceBadge = l.source ? `<span class="source-badge">${{escHtml(l.source)}}</span>` : '';
  const intelType = escHtml(l.intel_type || 'Intel');
  const whatMeans = escHtml((l.what_it_means||'').replace(/<[^>]+>/g,'').substring(0,60));
  const company = escHtml(l.company || '');
  const manager = escHtml(l.hiring_manager || '');
  const title = escHtml(l.hiring_manager_title || '');
  const priorityDot = l.priority === 'high' ? '<span class="priority-dot high"></span>' : '<span class="priority-dot normal"></span>';
  return `<tr><td>${{priorityDot}}<span class="score ${{sc}}" style="margin-left:6px">${{sv!=null?sv:'—'}}</span></td><td><div class="company-cell"><span class="company-name">${{company}}</span><span class="intel-type"><span>${{intelType}}</span>${{whatMeans}}</span></div></td><td><div class="company-cell"><span style="font-weight:600;font-size:0.83rem">${{manager||'—'}}</span><span style="font-size:0.72rem;color:var(--text2)">${{title}}</span></div></td><td><div class="contact-badges">${{emailBadge}}${{phoneBadge}}${{liBadge}}</div></td><td>${{sectorBadge}}</td><td>${{sourceBadge}}</td><td><div class="action-btns">${{actionEmail}}${{actionPhone}}${{actionLi}}</div></td></tr>`;
}}

function getFiltered() {{
  const f = {{
    search: document.getElementById('searchInput').value.toLowerCase(),
    sector: document.getElementById('filterSector').value,
    score: document.getElementById('filterScore').value,
    contact: document.getElementById('filterContact').value,
    source: document.getElementById('filterSource').value,
  }};
  return ALL_LEADS.filter(l => {{
    if (f.search && !(l.company||'').toLowerCase().includes(f.search) && !(l.hiring_manager||'').toLowerCase().includes(f.search) && !(l.what_it_means||'').toLowerCase().includes(f.search)) return false;
    if (f.sector && l.sector !== f.sector) return false;
    if (f.score) {{
      const s = l.lead_score || 0;
      if (f.score==='hot'&&s<70) return false;
      if (f.score==='warm'&&(s<50||s>=70)) return false;
      if (f.score==='cool'&&(s<30||s>=50)) return false;
      if (f.score==='cold'&&s>=30) return false;
    }}
    if (f.contact) {{
      const e=!!l.hirer_email,p=!!l.phone,i=!!l.hirer_linkedin;
      if (f.contact==='full'&&!(e&&p&&i)) return false;
      if (f.contact==='email'&&!e) return false;
      if (f.contact==='none'&&(e||p||i)) return false;
    }}
    if (f.source && l.source !== f.source) return false;
    return true;
  }});
}}

function applyFilters() {{
  const filtered = getFiltered();
  const count = document.getElementById('visibleCount');
  const tbody = document.getElementById('leadBody');
  const empty = document.getElementById('emptyState');
  if (!filtered.length) {{ tbody.innerHTML=''; empty.style.display='block'; count.textContent=''; return; }}
  empty.style.display='none';
  count.textContent = filtered.length + ' of ' + ALL_LEADS.length;
  tbody.innerHTML = filtered.map(renderRow).join('');
}}

function sortTable(key) {{
  if (sortKey === key) sortDir *= -1;
  else {{ sortKey = key; sortDir = -1; }}
  document.querySelectorAll('thead th').forEach(th => th.classList.remove('sorted'));
  const th = document.querySelector('th[data-sort="' + key + '"]');
  if (th) {{ th.classList.add('sorted'); th.querySelector('.sort-icon').textContent = sortDir === -1 ? '↓' : '↑'; }}
  const filtered = getFiltered();
  filtered.sort((a,b) => {{
    let va=a[key]??'',vb=b[key]??'';
    if (key==='lead_score') {{ va=a.lead_score??0; vb=b.lead_score??0; }}
    if (key==='contact') {{ va=(a.hirer_email?1:0)+(a.phone?1:0)+(a.hirer_linkedin?1:0); vb=(b.hirer_email?1:0)+(b.phone?1:0)+(b.hirer_linkedin?1:0); }}
    if (typeof va==='string') return sortDir*va.localeCompare(vb);
    return sortDir*(va-vb);
  }});
  const count = document.getElementById('visibleCount');
  const tbody = document.getElementById('leadBody');
  const empty = document.getElementById('emptyState');
  if (!filtered.length) {{ tbody.innerHTML=''; empty.style.display='block'; count.textContent=''; return; }}
  empty.style.display='none';
  count.textContent = filtered.length + ' of ' + ALL_LEADS.length;
  tbody.innerHTML = filtered.map(renderRow).join('');
}}

// Countdown
const day1 = new Date('2026-05-04');
function updateCountdown(){{
  const now = new Date();
  const diff = day1 - now;
  if (diff <= 0) {{ document.getElementById('countdown').textContent = '🚀 DAY 1!'; return; }}
  const d=Math.floor(diff/86400000),h=Math.floor((diff%86400000)/3600000),m=Math.floor((diff%3600000)/60000);
  document.getElementById('countdown').textContent = d+'d '+h+'h '+m+'m';
}}
updateCountdown();
setInterval(updateCountdown, 60000);
const days=['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'];
const months=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
const now=new Date();
document.getElementById('dayBadge').innerHTML='<strong>'+days[now.getDay()]+'</strong> · '+now.getDate()+' '+months[now.getMonth()];

// Init sorted by score desc
sortTable('lead_score');
</script>
</body>
</html>'''

    return html, 200, {'Content-Type': 'text/html'}

@app.route('/')
def dashboard():
    """Dashboard - overview"""
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute('SELECT COUNT(*) as count FROM companies')
    company_count = cursor.fetchone()['count']
    
    cursor.execute('SELECT COUNT(*) as count FROM decision_makers')
    dm_count = cursor.fetchone()['count']
    
    cursor.execute('SELECT COUNT(*) as count FROM decision_makers WHERE relationship_score >= 4')
    warm_count = cursor.fetchone()['count']
    
    cursor.execute('SELECT COUNT(*) as count FROM candidates')
    candidate_count = cursor.fetchone()['count']
    
    cursor.execute('SELECT COUNT(*) as count FROM deals')
    deal_count = cursor.fetchone()['count']
    
    cursor.execute('SELECT COUNT(*) as count FROM deals WHERE stage = "Placement"')
    placements_count = cursor.fetchone()['count']
    
    from datetime import datetime, timedelta
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    week_commencing = monday.strftime('Week Commencing %d %B')
    
    db.close()
    
    return render_template('dashboard_new.html', 
                         companies=company_count, 
                         dms=dm_count, 
                         warm=warm_count,
                         candidates=candidate_count,
                         deals=deal_count,
                         candidates_count=candidate_count,
                         contacts_count=dm_count,
                         conversations_count=warm_count,
                         placements_count=placements_count,
                         today=week_commencing)

@app.route('/companies')
def companies_list():
    """List all companies"""
    db = get_db()
    cursor = db.cursor()
    
    search = request.args.get('search', '')
    
    if search:
        cursor.execute('''SELECT c.*, 
            (SELECT COUNT(*) FROM contacts ct WHERE ct.company_id = c.id) as contact_count
            FROM companies c WHERE c.name LIKE ? ORDER BY c.name''', 
                      (f'%{search}%',))
    else:
        cursor.execute('''SELECT c.*, 
            (SELECT COUNT(*) FROM contacts ct WHERE ct.company_id = c.id) as contact_count
            FROM companies c ORDER BY c.name''')
    
    companies = cursor.fetchall()
    db.close()
    
    return render_template('companies.html', companies=companies, search=search)

@app.route('/company/<int:company_id>')
def company_detail(company_id):
    """Company detail + decision makers"""
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute('SELECT * FROM companies WHERE id = ?', (company_id,))
    company = cursor.fetchone()
    
    if not company:
        return redirect(url_for('companies_list'))
    
    cursor.execute('SELECT * FROM decision_makers WHERE company_id = ? ORDER BY relationship_score DESC', 
                   (company_id,))
    dms = cursor.fetchall()
    
    cursor.execute('SELECT * FROM projects WHERE company_id = ? ORDER BY name', (company_id,))
    projects = cursor.fetchall()
    
    db.close()
    
    return render_template('company_detail.html', company=company, dms=dms, projects=projects)

@app.route('/api/company', methods=['POST'])
def api_add_company():
    """API: Add/edit company"""
    data = request.json
    db = get_db()
    cursor = db.cursor()
    
    try:
        if 'id' in data and data['id']:
            # Update
            cursor.execute('''
                UPDATE companies 
                SET name=?, tier=?, sector=?, location=?, 
                    active_projects=?, upcoming_projects=?, competitors=?, notes=?,
                    updated_at=CURRENT_TIMESTAMP
                WHERE id=?
            ''', (data.get('name'), data.get('tier'), data.get('sector'),
                  data.get('location'), data.get('active_projects'),
                  data.get('upcoming_projects'), data.get('competitors'),
                  data.get('notes'), data.get('id')))
        else:
            # Add
            cursor.execute('''
                INSERT INTO companies 
                (name, tier, sector, location, active_projects, upcoming_projects, competitors, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (data.get('name'), data.get('tier'), data.get('sector'),
                  data.get('location'), data.get('active_projects'),
                  data.get('upcoming_projects'), data.get('competitors'),
                  data.get('notes')))
        
        db.commit()
        db.close()
        return jsonify({'status': 'success'})
    except Exception as e:
        db.close()
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/api/dm/<int:dm_id>')
def api_get_dm(dm_id):
    """API: Get decision maker by ID"""
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM decision_makers WHERE id = ?', (dm_id,))
    dm = cursor.fetchone()
    db.close()
    if dm:
        return jsonify(dict(dm))
    return jsonify({'error': 'Not found'}), 404

@app.route('/api/dm', methods=['POST'])
def api_add_dm():
    """API: Add/edit decision maker"""
    data = request.json
    db = get_db()
    cursor = db.cursor()
    
    try:
        if 'id' in data and data['id']:
            # Update
            cursor.execute('''
                UPDATE decision_makers 
                SET name=?, title=?, role=?, phone=?, email=?, linkedin=?,
                    hiring_signals=?, relationship_score=?, last_contact=?,
                    next_action=?, notes=?, updated_at=CURRENT_TIMESTAMP
                WHERE id=?
            ''', (data.get('name'), data.get('title'), data.get('role'),
                  data.get('phone'), data.get('email'), data.get('linkedin'),
                  data.get('hiring_signals'), data.get('relationship_score'),
                  data.get('last_contact'), data.get('next_action'),
                  data.get('notes'), data.get('id')))
        else:
            # Add
            cursor.execute('''
                INSERT INTO decision_makers 
                (company_id, name, title, role, phone, email, linkedin,
                 hiring_signals, relationship_score, last_contact, next_action, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (data.get('company_id'), data.get('name'), data.get('title'),
                  data.get('role'), data.get('phone'), data.get('email'),
                  data.get('linkedin'), data.get('hiring_signals'),
                  data.get('relationship_score'), data.get('last_contact'),
                  data.get('next_action'), data.get('notes')))
        
        db.commit()
        db.close()
        return jsonify({'status': 'success'})
    except Exception as e:
        db.close()
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/candidates')
def candidates_list():
    """List all candidates"""
    db = get_db()
    cursor = db.cursor()
    
    search = request.args.get('search', '')
    
    if search:
        cursor.execute('SELECT * FROM candidates WHERE name LIKE ? OR current_company LIKE ? ORDER BY name', 
                      (f'%{search}%', f'%{search}%'))
    else:
        cursor.execute('SELECT * FROM candidates ORDER BY name')
    
    candidates = cursor.fetchall()
    
    # Get unique locations for filter dropdown
    cursor.execute('SELECT DISTINCT location FROM candidates WHERE location IS NOT NULL AND location != "" ORDER BY location')
    locations = [row[0] for row in cursor.fetchall()]
    
    # Build company_id lookup for clickable company links
    company_lookup = {}
    for c in candidates:
        if c['current_company']:
            cursor.execute('SELECT id FROM companies WHERE name = ?', (c['current_company'],))
            row = cursor.fetchone()
            company_lookup[c['id']] = row['id'] if row else None
    
    db.close()
    
    return render_template('candidates.html', candidates=candidates, search=search, locations=locations, company_lookup=company_lookup)

@app.route('/candidates/<int:candidate_id>/deep')
def candidate_deep(candidate_id):
    """Deep candidate profile with intelligence"""
    db = get_db()
    cursor = db.cursor()
    
    # Get candidate basic info
    cursor.execute('SELECT * FROM candidates WHERE id = ?', (candidate_id,))
    candidate = cursor.fetchone()
    
    if not candidate:
        db.close()
        return redirect(url_for('candidates_list'))
    
    # Convert sqlite3.Row to dict for easier access
    candidate = dict(candidate)
    
    # Get work history
    cursor.execute('''
        SELECT * FROM candidate_projects 
        WHERE candidate_id = ? 
        ORDER BY start_date DESC
    ''', (candidate_id,))
    work_history = cursor.fetchall()
    
    # Get all project intelligence for matching
    cursor.execute('''
        SELECT pi.*, p.name as project_name, p.address, c.name as company_name
        FROM project_intelligence pi
        JOIN projects p ON pi.project_id = p.id
        LEFT JOIN companies c ON p.company_id = c.id
    ''')
    projects_intel = cursor.fetchall()
    
    # Build match scores for projects
    candidate_tags = (candidate.get('tags') or '').split(',') if candidate.get('tags') else []
    candidate_signals = (candidate.get('signals') or '').split(',') if candidate.get('signals') else []
    candidate_location_pref = candidate.get('aspirations_location') or candidate.get('location', '')
    
    matches = []
    for pi in projects_intel:
        score = 5  # base score
        reasons = []
        
        # Tag matching
        project_tags = (pi.get('key_skills') or '').split(',') if pi.get('key_skills') else []
        if project_tags and candidate_tags:
            matching = set(t.strip().lower() for t in project_tags) & set(t.strip().lower() for t in candidate_tags if t.strip())
            if matching:
                score += 2
                reasons.append(f"Matches skills: {', '.join(matching)}")
        
        # Project type matching
        if pi.get('project_type') and candidate.get('specialism'):
            if pi.get('project_type').lower() in candidate.get('specialism', '').lower():
                score += 2
                reasons.append(f"Specialism aligned: {candidate.get('specialism')}")
        
        # Location preference
        if pi.get('what_makes_interesting') and candidate_location_pref:
            if candidate_location_pref.lower() in pi.get('what_makes_interesting', '').lower():
                score += 1
        
        # Pace matching
        if pi.get('pace') and candidate.get('tags'):
            if pi.get('pace').lower() in candidate.get('tags', '').lower():
                score += 1
                reasons.append(f"Pace preference match")
        
        matches.append({
            'project': pi,
            'score': min(score, 10),
            'reasons': reasons
        })
    
    # Sort by score
    matches.sort(key=lambda x: x['score'], reverse=True)
    best_matches = matches[:5]
    
    # Get companies for lookup
    cursor.execute('SELECT id, name FROM companies ORDER BY name')
    companies = {c['id']: c['name'] for c in cursor.fetchall()}
    
    db.close()
    
    return render_template('candidate_deep.html', 
                          candidate=candidate, 
                          work_history=work_history,
                          best_matches=best_matches,
                          companies=companies)

@app.route('/candidates/add', methods=['GET', 'POST'])
def candidate_add():
    """Add or edit candidate with full intelligence"""
    db = get_db()
    cursor = db.cursor()
    
    if request.method == 'POST':
        # Extract form data
        data = {
            'name': request.form.get('name'),
            'email': request.form.get('email'),
            'phone': request.form.get('phone'),
            'linkedin': request.form.get('linkedin'),
            'current_company': request.form.get('current_company'),
            'title': request.form.get('title'),
            'specialism': request.form.get('specialism'),
            'years_experience': request.form.get('years_experience'),
            'salary_band': request.form.get('salary_band'),
            'location': request.form.get('location'),
            'availability': request.form.get('availability'),
            'status': request.form.get('status', 'Prospect'),
            'tags': request.form.get('tags'),
            'preferences_loved': request.form.get('preferences_loved'),
            'preferences_hated': request.form.get('preferences_hated'),
            'dealbreakers': request.form.get('dealbreakers'),
            'aspirations_role': request.form.get('aspirations_role'),
            'aspirations_salary': request.form.get('aspirations_salary'),
            'aspirations_location': request.form.get('aspirations_location'),
            'signals': request.form.get('signals'),
            'notes': request.form.get('notes'),
        }
        
        # Insert new candidate
        cursor.execute('''
            INSERT INTO candidates (
                name, email, phone, linkedin, current_company, title, specialism,
                years_experience, salary_band, location, availability, status,
                tags, preferences_loved, preferences_hated, dealbreakers,
                aspirations_role, aspirations_salary, aspirations_location,
                signals, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (data['name'], data['email'], data['phone'], data['linkedin'],
              data['current_company'], data['title'], data['specialism'],
              data['years_experience'], data['salary_band'], data['location'],
              data['availability'], data['status'], data['tags'],
              data['preferences_loved'], data['preferences_hated'], data['dealbreakers'],
              data['aspirations_role'], data['aspirations_salary'], data['aspirations_location'],
              data['signals'], data['notes']))
        
        candidate_id = cursor.lastrowid
        
        # Add work history entries
        project_names = request.form.getlist('project_name[]')
        project_companies = request.form.getlist('project_company[]')
        project_roles = request.form.getlist('project_role[]')
        project_starts = request.form.getlist('project_start[]')
        project_ends = request.form.getlist('project_end[]')
        
        for i in range(len(project_names)):
            if project_names[i]:
                cursor.execute('''
                    INSERT INTO candidate_projects 
                    (candidate_id, project_name, company, role, start_date, end_date)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (candidate_id, project_names[i], project_companies[i] if i < len(project_companies) else '',
                      project_roles[i] if i < len(project_roles) else '',
                      project_starts[i] if i < len(project_starts) else '',
                      project_ends[i] if i < len(project_ends) else ''))
        
        db.commit()
        db.close()
        return redirect(url_for('candidate_deep', candidate_id=candidate_id))
    
    # GET request - show form
    cursor.execute('SELECT id, name FROM companies ORDER BY name')
    companies = cursor.fetchall()
    db.close()
    
    return render_template('candidate_add.html', companies=companies, candidate=None)

@app.route('/candidates/<int:candidate_id>/edit', methods=['GET', 'POST'])
def candidate_edit(candidate_id):
    """Edit existing candidate"""
    db = get_db()
    cursor = db.cursor()
    
    if request.method == 'POST':
        cursor.execute('''
            UPDATE candidates SET
                name = ?, email = ?, phone = ?, linkedin = ?,
                current_company = ?, title = ?, specialism = ?,
                years_experience = ?, salary_band = ?, location = ?,
                availability = ?, status = ?, tags = ?,
                preferences_loved = ?, preferences_hated = ?, dealbreakers = ?,
                aspirations_role = ?, aspirations_salary = ?, aspirations_location = ?,
                signals = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (
            request.form.get('name'), request.form.get('email'), request.form.get('phone'), request.form.get('linkedin'),
            request.form.get('current_company'), request.form.get('title'), request.form.get('specialism'),
            request.form.get('years_experience'), request.form.get('salary_band'), request.form.get('location'),
            request.form.get('availability'), request.form.get('status'), request.form.get('tags'),
            request.form.get('preferences_loved'), request.form.get('preferences_hated'), request.form.get('dealbreakers'),
            request.form.get('aspirations_role'), request.form.get('aspirations_salary'), request.form.get('aspirations_location'),
            request.form.get('signals'), request.form.get('notes'),
            candidate_id
        ))
        
        # Update work history - delete existing and re-add
        cursor.execute('DELETE FROM candidate_projects WHERE candidate_id = ?', (candidate_id,))
        
        project_names = request.form.getlist('project_name[]')
        project_companies = request.form.getlist('project_company[]')
        project_roles = request.form.getlist('project_role[]')
        project_starts = request.form.getlist('project_start[]')
        project_ends = request.form.getlist('project_end[]')
        
        for i in range(len(project_names)):
            if project_names[i]:
                cursor.execute('''
                    INSERT INTO candidate_projects 
                    (candidate_id, project_name, company, role, start_date, end_date)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (candidate_id, project_names[i], project_companies[i] if i < len(project_companies) else '',
                      project_roles[i] if i < len(project_roles) else '',
                      project_starts[i] if i < len(project_starts) else '',
                      project_ends[i] if i < len(project_ends) else ''))
        
        db.commit()
        db.close()
        return redirect(url_for('candidate_deep', candidate_id=candidate_id))
    
    # GET - show form with existing data
    cursor.execute('SELECT * FROM candidates WHERE id = ?', (candidate_id,))
    candidate = cursor.fetchone()
    
    cursor.execute('SELECT * FROM candidate_projects WHERE candidate_id = ? ORDER BY start_date DESC', (candidate_id,))
    work_history = cursor.fetchall()
    
    cursor.execute('SELECT id, name FROM companies ORDER BY name')
    companies = cursor.fetchall()
    
    db.close()
    
    return render_template('candidate_add.html', candidate=candidate, work_history=work_history, companies=companies)

@app.route('/project-intelligence')
def project_intelligence_list():
    """List all projects with intelligence"""
    db = get_db()
    cursor = db.cursor()
    
    # Get all projects with their intelligence
    cursor.execute('''
        SELECT p.*, c.name as company_name, pi.id as intel_id,
               pi.what_makes_interesting, pi.ideal_profile, pi.team_culture,
               pi.pace, pi.project_type
        FROM projects p
        LEFT JOIN companies c ON p.company_id = c.id
        LEFT JOIN project_intelligence pi ON p.id = pi.project_id
        ORDER BY p.name
    ''')
    projects = cursor.fetchall()
    
    # Get all candidates for match counts
    cursor.execute('SELECT id, name, status, tags, specialism FROM candidates WHERE status != "Placed"')
    candidates = cursor.fetchall()
    
    db.close()
    
    return render_template('project_intelligence_list.html', projects=projects, candidates=candidates)

@app.route('/project-intelligence/<int:project_id>')
def project_intelligence_detail(project_id):
    """Project intelligence detail with candidate matches"""
    db = get_db()
    cursor = db.cursor()
    
    # Get project with intel
    cursor.execute('''
        SELECT p.*, c.name as company_name, c.id as company_id, pi.*
        FROM projects p
        LEFT JOIN companies c ON p.company_id = c.id
        LEFT JOIN project_intelligence pi ON p.id = pi.project_id
        WHERE p.id = ?
    ''', (project_id,))
    project = cursor.fetchone()
    
    if not project:
        db.close()
        return redirect(url_for('project_intelligence_list'))
    
    # Convert to dict
    project = dict(project)
    
    # Get jobs for this project
    cursor.execute('''
        SELECT * FROM jobs WHERE project_id = ? OR company = ?
        ORDER BY created_at DESC
    ''', (project_id, project['company_name'] if project['company_name'] else ''))
    jobs = cursor.fetchall()
    
    # Get all active candidates for matching
    cursor.execute('''
        SELECT * FROM candidates WHERE status IN ('Prospect', 'Engaged')
    ''')
    candidates_raw = cursor.fetchall()
    candidates = [dict(c) for c in candidates_raw]
    
    # Build match scores
    project_type = project.get('project_type', '') or ''
    project_skills = (project.get('key_skills') or '').split(',') if project.get('key_skills') else []
    project_pace = project.get('pace', '') or ''
    project_culture = project.get('team_culture', '') or ''
    
    matches = []
    for c in candidates:
        score = 5
        reasons = []
        
        # Specialism matching
        if c.get('specialism') and project_type:
            if project_type.lower() in c.get('specialism', '').lower():
                score += 2
                reasons.append(f"Specialism: {c.get('specialism')}")
        
        # Tag matching
        candidate_tags = (c.get('tags') or '').split(',') if c.get('tags') else []
        if candidate_tags and project_skills:
            matching = set(t.strip().lower() for t in candidate_tags if t.strip()) & set(t.strip().lower() for t in project_skills if t.strip())
            if matching:
                score += 2
                reasons.append(f"Matches tags: {', '.join(matching)}")
        
        # Location preference
        if c.get('aspirations_location') and project.get('what_makes_interesting'):
            if c.get('aspirations_location').lower() in project.get('what_makes_interesting', '').lower():
                score += 1
        
        # Pace preference
        if project_pace and c.get('tags'):
            if project_pace.lower() in c.get('tags', '').lower():
                score += 1
                reasons.append("Pace match")
        
        if score > 5:  # Only include matches
            matches.append({
                'candidate': c,
                'score': min(score, 10),
                'reasons': reasons
            })
    
    matches.sort(key=lambda x: x['score'], reverse=True)
    
    db.close()
    
    return render_template('project_intelligence_detail.html', project=project, jobs=jobs, matches=matches)

@app.route('/project-intelligence/<int:project_id>/edit', methods=['GET', 'POST'])
def project_intelligence_edit(project_id):
    """Edit project intelligence"""
    db = get_db()
    cursor = db.cursor()
    
    if request.method == 'POST':
        # Upsert project intelligence
        cursor.execute('''
            INSERT OR REPLACE INTO project_intelligence (
                project_id, what_makes_interesting, ideal_profile, team_culture,
                manager_style, pace, project_type, key_skills, nice_to_have,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (
            project_id,
            request.form.get('what_makes_interesting'),
            request.form.get('ideal_profile'),
            request.form.get('team_culture'),
            request.form.get('manager_style'),
            request.form.get('pace'),
            request.form.get('project_type'),
            request.form.get('key_skills'),
            request.form.get('nice_to_have')
        ))
        
        db.commit()
        db.close()
        return redirect(url_for('project_intelligence_detail', project_id=project_id))
    
    # GET - show form
    cursor.execute('''
        SELECT p.*, pi.*
        FROM projects p
        LEFT JOIN project_intelligence pi ON p.id = pi.project_id
        WHERE p.id = ?
    ''', (project_id,))
    project = dict(cursor.fetchone())
    
    db.close()
    
    return render_template('project_intelligence_edit.html', project=project)

# ===== COMPANY INTELLIGENCE ROUTES =====
@app.route('/company-intelligence')
def company_intelligence_list():
    """List all companies with intelligence"""
    db = get_db()
    cursor = db.cursor()
    
    # Get all companies with their intelligence
    cursor.execute('''
        SELECT c.*, ci.id as intel_id,
               ci.project_types, ci.pace, ci.team_style, ci.client_relationship,
               ci.size_profile, ci.growth_culture, ci.what_they_value,
               ci.ideal_candidate_profile, ci.common_pitfalls, ci.notes
        FROM companies c
        LEFT JOIN company_intelligence ci ON c.id = ci.company_id
        WHERE c.name IS NOT NULL AND c.name != ''
        ORDER BY c.name
    ''')
    companies = cursor.fetchall()
    
    # Get all candidates for match counts
    cursor.execute('SELECT id, name, status, tags, specialism, aspirations_role, aspirations_salary FROM candidates WHERE status != "Placed"')
    candidates = cursor.fetchall()
    
    db.close()
    
    return render_template('company_intelligence_list.html', companies=companies, candidates=candidates)

@app.route('/company-intelligence/<int:company_id>')
def company_intelligence_detail(company_id):
    """Company intelligence detail with candidate matches"""
    db = get_db()
    cursor = db.cursor()
    
    # Get company with intel
    cursor.execute('''
        SELECT c.*, ci.*
        FROM companies c
        LEFT JOIN company_intelligence ci ON c.id = ci.company_id
        WHERE c.id = ?
    ''', (company_id,))
    company = cursor.fetchone()
    
    if not company:
        db.close()
        return redirect(url_for('company_intelligence_list'))
    
    # Convert to dict
    company = dict(company)
    
    # Get jobs for this company
    cursor.execute('''
        SELECT * FROM jobs 
        WHERE company = ? OR company_id = ?
        ORDER BY created_at DESC
    ''', (company['name'], company_id))
    jobs = cursor.fetchall()
    
    # Get all active candidates for matching
    cursor.execute('''
        SELECT * FROM candidates WHERE status IN ('Prospect', 'Engaged')
    ''')
    candidates_raw = cursor.fetchall()
    candidates = [dict(c) for c in candidates_raw]
    
    # Build match scores based on company intel
    company_types = (company.get('project_types') or '').split(',') if company.get('project_types') else []
    company_pace = company.get('pace', '') or ''
    company_style = company.get('team_style', '') or ''
    company_size = company.get('size_profile', '') or ''
    company_growth = company.get('growth_culture', '') or ''
    company_values = (company.get('what_they_value') or '').lower() if company.get('what_they_value') else ''
    ideal_profile = (company.get('ideal_candidate_profile') or '').lower() if company.get('ideal_candidate_profile') else ''
    
    matches = []
    for c in candidates:
        score = 5
        reasons = []
        
        # Specialism matching
        if c.get('specialism'):
            for ptype in company_types:
                if ptype.strip().lower() in c.get('specialism', '').lower():
                    score += 2
                    reasons.append(f"Specialism: {ptype.strip()}")
                    break
        
        # Pace preference matching
        if company_pace and c.get('tags'):
            if company_pace.lower() in c.get('tags', '').lower():
                score += 1
                reasons.append(f"Pace: {company_pace}")
        
        # Team style matching
        if company_style and c.get('tags'):
            if company_style.lower() in c.get('tags', '').lower():
                score += 1
                reasons.append(f"Team style: {company_style}")
        
        # Size profile matching (career stage)
        if company_size and c.get('aspirations_role'):
            # Boutique/sme = wants broad role, corporate = wants structure
            if ('boutique' in company_size.lower() or 'sme' in company_size.lower()) and 'broad' in c.get('aspirations_role', '').lower():
                score += 1
                reasons.append("Career stage: boutique")
            elif 'corporate' in company_size.lower() or 'large' in company_size.lower():
                if 'structure' in c.get('aspirations_role', '').lower() or 'senior' in c.get('aspirations_role', '').lower():
                    score += 1
                    reasons.append("Career stage: corporate")
        
        # Growth culture matching
        if company_growth and c.get('aspirations_role'):
            if 'career' in company_growth.lower() and 'growth' in c.get('aspirations_role', '').lower():
                score += 1
                reasons.append("Growth aligned")
        
        # Values matching
        if company_values and c.get('tags'):
            if 'speed' in company_values and 'fast' in c.get('tags', '').lower():
                score += 1
            if 'quality' in company_values and 'quality' in c.get('tags', '').lower():
                score += 1
            if 'relationships' in company_values and 'relationship' in c.get('tags', '').lower():
                score += 1
        
        if score > 5:  # Only include matches
            matches.append({
                'candidate': c,
                'score': min(score, 10),
                'reasons': reasons
            })
    
    matches.sort(key=lambda x: x['score'], reverse=True)
    
    db.close()
    
    return render_template('company_intelligence_detail.html', company=company, jobs=jobs, matches=matches)

@app.route('/company-intelligence/add', methods=['GET', 'POST'])
def company_intelligence_add():
    """Add company intelligence"""
    db = get_db()
    cursor = db.cursor()
    
    if request.method == 'POST':
        company_id = request.form.get('company_id')
        
        cursor.execute('''
            INSERT OR REPLACE INTO company_intelligence (
                company_id, project_types, pace, team_style, client_relationship,
                size_profile, growth_culture, what_they_value, ideal_candidate_profile,
                common_pitfalls, notes, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (
            company_id,
            request.form.get('project_types'),
            request.form.get('pace'),
            request.form.get('team_style'),
            request.form.get('client_relationship'),
            request.form.get('size_profile'),
            request.form.get('growth_culture'),
            request.form.get('what_they_value'),
            request.form.get('ideal_candidate_profile'),
            request.form.get('common_pitfalls'),
            request.form.get('notes')
        ))
        
        db.commit()
        db.close()
        return redirect(url_for('company_intelligence_detail', company_id=company_id))
    
    # GET - show form
    cursor.execute('SELECT id, name FROM companies WHERE name IS NOT NULL AND name != "" ORDER BY name')
    companies = cursor.fetchall()
    
    db.close()
    
    return render_template('company_intelligence_add.html', companies=companies)

@app.route('/company-intelligence/<int:company_id>/edit', methods=['GET', 'POST'])
def company_intelligence_edit(company_id):
    """Edit company intelligence"""
    db = get_db()
    cursor = db.cursor()
    
    if request.method == 'POST':
        cursor.execute('''
            INSERT OR REPLACE INTO company_intelligence (
                company_id, project_types, pace, team_style, client_relationship,
                size_profile, growth_culture, what_they_value, ideal_candidate_profile,
                common_pitfalls, notes, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (
            company_id,
            request.form.get('project_types'),
            request.form.get('pace'),
            request.form.get('team_style'),
            request.form.get('client_relationship'),
            request.form.get('size_profile'),
            request.form.get('growth_culture'),
            request.form.get('what_they_value'),
            request.form.get('ideal_candidate_profile'),
            request.form.get('common_pitfalls'),
            request.form.get('notes')
        ))
        
        db.commit()
        db.close()
        return redirect(url_for('company_intelligence_detail', company_id=company_id))
    
    # GET - show form
    cursor.execute('''
        SELECT c.*, ci.*
        FROM companies c
        LEFT JOIN company_intelligence ci ON c.id = ci.company_id
        WHERE c.id = ?
    ''', (company_id,))
    company = dict(cursor.fetchone())
    
    db.close()
    
    return render_template('company_intelligence_edit.html', company=company)

# ===== END COMPANY INTELLIGENCE =====

@app.route('/projects')
def projects_list():
    """List all projects"""
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute('''
        SELECT p.*, c.name as company_name 
        FROM projects p 
        LEFT JOIN companies c ON p.company_id = c.id 
        ORDER BY p.created_at DESC
    ''')
    projects = cursor.fetchall()
    
    cursor.execute('SELECT id, name FROM companies ORDER BY name')
    companies = cursor.fetchall()
    db.close()
    
    return render_template('projects.html', projects=projects, companies=companies)

@app.route('/project/<int:project_id>')
def project_detail(project_id):
    """Project detail page"""
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''
        SELECT p.*, c.name as company_name, c.id as company_id
        FROM projects p
        LEFT JOIN companies c ON p.company_id = c.id
        WHERE p.id = ?
    ''', (project_id,))
    project = cursor.fetchone()
    db.close()
    if not project:
        return redirect(url_for('projects_list'))
    return render_template('project_detail.html', project=project)

@app.route('/contacts')
def contacts_list():
    """List all contacts"""
    db = get_db()
    cursor = db.cursor()
    
    search = request.args.get('search', '')
    sort = request.args.get('sort', 'contact_name')
    order = request.args.get('order', 'ASC')
    
    # Validate sort column
    allowed_sorts = ['contact_name', 'company', 'relationship_score', 'last_interaction', 'next_touch_date']
    if sort not in allowed_sorts:
        sort = 'contact_name'
    
    # Validate order
    if order not in ['ASC', 'DESC']:
        order = 'ASC'
    
    if search:
        cursor.execute(f'SELECT * FROM contacts WHERE contact_name LIKE ? OR company LIKE ? ORDER BY {sort} {order}', 
                      (f'%{search}%', f'%{search}%'))
    else:
        cursor.execute(f'SELECT * FROM contacts ORDER BY {sort} {order}')
    
    contacts = cursor.fetchall()
    db.close()
    
    return render_template('contacts.html', contacts=contacts, search=search, sort=sort, order=order)

@app.route('/leads')
def leads_list():
    """List all leads/intel"""
    db = get_db()
    cursor = db.cursor()
    search = request.args.get('search', '')
    if search:
        cursor.execute('SELECT * FROM leads WHERE company LIKE ? OR intel_type LIKE ? OR what_it_means LIKE ? ORDER BY date DESC', 
                      (f'%{search}%', f'%{search}%', f'%{search}%'))
    else:
        cursor.execute('SELECT * FROM leads ORDER BY date DESC')
    leads = cursor.fetchall()
    db.close()
    return render_template('leads.html', leads=leads, search=search)

@app.route('/api/lead/<int:lead_id>', methods=['GET'])
def api_get_lead(lead_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM leads WHERE id = ?', (lead_id,))
    row = cursor.fetchone()
    db.close()
    if row:
        return jsonify(dict(row))
    return jsonify({'error': 'Not found'}), 404

@app.route('/api/lead', methods=['POST'])
def api_add_lead():
    data = request.json
    db = get_db()
    cursor = db.cursor()
    try:
        if data.get('id'):
            cursor.execute('''UPDATE leads SET date=?, company=?, intel_type=?, source=?, what_it_means=?, 
                           action_trigger=?, location=?, sector=?, hiring_manager=?, phone=? WHERE id=?''',
                         (data.get('date'), data.get('company'), data.get('intel_type'), data.get('source'),
                          data.get('what_it_means'), data.get('action_trigger'),
                          data.get('location'), data.get('sector'), data.get('hiring_manager'), data.get('phone'),
                          data.get('id')))
        else:
            cursor.execute('''INSERT INTO leads (date, company, intel_type, source, what_it_means, 
                           action_trigger, location, sector, hiring_manager, phone) VALUES (?,?,?,?,?,?,?,?,?,?)''',
                         (data.get('date'), data.get('company'), data.get('intel_type'), data.get('source'),
                          data.get('what_it_means'), data.get('action_trigger'),
                          data.get('location'), data.get('sector'), data.get('hiring_manager'), data.get('phone')))
        db.commit()
        db.close()
        return jsonify({'status': 'success'})
    except Exception as e:
        db.close()
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/api/delete/lead/<int:record_id>', methods=['POST'])
def api_delete_lead(record_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('DELETE FROM leads WHERE id = ?', (record_id,))
    db.commit()
    db.close()
    return jsonify({'status': 'success'})

HUNTER_API_KEY = 'a4309eac38a707b805e3437cf8ab968056fb15e8'

# Role → Reports To mapping for construction/subcontractor roles
REPORTS_TO_MAP = {
    # Estimating
    "estimator": ["Estimating Manager", "Construction Manager", "Operations Manager"],
    "senior estimator": ["Estimating Manager", "General Manager"],
    "chief estimator": ["General Manager", "Director"],
    "estimating manager": ["General Manager", "Director"],
    
    # Site/Construction
    "site manager": ["Project Manager", "Construction Manager"],
    "site superintendent": ["Project Manager", "Construction Manager"],
    "project manager": ["Project Director", "Construction Manager", "General Manager"],
    "project director": ["General Manager", "Director", "CEO"],
    "construction manager": ["General Manager", "Director"],
    "contracts administrator": ["Project Manager", "Construction Manager"],
    "ca": ["Project Manager", "Construction Manager"],
    "contracts manager": ["Project Director", "General Manager"],
    
    # Engineering
    "site engineer": ["Project Manager", "Site Manager"],
    "project engineer": ["Project Manager", "Construction Manager"],
    "structural engineer": ["Engineering Manager", "Project Manager"],
    "civil engineer": ["Project Manager", "Engineering Manager"],
    "electrical engineer": ["Engineering Manager", "Project Manager"],
    "mechanical engineer": ["Engineering Manager", "Project Manager"],
    "engineer": ["Project Manager", "Engineering Manager"],
    
    # Foreperson/Trade
    "foreman": ["Site Manager", "Project Manager"],
    "leading hand": ["Foreman", "Site Manager"],
    "supervisor": ["Site Manager", "Project Manager"],
    
    # Commercial
    "quantity surveyor": ["Commercial Manager", "Project Manager"],
    "qs": ["Commercial Manager", "Project Manager"],
    "senior quantity surveyor": ["Commercial Manager", "Project Director"],
    "commercial manager": ["Project Director", "General Manager"],
    "cost manager": ["Commercial Manager", "Project Manager"],
    
    # Management
    "general manager": ["CEO", "Director", "Managing Director"],
    "operations manager": ["General Manager", "CEO"],
    "business development manager": ["General Manager", "CEO"],
    "bdm": ["General Manager", "CEO"],
    "managing director": ["CEO"],
    "director": ["CEO"],
    "ceo": [],
    
    # Specialized
    "safety officer": ["Site Manager", "Project Manager"],
    "safety manager": ["Operations Manager", "General Manager"],
    "quality manager": ["Project Manager", "Construction Manager"],
    "environmental manager": ["Operations Manager", "Project Manager"],
    
    # Default
    "default": ["Operations Manager", "General Manager", "Director"]
}

def extract_role_from_text(text):
    """Extract job title from what_it_means or action_trigger fields"""
    if not text:
        return None, None
    
    text_lower = text.lower()
    
    # Keywords to look for (in priority order)
    role_keywords = [
        "estimator", "senior estimator", "chief estimator", "estimating manager",
        "site manager", "site superintendent", "project manager", "project director", "construction manager",
        "contracts administrator", "ca", "contracts manager",
        "site engineer", "project engineer", "structural engineer", "civil engineer", "electrical engineer", "mechanical engineer",
        "foreman", "leading hand", "supervisor",
        "quantity surveyor", "qs", "senior quantity surveyor", "commercial manager", "cost manager",
        "general manager", "operations manager", "business development manager", "bdm",
        "safety officer", "safety manager", "quality manager", "environmental manager"
    ]
    
    for keyword in role_keywords:
        if keyword in text_lower:
            return keyword, REPORTS_TO_MAP.get(keyword, REPORTS_TO_MAP["default"])
    
    return None, REPORTS_TO_MAP["default"]

def score_contact_by_role(contact_title, target_roles):
    """Score a contact by how well their title matches target roles"""
    if not contact_title or not target_roles:
        return 0
    
    contact_lower = contact_title.lower()
    score = 0
    
    for i, target in enumerate(target_roles):
        target_lower = target.lower()
        # Exact match gets highest score
        if target_lower in contact_lower:
            # Higher score for better match (earlier in list = more senior)
            return 100 - (i * 10)
        # Partial match
        words = target_lower.split()
        for word in words:
            if len(word) > 3 and word in contact_lower:
                return 50 - (i * 5)
    
    return 0

def guess_domain(company_name):
    """Guess domain from company name for construction companies"""
    if not company_name:
        return None
    company_lower = company_name.lower().strip()
    
    # Known major construction companies
    known_domains = {
        'multiplex': 'multiplex.global',
        'hutchinson builders': 'hutchinsonbuilders.com',
        'hutchies': 'hutchinsonbuilders.com',
        'lendlease': 'lendlease.com',
        'ci group': 'cigroup.com.au',
        'cigroup': 'cigroup.com.au',
        'built': 'built.com.au',
        'icon': 'iconco.com.au',
        'icon co': 'iconco.com.au',
        'cockfield': 'cockfield.com.au',
        'fender': 'fender.com.au',
        'shaw contracting': 'shawcontracting.com.au',
        'sunstate': 'sunstate.com.au',
        'qj': 'qj.com.au',
        'k选用本': 'k选取本.com.au',
    }
    
    for key, domain in known_domains.items():
        if key in company_lower:
            return domain
    
    # Generic: try companyname.com.au
    # Remove common suffixes
    clean_name = company_lower
    for suffix in [' pty ltd', ' pty ltd', ' pty', ' ltd', ' co', ' group', ' constructions', ' construction', ' p&c']:
        clean_name = clean_name.replace(suffix, '')
    clean_name = clean_name.strip()
    clean_name = ''.join(c for c in clean_name if c.isalnum() or c == ' ')
    clean_name = clean_name.replace(' ', '')
    
    if clean_name:
        return f"{clean_name}.com.au"
    return None

@app.route('/api/lead/<int:lead_id>/outcome', methods=['POST'])
def api_lead_outcome(lead_id):
    """Update lead outcome"""
    data = request.json
    outcome = data.get('outcome', 'New Lead')
    db = get_db()
    cursor = db.cursor()
    cursor.execute('UPDATE leads SET outcome=? WHERE id=?', (outcome, lead_id))
    db.commit()
    db.close()
    return jsonify({'status': 'ok'})

@app.route('/api/lead/<int:lead_id>/field', methods=['POST'])
def api_lead_field(lead_id):
    """Update an arbitrary editable field on a lead"""
    data = request.json
    field = data.get('field')
    value = data.get('value', '')
    allowed = {'hiring_manager', 'hiring_manager_title', 'phone', 'location', 'sector'}
    if field not in allowed:
        return jsonify({'status': 'error', 'message': 'Field not allowed'}), 400
    db = get_db()
    cursor = db.cursor()
    cursor.execute(f'UPDATE leads SET {field}=? WHERE id=?', (value, lead_id))
    db.commit()
    db.close()
    return jsonify({'status': 'ok'})

@app.route('/api/lead/<int:lead_id>/enrich', methods=['POST'])
def api_enrich_lead(lead_id):
    """Enrich lead with Hunter.io email lookup + role intelligence"""
    import requests
    
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM leads WHERE id = ?', (lead_id,))
    lead = cursor.fetchone()
    
    if not lead:
        db.close()
        return jsonify({'status': 'error', 'message': 'Lead not found'}), 404
    
    company = lead['company']
    # Also get role_sought if available
    role_sought = lead.get('role_sought') if hasattr(lead, 'get') else None
    
    # Try to extract role from what_it_means or action_trigger
    what_it_means = lead['what_it_means'] or ''
    action_trigger = lead['action_trigger'] or ''
    combined_text = f"{what_it_means} {action_trigger}"
    
    detected_role, target_manager_titles = extract_role_from_text(combined_text)
    
    # If role_sought is explicitly set in DB, use it
    if not detected_role and role_sought:
        detected_role, target_manager_titles = extract_role_from_text(role_sought)
    
    domain = guess_domain(company)
    
    if not domain:
        db.close()
        return jsonify({'status': 'error', 'message': f'Could not guess domain for {company}'}), 400
    
    try:
        url = f'https://api.hunter.io/v2/domain-search?domain={domain}&api_key={HUNTER_API_KEY}&limit=10'
        resp = requests.get(url, timeout=10)
        
        if resp.status_code != 200:
            db.close()
            return jsonify({'status': 'error', 'message': f'Hunter API error: {resp.status_code}'}), resp.status_code
        
        data = resp.json()
        all_contacts = []
        best_matches = []
        
        if 'data' in data and 'emails' in data['data']:
            for email in data['data']['emails']:
                contact = {
                    'email': email.get('email'),
                    'first_name': email.get('first_name'),
                    'last_name': email.get('last_name'),
                    'position': email.get('position'),
                    'department': email.get('department')
                }
                all_contacts.append(contact)
                
                # Score by role match
                if target_manager_titles:
                    score = score_contact_by_role(contact.get('position'), target_manager_titles)
                    if score > 0:
                        contact['role_score'] = score
                        best_matches.append(contact)
        
        # Sort best matches by score (descending) and take top 3
        best_matches.sort(key=lambda x: x.get('role_score', 0), reverse=True)
        best_matches = best_matches[:3]
        
        # Generate recommended approach
        if detected_role and target_manager_titles:
            manager_title = target_manager_titles[0] if target_manager_titles else "Manager"
            recommended_approach = f"Ask for the {manager_title} when calling {company}"
        else:
            recommended_approach = f"Call {company} and ask for the relevant decision maker"
        
        # Try fallback domains if no emails found
        if not all_contacts:
            fallback_domains = []
            base = company.lower().replace(' ', '').replace('&','and')
            fallback_domains = [f"{base}.com.au", f"{base}.com", f"{base}.net.au"]
            for fb_domain in fallback_domains:
                if fb_domain == domain:
                    continue
                try:
                    fb_resp = requests.get(f'https://api.hunter.io/v2/domain-search?domain={fb_domain}&api_key={HUNTER_API_KEY}&limit=10', timeout=10)
                    time.sleep(1.5)  # Prevent Hunter.io/Alibaba Cloud rate limiting
                    if fb_resp.status_code == 200:
                        fb_data = fb_resp.json()
                        if fb_data.get('data', {}).get('emails'):
                            domain = fb_domain
                            for email in fb_data['data']['emails']:
                                contact = {
                                    'email': email.get('email'),
                                    'first_name': email.get('first_name'),
                                    'last_name': email.get('last_name'),
                                    'position': email.get('position'),
                                    'department': email.get('department')
                                }
                                all_contacts.append(contact)
                                if target_manager_titles:
                                    score = score_contact_by_role(contact.get('position'), target_manager_titles)
                                    if score > 0:
                                        contact['role_score'] = score
                                        best_matches.append(contact)
                            break
                except:
                    pass

        best_matches.sort(key=lambda x: x.get('role_score', 0), reverse=True)
        best_matches = best_matches[:3]

        db.close()
        return jsonify({
            'status': 'success',
            'company': company,
            'domain': domain,
            'role_sought': detected_role,
            'reports_to': target_manager_titles,
            'best_matches': best_matches,
            'all_contacts': all_contacts,
            'recommended_approach': recommended_approach
        })
    
    except Exception as e:
        db.close()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/contact/<int:contact_id>')
def contact_detail(contact_id):
    """Contact detail view"""
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM contacts WHERE id = ?', (contact_id,))
    contact = cursor.fetchone()
    db.close()
    
    if not contact:
        return redirect(url_for('contacts_list'))
    
    return render_template('contact_detail.html', contact=contact)

@app.route('/api/contact', methods=['POST'])
def api_add_contact():
    """API: Add/edit contact"""
    data = request.json
    db = get_db()
    cursor = db.cursor()
    
    try:
        if 'id' in data and data['id']:
            cursor.execute('''
                UPDATE contacts 
                SET contact_name=?, company=?, type=?, relationship_score=?, 
                    last_interaction=?, interaction_type=?, personal_detail=?,
                    value_given=?, next_touch_date=?, notes=?, phone=?, email=?
                WHERE id=?
            ''', (data.get('contact_name'), data.get('company'), data.get('type'),
                  data.get('relationship_score'), data.get('last_interaction'),
                  data.get('interaction_type'), data.get('personal_detail'),
                  data.get('value_given'), data.get('next_touch_date'),
                  data.get('notes'), data.get('phone'), data.get('email'),
                  data.get('id')))
        else:
            cursor.execute('''
                INSERT INTO contacts 
                (contact_name, company, company_id, type, relationship_score, last_interaction,
                 interaction_type, personal_detail, value_given, next_touch_date, notes, phone, email)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (data.get('contact_name'), data.get('company'), data.get('company_id'),
                  data.get('type'), data.get('relationship_score'), data.get('last_interaction'),
                  data.get('interaction_type'), data.get('personal_detail'),
                  data.get('value_given'), data.get('next_touch_date'), data.get('notes'),
                  data.get('phone'), data.get('email')))
        
        db.commit()
        db.close()
        return jsonify({'status': 'success'})
    except Exception as e:
        db.close()
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/api/contacts-by-company')
def api_contacts_by_company():
    """API: Get contacts by company name"""
    company = request.args.get('company', '')
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT id, contact_name, phone FROM contacts WHERE company LIKE ? ORDER BY contact_name', 
                  (f'%{company}%',))
    contacts = cursor.fetchall()
    db.close()
    return jsonify([dict(c) for c in contacts])

@app.route('/api/companies-list')
def api_companies_list():
    """API: Get all companies"""
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT id, name FROM companies ORDER BY name')
    companies = [{'id': row[0], 'name': row[1]} for row in cursor.fetchall()]
    db.close()
    return jsonify(companies)

@app.route('/api/companies')
def api_companies():
    """API: Get companies with full details for outreach"""
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''SELECT id, name, tier, sector, location, active_projects,
                      notes, last_activity, website, company_type
                      FROM companies ORDER BY tier ASC, name ASC''')
    columns = [desc[0] for desc in cursor.description]
    companies = []
    for row in cursor.fetchall():
        c = dict(zip(columns, row))
        # Get primary contact
        cursor.execute('''SELECT name, role FROM decision_makers
                          WHERE company_id = ? AND is_primary = 1 LIMIT 1''', (c['id'],))
        dm = cursor.fetchone()
        c['contact_name'] = dm[0] if dm else c.get('notes', '')
        companies.append(c)
    db.close()
    return jsonify(companies)

@app.route('/api/contact/<int:contact_id>')
def api_get_contact(contact_id):
    """API: Get contact by ID"""
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM contacts WHERE id = ?', (contact_id,))
    contact = cursor.fetchone()
    db.close()
    if contact:
        return jsonify(dict(contact))
    return jsonify({'error': 'Not found'}), 404

@app.route('/api/delete/contact/<int:record_id>', methods=['POST'])
def api_delete_contact(record_id):
    """API: Delete contact"""
    db = get_db()
    cursor = db.cursor()
    cursor.execute('DELETE FROM contacts WHERE id = ?', (record_id,))
    db.commit()
    db.close()
    return jsonify({'status': 'success'})

# ============ PROJECTS API ============
@app.route('/api/projects')
def api_list_projects():
    """API: List all projects"""
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''
        SELECT p.*, c.name as company_name 
        FROM projects p 
        LEFT JOIN companies c ON p.company_id = c.id 
        ORDER BY p.created_at DESC
    ''')
    projects = cursor.fetchall()
    db.close()
    return jsonify([dict(p) for p in projects])

@app.route('/api/project/<int:project_id>')
def api_get_project(project_id):
    """API: Get project by ID"""
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''
        SELECT p.*, c.name as company_name 
        FROM projects p 
        LEFT JOIN companies c ON p.company_id = c.id 
        WHERE p.id = ?
    ''', (project_id,))
    project = cursor.fetchone()
    db.close()
    if project:
        return jsonify(dict(project))
    return jsonify({'error': 'Not found'}), 404

@app.route('/api/projects', methods=['POST'])
def api_add_project():
    """API: Add/edit project"""
    data = request.json
    db = get_db()
    cursor = db.cursor()
    
    try:
        if 'id' in data and data['id']:
            # Update
            cursor.execute('''
                UPDATE projects 
                SET name=?, address=?, company_id=?, da_number=?, status=?, description=?
                WHERE id=?
            ''', (data.get('name'), data.get('address'), data.get('company_id'),
                  data.get('da_number'), data.get('status'), data.get('description'),
                  data.get('id')))
        else:
            # Add
            cursor.execute('''
                INSERT INTO projects 
                (name, address, company_id, da_number, status, description)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (data.get('name'), data.get('address'), data.get('company_id'),
                  data.get('da_number'), data.get('status') or 'Live', data.get('description')))
        
        db.commit()
        db.close()
        return jsonify({'status': 'success'})
    except Exception as e:
        db.close()
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/api/project/<int:project_id>', methods=['PUT'])
def api_update_project(project_id):
    """API: Update project"""
    data = request.json
    db = get_db()
    cursor = db.cursor()
    
    try:
        cursor.execute('''
            UPDATE projects 
            SET name=?, address=?, company_id=?, da_number=?, status=?, description=?
            WHERE id=?
        ''', (data.get('name'), data.get('address'), data.get('company_id'),
              data.get('da_number'), data.get('status'), data.get('description'),
              project_id))
        db.commit()
        db.close()
        return jsonify({'status': 'success'})
    except Exception as e:
        db.close()
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/api/project/<int:project_id>', methods=['DELETE'])
def api_delete_project(project_id):
    """API: Delete project"""
    db = get_db()
    cursor = db.cursor()
    cursor.execute('DELETE FROM projects WHERE id = ?', (project_id,))
    db.commit()
    db.close()
    return jsonify({'status': 'success'})

@app.route('/candidate/<int:candidate_id>')
def candidate_detail(candidate_id):
    """Candidate detail page"""
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute('SELECT * FROM candidates WHERE id = ?', (candidate_id,))
    candidate = cursor.fetchone()
    
    if not candidate:
        return redirect(url_for('candidates_list'))
    
    db.close()
    
    return render_template('candidate_detail.html', candidate=candidate)

@app.route('/candidate/<int:candidate_id>/profile', methods=['GET', 'POST'])
def candidate_profile(candidate_id):
    """Candidate Profile Generator - form and output"""
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute('SELECT * FROM candidates WHERE id = ?', (candidate_id,))
    candidate = cursor.fetchone()
    
    if not candidate:
        db.close()
        return redirect(url_for('candidates_list'))
    
    if request.method == 'POST':
        # Render the polished profile
        profile_data = {
            'name': candidate['name'],
            'title': candidate['title'],
            'current_company': candidate['current_company'],
            'location': candidate['location'],
            'salary': candidate['salary_band'],
            'specialism': candidate['specialism'],
            'years_experience': candidate['years_experience'],
            'notes': candidate['notes'],
            'career_summary': request.form.get('career_summary', ''),
            'achievement_1': request.form.get('achievement_1', ''),
            'achievement_2': request.form.get('achievement_2', ''),
            'achievement_3': request.form.get('achievement_3', ''),
            'technical_skills': request.form.get('technical_skills', ''),
            'industries': request.form.get('industries', ''),
            'why_seeking': request.form.get('why_seeking', ''),
            'work_style': request.form.get('work_style', ''),
            'references': request.form.get('references', 'no')
        }
        db.close()
        return render_template('candidate_profile.html', candidate=candidate, profile=profile_data)
    
    # GET - show form pre-filled with candidate data
    db.close()
    return render_template('candidate_profile_form.html', candidate=candidate)

@app.route('/candidate/<int:candidate_id>/submittal', methods=['GET', 'POST'])
def candidate_submittal(candidate_id):
    """Candidate Submittal Generator - form and output"""
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute('SELECT * FROM candidates WHERE id = ?', (candidate_id,))
    candidate = cursor.fetchone()
    
    if not candidate:
        db.close()
        return redirect(url_for('candidates_list'))
    
    if request.method == 'POST':
        # Render the polished submittal
        submittal_data = {
            'name': candidate['name'],
            'title': candidate['title'],
            'current_company': candidate['current_company'],
            'location': candidate['location'],
            'salary': candidate['salary_band'],
            'specialism': candidate['specialism'],
            'years_experience': candidate['years_experience'],
            'notes': candidate['notes'],
            'interview_notes': request.form.get('interview_notes', ''),
            'strength_1': request.form.get('strength_1', ''),
            'strength_2': request.form.get('strength_2', ''),
            'strength_3': request.form.get('strength_3', ''),
            'why_good_fit': request.form.get('why_good_fit', ''),
            'availability': request.form.get('availability', '')
        }
        db.close()
        return render_template('candidate_submittal.html', candidate=candidate, submittal=submittal_data)
    
    # GET - show form pre-filled with candidate data
    db.close()
    return render_template('candidate_submittal_form.html', candidate=candidate)

@app.route('/api/candidate', methods=['POST'])
def api_add_candidate():
    """API: Add/edit candidate"""
    data = request.json
    db = get_db()
    cursor = db.cursor()
    
    try:
        if 'id' in data and data['id']:
            # Update
            cursor.execute('''
                UPDATE candidates 
                SET name=?, current_company=?, title=?, specialism=?, years_experience=?,
                    salary_band=?, location=?, mobility=?, flight_risk=?, known_offers=?,
                    who_wants_them=?, relationship_score=?, last_contact=?, next_follow_up=?,
                    notes=?, updated_at=CURRENT_TIMESTAMP
                WHERE id=?
            ''', (data.get('name'), data.get('current_company'), data.get('title'),
                  data.get('specialism'), data.get('years_experience'), data.get('salary_band'),
                  data.get('location'), data.get('mobility'), data.get('flight_risk'),
                  data.get('known_offers'), data.get('who_wants_them'), 
                  data.get('relationship_score'), data.get('last_contact'),
                  data.get('next_follow_up'), data.get('notes'), data.get('id')))
        else:
            # Add
            cursor.execute('''
                INSERT INTO candidates 
                (name, current_company, title, specialism, years_experience, salary_band,
                 location, mobility, flight_risk, known_offers, who_wants_them,
                 relationship_score, last_contact, next_follow_up, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (data.get('name'), data.get('current_company'), data.get('title'),
                  data.get('specialism'), data.get('years_experience'), data.get('salary_band'),
                  data.get('location'), data.get('mobility'), data.get('flight_risk'),
                  data.get('known_offers'), data.get('who_wants_them'),
                  data.get('relationship_score'), data.get('last_contact'),
                  data.get('next_follow_up'), data.get('notes')))
        
        db.commit()
        db.close()
        return jsonify({'status': 'success'})
    except Exception as e:
        db.close()
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/deals')
def deals_list():
    """List all deals"""
    db = get_db()
    cursor = db.cursor()
    
    stage = request.args.get('stage', '')
    
    if stage:
        cursor.execute('SELECT * FROM deals WHERE stage = ? ORDER BY updated_at DESC', (stage,))
    else:
        cursor.execute('SELECT * FROM deals ORDER BY updated_at DESC')
    
    deals = cursor.fetchall()
    
    # Get unique stages for filter
    cursor.execute('SELECT DISTINCT stage FROM deals ORDER BY stage')
    stages = cursor.fetchall()
    
    db.close()
    
    return render_template('deals.html', deals=deals, stages=stages, current_stage=stage)

@app.route('/deal/<int:deal_id>')
def deal_detail(deal_id):
    """Deal detail page"""
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute('SELECT * FROM deals WHERE id = ?', (deal_id,))
    deal = cursor.fetchone()
    
    if not deal:
        return redirect(url_for('deals_list'))
    
    db.close()
    
    return render_template('deal_detail.html', deal=deal)

@app.route('/api/deal/<int:deal_id>')
def api_get_deal(deal_id):
    """API: Get deal by ID"""
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM deals WHERE id = ?', (deal_id,))
    deal = cursor.fetchone()
    db.close()
    if deal:
        return jsonify(dict(deal))
    return jsonify({'error': 'Not found'}), 404

@app.route('/api/deal', methods=['POST'])
def api_add_deal():
    """API: Add/edit deal"""
    data = request.json
    db = get_db()
    cursor = db.cursor()
    
    try:
        if 'id' in data and data['id']:
            # Update
            cursor.execute('''
                UPDATE deals 
                SET client=?, role=?, salary_value=?, fee_value=?, stage=?,
                    competition=?, probability=?, next_action=?, notes=?,
                    contact_name=?, phone=?, updated_at=CURRENT_TIMESTAMP
                WHERE id=?
            ''', (data.get('client'), data.get('role'), data.get('salary_value'),
                  data.get('fee_value'), data.get('stage'), data.get('competition'),
                  data.get('probability'), data.get('next_action'), data.get('notes'),
                  data.get('contact_name'), data.get('phone'), data.get('id')))
        else:
            # Add
            cursor.execute('''
                INSERT INTO deals 
                (client, role, salary_value, fee_value, stage, competition, probability, next_action, notes, contact_name, phone)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (data.get('client'), data.get('role'), data.get('salary_value'),
                  data.get('fee_value'), data.get('stage'), data.get('competition'),
                  data.get('probability'), data.get('next_action'), data.get('notes'),
                  data.get('contact_name'), data.get('phone')))
        
        db.commit()
        db.close()
        return jsonify({'status': 'success'})
    except Exception as e:
        db.close()
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/api/delete/<table>/<int:record_id>', methods=['POST'])
def api_delete(table, record_id):
    """API: Delete record with confirmation"""
    db = get_db()
    cursor = db.cursor()
    
    try:
        if table == 'candidate':
            cursor.execute('DELETE FROM candidates WHERE id = ?', (record_id,))
        elif table == 'company':
            cursor.execute('DELETE FROM companies WHERE id = ?', (record_id,))
        elif table == 'dm':
            cursor.execute('DELETE FROM decision_makers WHERE id = ?', (record_id,))
        elif table == 'deal':
            cursor.execute('DELETE FROM deals WHERE id = ?', (record_id,))
        
        db.commit()
        db.close()
        return jsonify({'status': 'success'})
    except Exception as e:
        db.close()
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/api/activity', methods=['POST'])
def api_add_activity():
    """API: Add new activity (call, meeting, visit, etc.)"""
    data = request.json
    db = get_db()
    cursor = db.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO activities (type, company_id, contact_id, candidate_id, deal_id, notes, outcome, duration_minutes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('type'),
            data.get('company_id'),
            data.get('contact_id'),
            data.get('candidate_id'),
            data.get('deal_id'),
            data.get('notes'),
            data.get('outcome'),
            data.get('duration_minutes')
        ))
        
        # Update last_contact on the related record
        from datetime import datetime
        today = datetime.now().strftime('%Y-%m-%d')
        
        if data.get('candidate_id'):
            cursor.execute('UPDATE candidates SET last_contact = ? WHERE id = ?', 
                          (today, data.get('candidate_id')))
        if data.get('contact_id'):
            # Try contacts table first (newer), then decision_makers
            cursor.execute('UPDATE contacts SET last_interaction = ? WHERE id = ?', 
                          (today, data.get('contact_id')))
        
        db.commit()
        db.close()
        return jsonify({'status': 'success'})
    except Exception as e:
        db.close()
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/api/activities/<table>/<int:record_id>')
def api_get_activities(table, record_id):
    """API: Get activities for a company, candidate, or deal"""
    db = get_db()
    cursor = db.cursor()
    
    try:
        if table == 'company':
            cursor.execute('''
                SELECT a.*, c.name as contact_name, co.name as company_name
                FROM activities a
                LEFT JOIN decision_makers c ON a.contact_id = c.id
                LEFT JOIN companies co ON a.company_id = co.id
                WHERE a.company_id = ?
                ORDER BY a.created_at DESC
            ''', (record_id,))
        elif table == 'candidate':
            cursor.execute('''
                SELECT a.*, c.name as candidate_name
                FROM activities a
                LEFT JOIN candidates c ON a.candidate_id = c.id
                WHERE a.candidate_id = ?
                ORDER BY a.created_at DESC
            ''', (record_id,))
        elif table == 'deal':
            cursor.execute('''
                SELECT a.*, d.role as deal_role
                FROM activities a
                LEFT JOIN deals d ON a.deal_id = d.id
                WHERE a.deal_id = ?
                ORDER BY a.created_at DESC
            ''', (record_id,))
        else:
            return jsonify({'status': 'error', 'message': 'Invalid table'}), 400
        
        activities = []
        for row in cursor.fetchall():
            activities.append({
                'id': row[0],
                'type': row[1],
                'company_id': row[2],
                'contact_id': row[3],
                'notes': row[4],
                'outcome': row[5],
                'duration_minutes': row[6],
                'created_at': row[7],
                'candidate_id': row[8],
                'deal_id': row[9],
                'contact_name': row[10] if len(row) > 10 else None,
                'company_name': row[11] if len(row) > 11 else None
            })
        
        db.close()
        return jsonify({'activities': activities})
    except Exception as e:
        db.close()
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/api/next-action', methods=['POST'])
def api_set_next_action():
    """API: Set next_action date for candidate, dm, or deal"""
    data = request.json
    db = get_db()
    cursor = db.cursor()
    
    try:
        table = data.get('table')  # candidates, decision_makers, deals
        record_id = data.get('id')
        next_action = data.get('next_action')
        
        if table == 'candidates':
            cursor.execute('UPDATE candidates SET next_follow_up = ? WHERE id = ?', 
                          (next_action, record_id))
        elif table == 'decision_makers':
            cursor.execute('UPDATE decision_makers SET next_action = ? WHERE id = ?', 
                          (next_action, record_id))
        elif table == 'deals':
            cursor.execute('UPDATE deals SET next_action = ? WHERE id = ?', 
                          (next_action, record_id))
        else:
            return jsonify({'status': 'error', 'message': 'Invalid table'}), 400
        
        db.commit()
        db.close()
        return jsonify({'status': 'success'})
    except Exception as e:
        db.close()
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/api/export')
def api_export():
    """Export all data to CSV"""
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute('SELECT * FROM companies')
    companies = cursor.fetchall()
    
    csv_file = os.path.expanduser("~/.openclaw/workspace/seq-crm/market_map_export.csv")
    
    with open(csv_file, 'w', newline='') as f:
        writer = csv.writer(f)
        
        # Header
        writer.writerow(['Company', 'Tier', 'Sector', 'Location', 'Active Projects',
                        'Upcoming Projects', 'Competitors', 'DM Name', 'DM Title', 'DM Role',
                        'Phone', 'Email', 'LinkedIn', 'Hiring Signals', 'Relationship',
                        'Last Contact', 'Next Action', 'Notes'])
        
        # Data
        for company in companies:
            cursor.execute('SELECT * FROM decision_makers WHERE company_id = ?', 
                          (company['id'],))
            dms = cursor.fetchall()
            
            if dms:
                for dm in dms:
                    writer.writerow([
                        company['name'], company['tier'], company['sector'],
                        company['location'], company['active_projects'],
                        company['upcoming_projects'], company['competitors'],
                        dm['name'], dm['title'], dm['role'],
                        dm['phone'], dm['email'], dm['linkedin'],
                        dm['hiring_signals'], dm['relationship_score'],
                        dm['last_contact'], dm['next_action'], dm['notes']
                    ])
            else:
                writer.writerow([company['name'], company['tier'], company['sector'],
                               company['location'], company['active_projects'],
                               company['upcoming_projects'], company['competitors']])
    
    db.close()
    return send_file(csv_file, as_attachment=True, download_name=f"market_map_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")

@app.route('/cron/jobs.json')
def cron_jobs():
    import os
    jobs_path = '/home/chris/.openclaw/cron/jobs.json'
    if os.path.exists(jobs_path):
        return send_file(jobs_path, mimetype='application/json')
    return '{"jobs": []}', 404

@app.route('/mission-control')
@app.route('/mc')
def mc():
    return send_from_directory('static/mission', 'final.html')
@app.route('/v3')
def v3():
    return send_from_directory('static/mission', 'final.html')

@app.route('/mc-test')
def mc_test():
    return send_from_directory('static/mission', 'test.html')

# Activity tracking endpoint for Mission Control
@app.route('/api/activity')
def api_activity():
    import os
    from pathlib import Path
    
    activities = []
    base_path = Path('/home/chris/.openclaw/agents')
    
    # Check main agent sessions
    main_sessions = base_path / 'main' / 'sessions'
    if main_sessions.exists():
        for session_file in sorted(main_sessions.glob('*.jsonl'), key=lambda x: os.path.getmtime(x), reverse=True)[:2]:
            try:
                with open(session_file) as f:
                    lines = f.readlines()
                    for line in lines[-5:]:
                        import json
                        entry = json.loads(line)
                        entry_type = entry.get('type', '')
                        timestamp = entry.get('timestamp', '')
                        
                        if entry_type == 'message':
                            msg = entry.get('message', {})
                            role = msg.get('role', '')
                            content = msg.get('content', [])
                            
                            if role == 'user':
                                text = ''
                                for c in content:
                                    if c.get('type') == 'text':
                                        text = c.get('text', '')[:80]
                                if text:
                                    activities.append({
                                        'text': f'User: {text}',
                                        'type': 'user',
                                        'time': timestamp
                                    })
                            elif role == 'assistant':
                                for c in content:
                                    if c.get('type') == 'text':
                                        text = c.get('text', '')[:80]
                                        if text:
                                            activities.append({
                                                'text': f'Claudia: {text}',
                                                'type': 'claudia',
                                                'time': timestamp
                                            })
                                    elif c.get('type') == 'toolCall':
                                        tool_name = c.get('name', 'unknown')
                                        activities.append({
                                            'text': f'🔧 Running {tool_name}',
                                            'type': 'system',
                                            'time': timestamp
                                        })
            except:
                pass
    
    # Check jason subagent
    jason_sessions = base_path / 'jason' / 'sessions'
    if jason_sessions.exists():
        for session_file in sorted(jason_sessions.glob('*.jsonl'), key=lambda x: os.path.getmtime(x), reverse=True)[:1]:
            try:
                with open(session_file) as f:
                    lines = f.readlines()
                    for line in lines[-3:]:
                        import json
                        entry = json.loads(line)
                        if entry.get('type') == 'message':
                            msg = entry.get('message', {})
                            if msg.get('role') == 'assistant':
                                for c in msg.get('content', []):
                                    if c.get('type') == 'toolCall':
                                        activities.append({
                                            'text': f'👨‍💻 Jason: {c.get("name", "tool")}',
                                            'type': 'jason',
                                            'time': entry.get('timestamp')
                                        })
            except:
                pass
    
    return jsonify({'activities': activities[:15]})

# Additional routes for missing pages
@app.route('/analytics')
def analytics():
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT COUNT(*) as count FROM companies')
    companies_count = cursor.fetchone()['count']
    cursor.execute('SELECT COUNT(*) as count FROM contacts')
    contacts_count = cursor.fetchone()['count']
    cursor.execute('SELECT COUNT(*) as count FROM candidates')
    candidates_count = cursor.fetchone()['count']
    cursor.execute('SELECT COUNT(*) as count FROM deals')
    deals_count = cursor.fetchone()['count']
    
    # Real pipeline from deals
    cursor.execute('SELECT COALESCE(SUM(fee_value), 0) FROM deals')
    weighted_pipeline = cursor.fetchone()[0] or 0
    cursor.execute('SELECT COALESCE(SUM(fee_achieved), 0) FROM deals')
    total_fee_achieved = cursor.fetchone()[0] or 0
    
    # Real funnel from submissions table
    cursor.execute("SELECT COUNT(*) FROM submissions WHERE stage = 'cv_submitted'")
    cv_submitted = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM submissions WHERE stage = 'shortlisted'")
    cv_shortlisted = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM submissions WHERE stage = 'interview'")
    interview = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM submissions WHERE stage = 'offer'")
    offer = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM submissions WHERE stage = 'placed'")
    placed = cursor.fetchone()[0]
    
    # Real conversion rates from submissions data
    cv_submitted_pct = min(cv_submitted / max(candidates_count, 1) * 100, 100) if candidates_count else 0
    shortlist_rate = min(cv_shortlisted / max(cv_submitted, 1) * 100, 100) if cv_submitted else 0
    interview_rate = min(interview / max(cv_shortlisted, 1) * 100, 100) if cv_shortlisted else 0
    offer_rate = min(offer / max(interview, 1) * 100, 100) if interview else 0
    win_rate = min(placed / max(offer, 1) * 100, 100) if offer else 0
    cv_bar_pct = min(cv_submitted_pct, 100)
    shortlist_bar_pct = min(shortlist_rate, 100)
    interview_bar_pct = min(interview_rate, 100)
    offer_bar_pct = min(offer_rate, 100)
    win_bar_pct = min(win_rate, 100)
    at_risk_clients = 0  # No data yet for at-risk calc
    
    db.close()
    return render_template('analytics.html', 
                          companies_count=companies_count,
                          contacts_count=contacts_count,
                          candidates_count=candidates_count,
                          deals_count=deals_count,
                          weighted_pipeline=weighted_pipeline,
                          total_deals=total_deals,
                          cv_submitted=cv_submitted,
                          cv_shortlisted=cv_shortlisted,
                          interview=interview,
                          offer=offer,
                          placed=placed,
                          cv_submitted_pct=cv_submitted_pct,
                          shortlist_rate=shortlist_rate,
                          interview_rate=interview_rate,
                          offer_rate=offer_rate,
                          win_rate=win_rate,
                          cv_bar_pct=cv_bar_pct,
                          shortlist_bar_pct=shortlist_bar_pct,
                          interview_bar_pct=interview_bar_pct,
                          offer_bar_pct=offer_bar_pct,
                          win_bar_pct=win_bar_pct,
                          at_risk_clients=at_risk_clients)

@app.route('/activities')
def activities():
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM activities ORDER BY created_at DESC LIMIT 100')
    activities = cursor.fetchall()
    db.close()
    return render_template('activities.html', activities=activities)

@app.route('/submissions')
def submissions():
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM candidates ORDER BY created_at DESC')
    candidates = cursor.fetchall()
    db.close()
    return render_template('submissions.html', candidates=candidates)

@app.route('/weekly-reviews')
def weekly_reviews():
    return render_template('weekly_reviews.html')

@app.route('/job-adverts')
def job_adverts():
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM job_adverts ORDER BY created_at DESC')
    adverts = cursor.fetchall()
    db.close()
    return render_template('job_adverts.html', job_adverts=adverts)

@app.route('/job-advert/<int:advert_id>')
def view_job_advert(advert_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM job_adverts WHERE id = ?', (advert_id,))
    advert = cursor.fetchone()
    if not advert:
        db.close()
        return "Advert not found", 404
    
    advert_dict = dict(advert)
    
    # Extract real posted date from content
    import re as _re
    content = advert_dict.get('content', '') or ''
    posted_match = _re.search(r'Posted: (\d{4}-\d{2}-\d{2})', content)
    if posted_match:
        advert_dict['posted_date'] = posted_match.group(1)
    
    adzuna_id = advert_dict.get('adzuna_id')
    redirect_url = advert_dict.get('url')
    
    # Try to fetch full description from Adzuna using the job ID
    if adzuna_id and adzuna_id not in (None, '', 'None'):
        try:
            import urllib.request
            import json
            keys_path = Path(__file__).parent / "adzuna_keys.json"
            with open(keys_path) as f:
                keys = json.load(f)
            
            # Fetch full job details from Adzuna API using job ID
            url = f"https://api.adzuna.com/v1/api/jobs/au/{adzuna_id}?app_id={keys['app_id']}&app_key={keys['app_key']}"
            with urllib.request.urlopen(url, timeout=10) as response:
                full_job = json.loads(response.read().decode())
                if full_job.get('description'):
                    advert_dict['content'] = full_job['description']
                if full_job.get('redirect_url'):
                    advert_dict['url'] = full_job['redirect_url']
        except Exception as e:
            print(f"Could not fetch full advert: {e}")
    
    db.close()
    return render_template('job_advert_view.html', advert=advert_dict)

@app.route('/api/job-adverts')
def api_job_adverts():
    db = get_db()
    cursor = db.cursor()
    query = 'SELECT * FROM job_adverts WHERE 1=1'
    params = []
    
    tier = request.args.get('tier')
    if tier:
        query += ' AND tier = ?'
        params.append(tier)
    
    sector = request.args.get('sector')
    if sector:
        query += ' AND sector = ?'
        params.append(sector)
    
    size = request.args.get('size')
    if size:
        query += ' AND project_size = ?'
        params.append(size)
    
    location = request.args.get('location')
    if location:
        query += ' AND location LIKE ?'
        params.append(f'%{location}%')
    
    cursor.execute(query, params)
    adverts = cursor.fetchall()
    db.close()
    return jsonify([dict(row) for row in adverts])

@app.route('/api/job-advert/<int:advert_id>')
def api_job_advert(advert_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM job_adverts WHERE id = ?', (advert_id,))
    advert = cursor.fetchone()
    db.close()
    if advert:
        return jsonify(dict(advert))
    return jsonify({'error': 'Not found'}), 404

@app.route('/recruitment-metrics')
def recruitment_metrics():
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT COUNT(*) as count FROM companies')
    companies_count = cursor.fetchone()['count']
    cursor.execute('SELECT COUNT(*) as count FROM contacts')
    contacts_count = cursor.fetchone()['count']
    cursor.execute('SELECT COUNT(*) as count FROM candidates')
    candidates_count = cursor.fetchone()['count']
    cursor.execute('SELECT COUNT(*) as count FROM deals')
    total_deals = cursor.fetchone()['count']
    cursor.execute('SELECT COALESCE(SUM(fee_value), 0) FROM deals')
    total_fee_value = cursor.fetchone()[0] or 0
    cursor.execute('SELECT COALESCE(AVG(fee_value), 0) FROM deals')
    avg_fee = cursor.fetchone()[0] or 0
    cursor.execute('SELECT COALESCE(AVG(days_to_fill), 0) FROM deals WHERE days_to_fill IS NOT NULL')
    avg_days = cursor.fetchone()[0] or 0
    cursor.execute('SELECT COALESCE(SUM(fee_achieved), 0) FROM deals')
    total_fee_achieved = cursor.fetchone()[0] or 0
    cursor.execute("SELECT stage, COUNT(*) as count FROM deals GROUP BY stage")
    by_stage = cursor.fetchall()
    cursor.execute("SELECT COUNT(*) FROM submissions WHERE stage = 'cv_submitted'")
    submitted = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM submissions WHERE stage = 'interview'")
    interviews = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM submissions WHERE stage = 'offer'")
    offers = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM submissions WHERE stage = 'placed'")
    placed = cursor.fetchone()[0]
    # Real conversion rates
    cv_to_interview_rate = min(interviews / max(submitted, 1) * 100, 100) if submitted else 0
    interview_to_offer_rate = min(offers / max(interviews, 1) * 100, 100) if interviews else 0
    offer_accept_rate = min(placed / max(offers, 1) * 100, 100) if offers else 0
    db.close()
    return render_template('recruitment_metrics.html',
                          companies_count=companies_count,
                          contacts_count=contacts_count,
                          candidates_count=candidates_count,
                          total_deals=total_deals,
                          total_fee_value=total_fee_value,
                          total_fee_achieved=total_fee_achieved,
                          avg_fee=avg_fee,
                          avg_days=avg_days,
                          by_stage=by_stage,
                          active_candidates=candidates_count,
                          total_candidates=candidates_count,
                          submitted=submitted,
                          interviews=interviews,
                          offers=offers,
                          placed=placed,
                          cv_to_interview_rate=cv_to_interview_rate,
                          interview_to_offer_rate=interview_to_offer_rate,
                          offer_accept_rate=offer_accept_rate,
                          by_source=[],
                          recent_placements=[])

# Activity tracking endpoint for Mission Control
@app.route('/api/mc-activity')
def api_mc_activity():
    import os
    from pathlib import Path
    
    activities = []
    base_path = Path('/home/chris/.openclaw/agents')
    
    # Check main agent sessions
    main_sessions = base_path / 'main' / 'sessions'
    if main_sessions.exists():
        for session_file in sorted(main_sessions.glob('*.jsonl'), key=lambda x: os.path.getmtime(x), reverse=True)[:2]:
            try:
                with open(session_file) as f:
                    lines = f.readlines()
                    for line in lines[-5:]:  # Last 5 entries per session
                        import json
                        entry = json.loads(line)
                        entry_type = entry.get('type', '')
                        timestamp = entry.get('timestamp', '')
                        
                        if entry_type == 'message':
                            msg = entry.get('message', {})
                            role = msg.get('role', '')
                            content = msg.get('content', [])
                            
                            if role == 'user':
                                text = ''
                                for c in content:
                                    if c.get('type') == 'text':
                                        text = c.get('text', '')[:80]
                                if text:
                                    activities.append({
                                        'text': f'User: {text}',
                                        'type': 'user',
                                        'time': timestamp
                                    })
                            elif role == 'assistant':
                                for c in content:
                                    if c.get('type') == 'text':
                                        text = c.get('text', '')[:80]
                                        if text:
                                            activities.append({
                                                'text': f'Claudia: {text}',
                                                'type': 'claudia',
                                                'time': timestamp
                                            })
                                    elif c.get('type') == 'toolCall':
                                        tool_name = c.get('name', 'unknown')
                                        activities.append({
                                            'text': f'🔧 Running {tool_name}',
                                            'type': 'system',
                                            'time': timestamp
                                        })
                        elif entry_type == 'custom' and entry.get('customType') == 'model-snapshot':
                            activities.append({
                                'text': '🧠 Model thinking...',
                                'type': 'system',
                                'time': timestamp
                            })
            except:
                pass
    
    # Check jason subagent
    jason_sessions = base_path / 'jason' / 'sessions'
    if jason_sessions.exists():
        for session_file in sorted(jason_sessions.glob('*.jsonl'), key=lambda x: os.path.getmtime(x), reverse=True)[:1]:
            try:
                with open(session_file) as f:
                    lines = f.readlines()
                    for line in lines[-3:]:
                        import json
                        entry = json.loads(line)
                        if entry.get('type') == 'message':
                            msg = entry.get('message', {})
                            if msg.get('role') == 'assistant':
                                for c in msg.get('content', []):
                                    if c.get('type') == 'toolCall':
                                        activities.append({
                                            'text': f'👨‍💻 Jason: {c.get("name", "tool")}',
                                            'type': 'jason',
                                            'time': entry.get('timestamp')
                                        })
            except:
                pass
    
    # Return most recent 15
    return jsonify({'activities': activities[:15]})

# Missing API endpoints (found during audit)
@app.route('/api/candidates-list')
def api_candidates_list():
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT id, name, title, status, created_at FROM candidates ORDER BY created_at DESC')
    candidates = cursor.fetchall()
    db.close()
    return jsonify([dict(row) for row in candidates])

@app.route('/api/company/<int:company_id>', methods=['GET'])
def api_company_get(company_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM companies WHERE id = ?', (company_id,))
    company = cursor.fetchone()
    db.close()
    if company:
        return jsonify(dict(company))
    return jsonify({'error': 'Not found'}), 404

@app.route('/api/complete-week', methods=['POST'])
def api_complete_week():
    data = request.get_json()
    week_id = data.get('week_id')
    if not week_id:
        return jsonify({'error': 'week_id required'}), 400
    
    db = get_db()
    cursor = db.cursor()
    cursor.execute('UPDATE weekly_reviews SET completed = 1 WHERE id = ?', (week_id,))
    db.commit()
    db.close()
    return jsonify({'success': True})

@app.route('/api/submission', methods=['GET', 'POST'])
def api_submission():
    db = get_db()
    cursor = db.cursor()
    
    if request.method == 'POST':
        data = request.get_json()
        cursor.execute('''INSERT INTO submissions 
            (candidate_id, deal_id, company_id, status, sent_date, notes, stage)
            VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (data.get('candidate_id'), data.get('deal_id'), data.get('company_id'),
             data.get('status', 'Submitted'), data.get('sent_date'), data.get('notes', ''),
             data.get('stage', 'Sent')))
        db.commit()
        submission_id = cursor.lastrowid
        db.close()
        return jsonify({'id': submission_id, 'success': True})
    
    # GET all
    cursor.execute('SELECT * FROM submissions ORDER BY sent_date DESC')
    submissions = cursor.fetchall()
    db.close()
    return jsonify([dict(row) for row in submissions])

@app.route('/api/submissions-for-deal/<int:deal_id>')
def api_submissions_for_deal(deal_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM submissions WHERE deal_id = ? ORDER BY sent_date DESC', (deal_id,))
    submissions = cursor.fetchall()
    db.close()
    return jsonify([dict(row) for row in submissions])

@app.route('/api/submission/update-stage', methods=['POST'])
def api_submission_update_stage():
    data = request.get_json()
    submission_id = data.get('submission_id')
    new_stage = data.get('stage')
    
    if not submission_id or not new_stage:
        return jsonify({'error': 'submission_id and stage required'}), 400
    
    db = get_db()
    cursor = db.cursor()
    cursor.execute('UPDATE submissions SET status = ? WHERE id = ?', (new_stage, submission_id))
    db.commit()
    db.close()
    return jsonify({'success': True})

@app.route('/visits')
def visits_list():
    db = get_db()
    cursor = db.cursor()
    # Get all visits with company names
    cursor.execute('''
        SELECT v.id, v.visit_date, v.contact_name, v.notes, v.outcome, v.follow_up, v.created_at, c.name as company_name
        FROM visits v
        LEFT JOIN companies c ON v.company_id = c.id
        ORDER BY v.visit_date DESC
    ''')
    visits = cursor.fetchall()
    # Get companies for dropdown
    cursor.execute('SELECT id, name FROM companies ORDER BY name')
    companies = cursor.fetchall()
    db.close()
    return render_template('visits.html', visits=visits, companies=companies)

@app.route('/api/visit', methods=['POST'])
def api_add_visit():
    data = request.get_json()
    company_id = data.get('company_id')
    visit_date = data.get('visit_date')
    contact_name = data.get('contact_name')
    notes = data.get('notes', '')
    outcome = data.get('outcome', '')
    follow_up = data.get('follow_up', '')
    
    if not company_id or not visit_date:
        return jsonify({'error': 'company_id and visit_date required'}), 400
    
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''
        INSERT INTO visits (company_id, visit_date, contact_name, notes, outcome, follow_up)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (company_id, visit_date, contact_name, notes, outcome, follow_up))
    db.commit()
    visit_id = cursor.lastrowid
    db.close()
    return jsonify({'success': True, 'id': visit_id})

@app.route('/call-summariser', methods=['GET', 'POST'])
def call_summariser():
    """Call Summariser - Generate structured summaries from call notes"""
    from datetime import datetime
    import re
    
    summary = None
    
    if request.method == 'POST':
        notes = request.form.get('notes', '')
        contact_name = request.form.get('contact_name', '')
        call_type = request.form.get('call_type', 'Candidate Call')
        
        today = datetime.now().strftime('%d %B %Y')
        
        # Split into sentences for analysis
        sentences = re.split(r'[.!?]+', notes)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        # KEY INTEL CAPTURED - keywords for hiring/role intel
        intel_keywords = ['hiring', 'looking', 'project', 'start', 'available', 'role', 'need', 'want', 'budget', 'salary', 'timeline', 'position', 'opportunity', 'candidate', 'client', 'company', 'team', 'grow', 'expansion']
        key_intel = []
        for sent in sentences:
            sent_lower = sent.lower()
            if any(kw in sent_lower for kw in intel_keywords):
                key_intel.append(sent)
        
        # CANDIDATE/CLIENT ASSESSMENT - sentiment and concerns
        positive_phrases = ['great', 'excellent', 'good', 'interested', 'keen', 'enthusiastic', 'positive', 'strong', 'impressive', 'qualified', 'perfect', 'best']
        concern_phrases = ['concern', 'worry', 'hesitant', 'difficult', 'challenge', 'problem', 'issue', 'but', 'however', 'unfortunately', 'not sure', 'maybe', 'consider']
        
        positives = [s for s in sentences if any(p in s.lower() for p in positive_phrases)]
        concerns = [s for s in sentences if any(c in s.lower() for c in concern_phrases)]
        
        assessment = {
            'positives': positives,
            'concerns': concerns
        }
        
        # ACTION ITEMS - keywords for commitments/actions
        action_keywords = ['will', 'going to', 'follow up', 'send', 'call', 'email', 'book', 'schedule', 'next', 'prepare', 'review', 'submit', 'arrange', 'confirm', 'check']
        action_items = []
        for sent in sentences:
            sent_lower = sent.lower()
            if any(ak in sent_lower for ak in action_keywords):
                action_items.append(sent)
        
        # NEXT STEPS - extract dates/timeframes
        date_patterns = [
            r'\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*',
            r'\d{1,2}/\d{1,2}',
            r'next week',
            r'this week',
            r'monday|tuesday|wednesday|thursday|friday|saturday|sunday',
            r'tomorrow',
            r'in \d+ (days?|weeks?)',
            r'by (?:end of )?(?:this week|next week|month)'
        ]
        
        next_steps = []
        for sent in sentences:
            sent_lower = sent.lower()
            for pattern in date_patterns:
                if re.search(pattern, sent_lower):
                    next_steps.append(sent)
                    break
        
        summary = {
            'date': today,
            'contact': contact_name,
            'type': call_type,
            'key_intel': key_intel,
            'assessment': assessment,
            'action_items': action_items,
            'next_steps': next_steps,
            'raw_notes': notes
        }
    
    return render_template('call_summariser.html', summary=summary)
@app.route('/market-heatmap')
def market_heatmap():
    """Market Heat Map - analyze job adverts for strategic intelligence"""
    from collections import Counter
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute('SELECT title, tier, sector, location, role_type FROM job_adverts')
    adverts = cursor.fetchall()
    total_adverts = len(adverts)
    
    cursor.execute('SELECT COUNT(DISTINCT name) FROM companies')
    total_companies = cursor.fetchone()[0]
    
    # Counters
    roles = Counter()
    locations = Counter()
    sectors = Counter()
    tiers = Counter()
    role_sector = {}  # role -> sector -> count
    gc_data = []
    
    for a in adverts:
        role = a['role_type'] or a['title'] or 'Unknown'
        tier = a['tier'] or 'Unknown'
        sector = a['sector'] or 'Unknown'
        loc = a['location'] or 'Unknown'
        
        roles[role] += 1
        locations[loc] += 1
        sectors[sector] += 1
        tiers[tier] += 1
        
        if role not in role_sector:
            role_sector[role] = Counter()
        role_sector[role][sector] += 1
        
        if 'Gold Coast' in loc:
            gc_data.append({'role_type': role, 'tier': tier, 'sector': sector})
    
    # Top items
    top_role, top_role_count = roles.most_common(1)[0] if roles else ('N/A', 0)
    top_location, top_location_count = locations.most_common(1)[0] if locations else ('N/A', 0)
    top_sector, top_sector_count = sectors.most_common(1)[0] if sectors else ('N/A', 0)
    top_tier = tiers.most_common(1)[0][0] if tiers else 'N/A'
    
    tier1_count = tiers.get('Tier 1', 0)
    tier1_pct = round(tier1_count / total_adverts * 100) if total_adverts else 0
    
    max_role = max(roles.values()) if roles else 1
    max_loc = max(locations.values()) if locations else 1
    
    role_ranking = [{'name': r, 'count': c, 'pct': round(c / max_role * 100)} for r, c in roles.most_common(15)]
    location_ranking = [{'name': l, 'count': c, 'pct': round(c / max_loc * 100)} for l, c in locations.most_common(10)]
    
    # Heatmap data
    all_sectors = sorted(sectors.keys())
    heatmap_rows = []
    for role, count in roles.most_common(15):
        values = [role_sector.get(role, {}).get(s, 0) for s in all_sectors]
        heatmap_rows.append({'role': role, 'cells': values, 'total': count})
    
    # Tier breakdown
    tier_breakdown = []
    for t, c in tiers.most_common():
        tier_breakdown.append({'name': t, 'count': c, 'pct': round(c / total_adverts * 100)})
    
    # Sector breakdown
    sector_breakdown = []
    for s, c in sectors.most_common():
        sector_breakdown.append({'name': s, 'count': c, 'pct': round(c / total_adverts * 100)})
    
    # Gold Coast roles
    gc_counter = Counter()
    for g in gc_data:
        gc_counter[(g['role_type'], g['tier'], g['sector'])] += 1
    gc_roles = [{'role_type': k[0], 'tier': k[1], 'sector': k[2], 'count': v} for k, v in gc_counter.most_common()]
    gc_count = len(gc_data)
    
    updated = datetime.now().strftime('%d %b %Y')
    
    db.close()
    return render_template('market_heatmap.html',
        total_adverts=total_adverts, total_companies=total_companies,
        top_role=top_role, top_role_count=top_role_count,
        top_location=top_location, top_location_count=top_location_count,
        top_sector=top_sector, top_sector_count=top_sector_count,
        top_tier=top_tier, tier1_count=tier1_count, tier1_pct=tier1_pct,
        role_ranking=role_ranking, location_ranking=location_ranking,
        sectors=all_sectors, heatmap_rows=heatmap_rows,
        tier_breakdown=tier_breakdown, sector_breakdown=sector_breakdown,
        gc_roles=gc_roles, gc_count=gc_count, updated=updated)


@app.route('/revenue-modeler')
def revenue_modeler():
    """Revenue Modeler — Year 1 earnings projection"""
    return send_file('revenue-modeler.html')


@app.route('/the-vault')
def the_vault():
    """The Vault — Talent Intelligence Hub"""
    import json
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''
        SELECT id, name, title, current_company, specialism, years_experience,
               salary_band, location, mobility, flight_risk, known_offers,
               who_wants_them, relationship_score, last_contact, next_follow_up, notes
        FROM candidates
        ORDER BY relationship_score DESC, name ASC
    ''')
    rows = cursor.fetchall()
    candidates_data = []
    for r in rows:
        candidates_data.append({
            'id': r['id'],
            'name': r['name'],
            'title': r['title'] or '',
            'current_company': r['current_company'] or '',
            'specialism': r['specialism'] or '',
            'years_experience': r['years_experience'] or 0,
            'salary_band': r['salary_band'] or '',
            'location': r['location'] or '',
            'mobility': r['mobility'] or '',
            'flight_risk': r['flight_risk'] or '',
            'known_offers': r['known_offers'] or '',
            'who_wants_them': r['who_wants_them'] or '',
            'relationship_score': r['relationship_score'] or 1,
            'last_contact': r['last_contact'] or None,
            'next_follow_up': r['next_follow_up'] or None,
            'notes': r['notes'] or '',
        })
    db.close()
    candidates_json = json.dumps(candidates_data, default=str)
    return send_file('the-vault.html', mimetype='text/html')


@app.route('/war-room')
def war_room():
    """War Room — Strategic command center for Day 1 prep"""
    db = get_db()
    cursor = db.cursor()
    
    # Stats
    stats = {}
    cursor.execute('SELECT COUNT(*) FROM companies')
    stats['companies'] = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM decision_makers')
    stats['contacts'] = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM projects')
    stats['projects'] = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM leads')
    stats['leads'] = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM candidates')
    stats['candidates'] = cursor.fetchone()[0]
    
    # Tier breakdown
    cursor.execute("SELECT COUNT(*) FROM companies WHERE tier='1' OR tier='Tier 1'")
    stats['tier1'] = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM companies WHERE tier='2' OR tier='Tier 2'")
    stats['tier2'] = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM companies WHERE tier='3' OR tier='Tier 3'")
    stats['tier3'] = cursor.fetchone()[0]
    stats['untiered'] = stats['companies'] - stats['tier1'] - stats['tier2'] - stats['tier3']
    
    total = max(stats['companies'], 1)
    stats['tier1_pct'] = round(stats['tier1'] / total * 100)
    stats['tier2_pct'] = round(stats['tier2'] / total * 100)
    stats['tier3_pct'] = round(stats['tier3'] / total * 100)
    stats['untiered_pct'] = 100 - stats['tier1_pct'] - stats['tier2_pct'] - stats['tier3_pct']
    
    # Verified contacts (have email or phone)
    cursor.execute("SELECT COUNT(*) FROM decision_makers WHERE (email IS NOT NULL AND email != '' AND email NOT LIKE 'TBC%') OR (phone IS NOT NULL AND phone != '')")
    stats['verified_contacts'] = cursor.fetchone()[0]
    stats['verified_pct'] = round(stats['verified_contacts'] / max(stats['contacts'], 1) * 100)
    
    # Priority targets — companies with most projects, sorted by project count
    cursor.execute('''
        SELECT c.id, c.name, c.tier, c.sector, c.location,
               COUNT(DISTINCT p.id) as project_count,
               (SELECT COUNT(*) FROM decision_makers dm WHERE dm.company_id = c.id) as contact_count
        FROM companies c
        LEFT JOIN projects p ON p.company_id = c.id OR p.builder_id = c.id
        GROUP BY c.id
        ORDER BY project_count DESC, contact_count DESC
        LIMIT 8
    ''')
    rows = cursor.fetchall()
    targets = []
    for i, r in enumerate(rows):
        priority_class = 'priority-hot' if i < 3 else ('priority-warm' if i < 6 else 'priority-build')
        action = 'Call' if i < 3 else ('Visit' if i < 6 else 'Research')
        action_class = 'action-call' if i < 3 else ('action-visit' if i < 6 else 'action-research')
        targets.append({
            'id': r['id'], 'name': r['name'], 'sector': r['sector'],
            'project_count': r['project_count'], 'contact_count': r['contact_count'],
            'priority_class': priority_class, 'action': action, 'action_class': action_class
        })
    
    # Sector breakdown
    cursor.execute("SELECT sector, COUNT(*) as cnt FROM companies WHERE sector IS NOT NULL AND sector != '' GROUP BY sector ORDER BY cnt DESC LIMIT 6")
    sector_rows = cursor.fetchall()
    max_sector = max([r['cnt'] for r in sector_rows]) if sector_rows else 1
    colors = ['var(--accent)', 'var(--primary)', '#2ecc71', '#9b59b6', '#e67e22', '#1abc9c']
    sectors = [{'name': r['sector'], 'count': r['cnt'], 'pct': round(r['cnt'] / max_sector * 100), 'color': colors[i % len(colors)]} for i, r in enumerate(sector_rows)]
    
    # Market intel
    market_intel = [
        {'tag': 'MEGA PROJECT', 'tag_class': 'tag-project', 'title': 'Gold Coast Light Rail Stage 3', 'detail': 'John Holland / ACCIONA Alliance — PM: Chris Fraser — completing 2026'},
        {'tag': 'COMPLETION', 'tag_class': 'tag-completion', 'title': 'The Standard — McNab', 'detail': 'Senior PM: Simon Rua — team winding down 2026'},
        {'tag': 'COMPLETION', 'tag_class': 'tag-completion', 'title': 'Albatross Ave — Mosaic', 'detail': 'CM: Daniel Batchelor — completing 2026'},
        {'tag': 'HIRING', 'tag_class': 'tag-hiring', 'title': f'{stats["leads"]} active leads from job boards', 'detail': 'GC area, $150k+ white-collar construction roles'},
        {'tag': 'PROJECT', 'tag_class': 'tag-project', 'title': f'{stats["projects"]} tracked projects across Gold Coast & SEQ', 'detail': 'Pipeline mapped with builder PMs & estimated completions'},
    ]
    
    # 2026 completions
    cursor.execute("SELECT name, builder_name, project_manager_name FROM projects WHERE estimated_end LIKE '2026%' ORDER BY estimated_end")
    comp_rows = cursor.fetchall()
    completions_2026 = [{'name': r['name'], 'builder': r['builder_name'] or '—', 'pm': r['project_manager_name']} for r in comp_rows]
    
    db.close()
    return render_template('war_room.html', stats=stats, targets=targets, sectors=sectors,
                          market_intel=market_intel, completions_2026=completions_2026)


@app.route('/pipeline-command')
def pipeline_command():
    """Pipeline Command — Tactical outbound assault center"""
    db = get_db()
    cursor = db.cursor()

    # Stats
    stats = {}
    cursor.execute('SELECT COUNT(*) FROM companies')
    stats['companies'] = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM decision_makers')
    stats['contacts'] = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM projects')
    stats['projects'] = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM leads')
    stats['leads'] = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM candidates')
    stats['candidates'] = cursor.fetchone()[0]

    # Pipeline cards — Tier 1 & 2 companies with contacts
    cursor.execute('''
        SELECT c.id, c.name as company, c.tier, c.sector, c.location,
               dm.name as contact, dm.email, dm.phone, dm.linkedin, dm.title,
               'Pipeline research' as role
        FROM companies c
        LEFT JOIN decision_makers dm ON dm.company_id = c.id
        WHERE c.tier IN ('1', 'Tier 1', '2', 'Tier 2')
        AND (dm.name IS NOT NULL AND dm.name != '')
        ORDER BY c.tier ASC, c.name ASC
        LIMIT 20
    ''')
    deal_rows = cursor.fetchall()

    pipeline_map = []
    for r in deal_rows:
        pipeline_map.append({
            'id': r['id'], 'company': r['company'], 'tier': r['tier'] or '—',
            'sector': r['sector'] or '—', 'location': r['location'] or '—',
            'contact': r['contact'] or '—', 'email': r['email'] or '—',
            'phone': r['phone'] or '—', 'linkedin': r['linkedin'] or '—',
            'role': r['role'] or '—'
        })

    pipeline = {
        'map': pipeline_map,
        'qualify': [],
        'proposal': [],
        'negotiate': [],
        'placed': []
    }

    # Top contacts for quick access
    cursor.execute('''
        SELECT dm.name, dm.title, dm.email, dm.phone, dm.linkedin, c.name as company
        FROM decision_makers dm
        JOIN companies c ON c.id = dm.company_id
        WHERE dm.email IS NOT NULL AND dm.email != '' AND dm.email NOT LIKE 'TBC%'
        AND c.tier IN ('1', 'Tier 1', '2', 'Tier 2')
        ORDER BY c.tier ASC
        LIMIT 12
    ''')
    contact_rows = cursor.fetchall()
    top_contacts = [
        {'name': r['name'], 'title': r['title'] or '—', 'company': r['company'],
         'email': r['email'] or '', 'phone': r['phone'] or '', 'linkedin': r['linkedin'] or ''}
        for r in contact_rows
    ]

    # Outreach sequence — top 5 Tier 1 companies
    cursor.execute('''
        SELECT c.name as company, dm.name as contact, 'Cold outreach' as action,
               'Research their current projects and send LinkedIn connection + email' as subject,
               'linkedin' as channel
        FROM companies c
        LEFT JOIN decision_makers dm ON dm.company_id = c.id
        WHERE c.tier IN ('1', 'Tier 1')
        AND dm.name IS NOT NULL AND dm.name != ''
        ORDER BY c.name ASC
        LIMIT 5
    ''')
    seq_rows = cursor.fetchall()
    outreach_sequence = [
        {'company': r['company'], 'contact': r['contact'], 'action': r['action'],
         'subject': r['subject'], 'channel': r['channel']}
        for r in seq_rows
    ]

    # Sector breakdown
    sector_breakdown = {'developers': 0, 'builders': 0, 'civil': 0, 'qs': 0, 'govt': 0}
    cursor.execute("SELECT sector FROM companies WHERE sector IS NOT NULL AND sector != ''")
    for row in cursor.fetchall():
        s = (row['sector'] or '').lower()
        if 'developer' in s or 'property' in s: sector_breakdown['developers'] += 1
        elif 'builder' in s: sector_breakdown['builders'] += 1
        elif 'civil' in s: sector_breakdown['civil'] += 1
        elif 'qs' in s or 'consultancy' in s: sector_breakdown['qs'] += 1
        else: sector_breakdown['govt'] += 1

    # Days to Day 1 at Lead Group (May 4, 2026)
    from datetime import date
    day1 = date(2026, 5, 4)
    today = date.today()
    days_to_lead = (day1 - today).days

    outreach_metrics = {
        'day1_target': min(len([c for c in top_contacts if c['email']]), 10),
        'li_target': 15,
        'week1_conversations': '5-8',
        'month1_interviews': '3-5',
        'quarterly_target': '1-2'
    }

    db.close()
    return render_template('pipeline-command.html',
                          stats=stats, pipeline=pipeline,
                          top_contacts=top_contacts,
                          outreach_sequence=outreach_sequence,
                          outreach_metrics=outreach_metrics,
                          sector_breakdown=sector_breakdown,
                          days_to_lead=days_to_lead)


@app.route('/network-radar')
def network_radar():
    """Network Radar — Coverage analysis & enrichment sprint planner"""
    import json
    db = get_db()
    cursor = db.cursor()
    
    # Companies with contact info
    cursor.execute('''
        SELECT comp.id, comp.name, comp.tier, comp.website, comp.sector,
               COUNT(ct.id) as contact_count,
               SUM(CASE WHEN ct.email IS NOT NULL AND ct.email != '' THEN 1 ELSE 0 END) as email_count,
               SUM(CASE WHEN ct.phone IS NOT NULL AND ct.phone != '' THEN 1 ELSE 0 END) as phone_count,
               (SELECT ct2.contact_name FROM contacts ct2 WHERE ct2.company_id = comp.id 
                ORDER BY CASE WHEN ct2.email IS NOT NULL AND ct2.email != '' THEN 1 ELSE 0 END +
                         CASE WHEN ct2.phone IS NOT NULL AND ct2.phone != '' THEN 1 ELSE 0 END DESC
                LIMIT 1) as top_contact
        FROM companies comp
        LEFT JOIN contacts ct ON comp.id = ct.company_id
        GROUP BY comp.id
        ORDER BY comp.name
    ''')
    all_companies = cursor.fetchall()
    
    # Stats
    total = len(all_companies)
    blind = 0  # no contacts
    gaps = 0   # has contacts but no email/phone
    partial = 0  # has either email or phone
    full = 0   # has both email and phone
    
    network = []
    for comp in all_companies:
        name = comp['name'] or 'Unknown'
        tier = comp['tier'] or ''
        contact_count = comp['contact_count'] or 0
        email_count = comp['email_count'] or 0
        phone_count = comp['phone_count'] or 0
        top_contact = comp['top_contact'] or ''
        
        # Status
        if contact_count == 0:
            status = 'blind'
            status_display = 'No Contacts'
            blind += 1
        elif email_count == 0 and phone_count == 0:
            status = 'gaps'
            status_display = 'Named, No Info'
            gaps += 1
        elif email_count > 0 and phone_count > 0:
            status = 'full'
            status_display = 'Ready'
            full += 1
        else:
            status = 'partial'
            status_display = 'Partial'
            partial += 1
        
        # Tier classification
        tier_clean = tier.strip()
        if 'Tier 1' in tier_clean or tier_clean == 'T1':
            tier_class = 't1'
        elif 'Tier 2' in tier_clean or tier_clean == 'T2':
            tier_class = 't2'
        elif 'Tier 3' in tier_clean or tier_clean == 'T3':
            tier_class = 't3'
        elif 'Government' in tier_clean:
            tier_class = 'govt'
        elif 'Developer' in tier_clean:
            tier_class = 'dev'
        elif 'Consultant' in tier_clean:
            tier_class = 'consult'
        else:
            tier_class = 't3'
        
        # Priority
        is_tier1 = 'Tier 1' in tier_clean or tier_clean == 'T1'
        is_tier2 = 'Tier 2' in tier_clean or tier_clean == 'T2'
        
        if status == 'blind' and (is_tier1 or is_tier2):
            priority = 0
        elif status == 'blind' or status == 'gaps':
            priority = 1
        elif status == 'partial':
            priority = 2
        else:
            priority = 3
        
        network.append({
            'name': name,
            'tier': tier_clean,
            'tier_display': tier_clean if tier_clean else '—',
            'tier_class': tier_class,
            'contact_count': contact_count,
            'email_count': email_count,
            'phone_count': phone_count,
            'top_contact': top_contact,
            'status': status,
            'status_display': status_display,
            'status_class': status,
            'priority': priority,
            'sector': comp['sector'] or '',
        })
    
    # Sort: urgent first, then by name
    network.sort(key=lambda x: (x['priority'], x['name']))
    
    stats = {
        'total_companies': total,
        'blind': blind,
        'gaps': gaps,
        'partial': partial,
        'full': full,
    }
    
    # Coverage score
    coverage_score = round((partial + full) / total * 100) if total > 0 else 0
    
    # Quick wins — contactable RIGHT NOW
    cursor.execute('''
        SELECT ct.contact_name, ct.company, ct.type as title, ct.email, ct.phone,
               ct.relationship_score, comp.name as company_name, comp.tier as company_tier
        FROM contacts ct
        LEFT JOIN companies comp ON ct.company_id = comp.id
        WHERE (ct.email IS NOT NULL AND ct.email != '') OR (ct.phone IS NOT NULL AND ct.phone != '')
        ORDER BY 
            CASE WHEN ct.email IS NOT NULL AND ct.phone IS NOT NULL THEN 0
                 WHEN ct.phone IS NOT NULL THEN 1
                 ELSE 2 END,
            ct.contact_name
    ''')
    contactable = cursor.fetchall()
    
    quick_wins = []
    for ct in contactable:
        quick_wins.append({
            'name': ct['contact_name'] or 'TBC',
            'title': ct['title'] or '',
            'company': ct['company_name'] or ct['company'] or ct.get('contact_company') or '',
            'tier': ct['company_tier'] or '',
            'email': ct['email'] or '',
            'phone': ct['phone'] or '',
            'has_both': (ct['email'] and ct['phone']),
        })
    
    # Hot leads for sidebar
    cursor.execute('''
        SELECT company, sector, lead_score, hiring_manager, hirer_email,
               CASE WHEN hiring_manager IS NOT NULL AND hiring_manager != '' AND hirer_email IS NOT NULL THEN 1 ELSE 0 END as actionable
        FROM leads 
        WHERE lead_score >= 70 
        ORDER BY lead_score DESC
        LIMIT 5
    ''')
    hot_leads = cursor.fetchall()
    
    # Sprint plan
    remaining = blind + gaps
    weekly = max(1, round(remaining / 4))
    
    sprint_weeks = [
        {
            'label': 'Week 1 (Apr 7-13)',
            'goal': f'Enrich {weekly} Tier 1 & 2 blind spots — find the decision makers',
            'tasks': [
                f'LinkedIn: "Construction Manager" + "Gold Coast" → {weekly} companies',
                f'Find named contacts at {weekly} Tier 1/Tier 2 blind companies',
                'Hunter.io lookup for any emails found',
                'Send first batch of LinkedIn connection requests (5-10)',
            ]
        },
        {
            'label': 'Week 2 (Apr 14-20)',
            'goal': f'Enrich {weekly} more — start outreach to Week 1 connections',
            'tasks': [
                f'{weekly} more companies (Tier 2 + Government)',
                'Send intro messages to new LinkedIn connections',
                'Research upcoming GC project completions (hiring signals)',
                'Book 2 coffee chats with warm contacts',
            ]
        },
        {
            'label': 'Week 3 (Apr 21-27)',
            'goal': 'Coffee chat blitz — 3+ meetings with builders',
            'tasks': [
                'Attend 3+ coffee chats',
                'Fill remaining Tier 3 blind spots',
                'Identify candidates at target companies',
                'Pre-position candidates before Day 1',
            ]
        },
        {
            'label': 'Week 4 (Apr 28 - May 4)',
            'goal': 'Final sprint — every company has a warm contact',
            'tasks': [
                'Final coffee chats with remaining leads',
                "Send 'starting at Lead Group' broadcast to all connections",
                'Prepare Day 1 outreach list',
                'CRM complete: every company mapped, every contact warm',
            ]
        }
    ]
    
    db.close()
    return render_template('network_radar.html',
                          companies=network, stats=stats,
                          coverage_score=coverage_score,
                          quick_wins=quick_wins,
                          hot_leads=hot_leads,
                          sprint_weeks=sprint_weeks,
                          weekly_target=weekly,
                          contacts_by_status={'partial': partial, 'covered': full})


@app.route('/pre-launch')
def pre_launch():
    """Pre-Launch Command Center — Day 1 Countdown & Sprint Plan"""
    return send_file('pre-launch.html', mimetype='text/html')


@app.route('/interview-prep')
def interview_prep():
    """Interview Prep Generator — Role-specific interview questions from CRM data"""
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT COUNT(*) as c FROM companies')
    companies = cursor.fetchone()['c']
    cursor.execute('SELECT COUNT(*) as c FROM candidates WHERE status IN ("Active", "active")')
    candidates = cursor.fetchone()['c']
    cursor.execute('SELECT COUNT(*) as c FROM job_adverts')
    adverts = cursor.fetchone()['c']
    cursor.execute('SELECT COUNT(*) as c FROM projects')
    projects = cursor.fetchone()['c']
    return render_template('interview_prep.html',
                          stats={'companies': companies, 'candidates': candidates,
                                 'adverts': adverts, 'projects': projects})


@app.route('/api/crm_stats')
def api_crm_stats():
    """JSON stats for interview prep tool"""
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT COUNT(*) as c FROM companies')
    companies = cursor.fetchone()['c']
    cursor.execute('SELECT COUNT(*) as c FROM candidates WHERE status IN ("Active", "active")')
    candidates = cursor.fetchone()['c']
    cursor.execute('SELECT COUNT(*) as c FROM job_adverts')
    adverts = cursor.fetchone()['c']
    cursor.execute('SELECT COUNT(*) as c FROM projects')
    projects = cursor.fetchone()['c']
    return jsonify({'companies': companies, 'candidates': candidates,
                    'adverts': adverts, 'projects': projects})


@app.route('/sales-pipeline')
def sales_pipeline():
    """Sales Pipeline — Content-Driven Lead Conversion"""
    return send_file('sales-pipeline.html', mimetype='text/html')


@app.route('/content-command')
def content_command():
    """Content Command — Content Strategy & Tracking"""
    return send_file('content-command.html', mimetype='text/html')


@app.route('/call-campaign')
def call_campaign():
    """Call Campaign Command Center — Hot Leads Ready to Contact"""
    return send_file('call-campaign.html', mimetype='text/html')


# ============ JOBS ROUTES ============
@app.route('/jobs')
def jobs_list():
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''
        SELECT j.*, c.name as company_name 
        FROM jobs j 
        LEFT JOIN companies c ON j.company_id = c.id 
        ORDER BY j.created_at DESC
    ''')
    jobs = cursor.fetchall()
    cursor.execute('SELECT id, name FROM companies ORDER BY name')
    companies = cursor.fetchall()
    cursor.execute('SELECT id, contact_name, company FROM contacts ORDER BY contact_name')
    contacts = cursor.fetchall()
    db.close()
    return render_template('jobs.html', jobs=jobs, companies=companies, contacts=contacts)

@app.route('/api/job', methods=['POST'])
def api_add_job():
    data = request.json
    db = get_db()
    cursor = db.cursor()
    try:
        if data.get('id'):
            cursor.execute('''UPDATE jobs SET title=?, company_id=?, company=?, status=?, job_type=?, 
                location=?, salary_min=?, salary_max=?, description=?, requirements=?, source=?,
                contact_id=?, fee_percentage=?, estimated_fee=?, date_received=?, notes=?
                WHERE id=?''',
                (data.get('title'), data.get('company_id'), data.get('company'), data.get('status','Open'),
                 data.get('job_type'), data.get('location'), data.get('salary_min'), data.get('salary_max'),
                 data.get('description'), data.get('requirements'), data.get('source'),
                 data.get('contact_id'), data.get('fee_percentage',15.0), data.get('estimated_fee'),
                 data.get('date_received'), data.get('notes'), data['id']))
        else:
            cursor.execute('''INSERT INTO jobs (title, company_id, company, status, job_type, location,
                salary_min, salary_max, description, requirements, source, contact_id, fee_percentage,
                estimated_fee, date_received, notes)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                (data.get('title'), data.get('company_id'), data.get('company'), data.get('status','Open'),
                 data.get('job_type'), data.get('location'), data.get('salary_min'), data.get('salary_max'),
                 data.get('description'), data.get('requirements'), data.get('source'),
                 data.get('contact_id'), data.get('fee_percentage',15.0), data.get('estimated_fee'),
                 data.get('date_received'), data.get('notes')))
        db.commit()
        return jsonify({'success': True, 'id': cursor.lastrowid})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    finally:
        db.close()

@app.route('/api/job/<int:job_id>', methods=['DELETE'])
def api_delete_job(job_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('DELETE FROM jobs WHERE id=?', (job_id,))
    db.commit()
    db.close()
    return jsonify({'success': True})

@app.route('/api/job/<int:job_id>/status', methods=['POST'])
def api_update_job_status(job_id):
    data = request.json
    db = get_db()
    cursor = db.cursor()
    cursor.execute('UPDATE jobs SET status=? WHERE id=?', (data.get('status'), job_id))
    db.commit()
    db.close()
    return jsonify({'success': True})

# === MORNING HITLIST ENGINE ===

@app.route('/hitlist')
def hitlist():
    """Morning Hitlist — ranked priority 'who to call first' based on all CRM signals"""
    db = get_db()
    cursor = db.cursor()
    
    # Build a unified hitlist from all signals
    hits = []
    today = datetime.now().strftime('%Y-%m-%d')
    
    # 1. Decision makers with hiring signals (highest priority = revenue signal)
    cursor.execute("""
        SELECT dm.id, dm.name, dm.title, dm.hiring_signals, dm.relationship_score,
               dm.last_contact, dm.phone, dm.email, dm.linkedin, dm.notes,
               c.name as company_name, c.tier as company_tier, c.sector as company_sector,
               c.active_projects, c.upcoming_projects
        FROM decision_makers dm
        JOIN companies c ON dm.company_id = c.id
        WHERE dm.hiring_signals IS NOT NULL AND dm.hiring_signals != ''
        ORDER BY dm.relationship_score ASC
    """)
    for dm in cursor.fetchall():
        dm = dict(dm)
        signal_text = dm.get('hiring_signals', '') or ''
        
        # Score: hiring signal is gold
        score = 40
        
        # Tier bonus
        tier = (dm.get('company_tier') or '').upper()
        if tier in ('TIER 1', 'T1', '1'):
            score += 20
        elif tier in ('TIER 2', 'T2', '2'):
            score += 10
        
        # Stale relationship bonus (longer = more urgent to reconnect)
        last_contact = dm.get('last_contact') or ''
        if last_contact:
            try:
                days = (datetime.now() - datetime.strptime(last_contact[:10], '%Y-%m-%d')).days
                if days > 30:
                    score += min(15, days // 7)
            except:
                pass
        else:
            score += 10  # never contacted
        
        hits.append({
            'source': 'hiring_signal',
            'score': score,
            'name': dm['name'],
            'title': dm['title'],
            'company': dm['company_name'],
            'tier': tier,
            'sector': dm.get('company_sector', ''),
            'signal': signal_text,
            'last_contact': last_contact,
            'phone': dm.get('phone', ''),
            'email': dm.get('email', ''),
            'linkedin': dm.get('linkedin', ''),
            'action': '📞 Call — they\'re hiring!',
            'context': f"Tier {tier} — {signal_text[:120]}"
        })
    
    # 2. Contract wins (recent leads with contract_win type)
    cursor.execute("""
        SELECT l.company, l.what_it_means, l.action_trigger, l.created_at, l.source_url,
               c.tier as company_tier, c.sector as company_sector
        FROM leads l
        LEFT JOIN companies c ON l.company_id = c.id
        WHERE l.lead_score IS NOT NULL AND l.lead_score > 0
           OR l.source = 'Contract Win Alert'
        ORDER BY l.created_at DESC
        LIMIT 20
    """)
    for lead in cursor.fetchall():
        lead = dict(lead)
        score = 35
        
        tier = (lead.get('company_tier') or '').upper()
        if tier in ('TIER 1', 'T1', '1'):
            score += 20
        elif tier in ('TIER 2', 'T2', '2'):
            score += 10
        
        hits.append({
            'source': 'contract_win',
            'score': score,
            'name': 'TBD — new contact',
            'title': '',
            'company': lead['company'],
            'tier': tier,
            'sector': lead.get('company_sector', ''),
            'signal': lead.get('what_it_means', ''),
            'last_contact': 'Never',
            'phone': '',
            'email': '',
            'linkedin': '',
            'action': '🔍 Research & find decision maker',
            'context': f"{lead.get('what_it_means', '')[:120]}" if lead.get('what_it_means') else f"Contract win — reach out"
        })
    
    # 3. Stale T1/T2 contacts (no interaction > 21 days = risk of relationship decay)
    from datetime import timedelta
    twenty_one_ago = (datetime.now() - timedelta(days=21)).strftime('%Y-%m-%d')
    cursor.execute("""
        SELECT co.id, co.name, co.tier, co.sector, co.active_projects,
               MAX(c.last_interaction) as last_interaction
        FROM companies co
        LEFT JOIN contacts c ON c.company = co.name
        WHERE co.tier IN ('Tier 1', 'T1', 'Tier 2', 'T2', '1', '2')
        GROUP BY co.id
        HAVING last_interaction IS NULL OR last_interaction < ?
        ORDER BY last_interaction ASC
        LIMIT 15
    """, (twenty_one_ago,))
    for comp in cursor.fetchall():
        comp = dict(comp)
        tier = (comp.get('tier') or '').upper()
        score = 25
        if tier in ('TIER 1', 'T1', '1'):
            score += 15
        elif tier in ('TIER 2', 'T2', '2'):
            score += 8
        
        last_int = comp.get('last_interaction') or 'Never'
        
        hits.append({
            'source': 'relationship_decay',
            'score': score,
            'name': 'Any DM at this company',
            'title': '',
            'company': comp['name'],
            'tier': tier,
            'sector': comp.get('sector', ''),
            'signal': comp.get('active_projects', ''),
            'last_contact': last_int,
            'phone': '',
            'email': '',
            'linkedin': '',
            'action': '💬 Check in — relationship going cold',
            'context': f"Last touch: {last_int}" if last_int and last_int != 'Never' else "No recorded interaction"
        })
    
    # Sort by score descending
    hits.sort(key=lambda x: -x['score'])
    
    # Compute stats
    hiring_signal_count = len([h for h in hits if h['source'] == 'hiring_signal'])
    contract_win_count = len([h for h in hits if h['source'] == 'contract_win'])
    stale_count = len([h for h in hits if h['source'] == 'relationship_decay'])
    
    db.close()
    
    return render_template('hitlist.html',
        hits=hits,
        total=len(hits),
        hiring_count=hiring_signal_count,
        contract_count=contract_win_count,
        stale_count=stale_count,
        today_date=datetime.now().strftime('%A, %d %B %Y')
    )

@app.route('/day-one-sim')
def day_one_sim():
    """Interactive Day One Simulator for Chris's first day at Lead Group"""
    return render_template('day-one-sim.html')

@app.route('/api/hitlist/click/<int:idx>', methods=['POST'])
def api_hitlist_click(idx):
    """Log a hitlist item as contacted"""
    data = request.json
    contact_id = data.get('contact_id')
    company = data.get('company')
    
    db = get_db()
    cursor = db.cursor()
    
    # Update decision maker last_contact if we have the ID
    if contact_id and data.get('source') == 'hiring_signal':
        cursor.execute('''
            UPDATE decision_makers SET last_contact = ?, notes = COALESCE(notes, '') || '\n' || ?
            WHERE id = ?
        ''', (datetime.now().strftime('%Y-%m-%d'), f"[{datetime.now().strftime('%d %b')}] Hitlist outreach", contact_id))
        db.commit()
    
    db.close()
    return jsonify({'success': True})
if __name__ == '__main__':
    init_db()
    app.run(host='127.0.0.1', port=8090, debug=False, use_reloader=False)

# === MORNING HITLIST ENGINE ===

@app.route('/hitlist')
def hitlist():
    """Morning Hitlist — ranked priority 'who to call first' based on all CRM signals"""
    db = get_db()
    cursor = db.cursor()
    
    # Build a unified hitlist from all signals
    hits = []
    today = datetime.now().strftime('%Y-%m-%d')
    
    # 1. Decision makers with hiring signals (highest priority = revenue signal)
    cursor.execute("""
        SELECT dm.id, dm.name, dm.title, dm.hiring_signals, dm.relationship_score,
               dm.last_contact, dm.phone, dm.email, dm.linkedin, dm.notes,
               c.name as company_name, c.tier as company_tier, c.sector as company_sector,
               c.active_projects, c.upcoming_projects
        FROM decision_makers dm
        JOIN companies c ON dm.company_id = c.id
        WHERE dm.hiring_signals IS NOT NULL AND dm.hiring_signals != ''
        ORDER BY dm.relationship_score ASC
    """)
    for dm in cursor.fetchall():
        dm = dict(dm)
        signal_text = dm.get('hiring_signals', '') or ''
        
        # Score: hiring signal is gold
        score = 40
        
        # Tier bonus
        tier = (dm.get('company_tier') or '').upper()
        if tier in ('TIER 1', 'T1', '1'):
            score += 20
        elif tier in ('TIER 2', 'T2', '2'):
            score += 10
        
        # Stale relationship bonus (longer = more urgent to reconnect)
        last_contact = dm.get('last_contact') or ''
        if last_contact:
            try:
                days = (datetime.now() - datetime.strptime(last_contact[:10], '%Y-%m-%d')).days
                if days > 30:
                    score += min(15, days // 7)
            except:
                pass
        else:
            score += 10  # never contacted
        
        hits.append({
            'source': 'hiring_signal',
            'score': score,
            'name': dm['name'],
            'title': dm['title'],
            'company': dm['company_name'],
            'tier': tier,
            'sector': dm.get('company_sector', ''),
            'signal': signal_text,
            'last_contact': last_contact,
            'phone': dm.get('phone', ''),
            'email': dm.get('email', ''),
            'linkedin': dm.get('linkedin', ''),
            'action': '📞 Call — they\'re hiring!',
            'context': f"Tier {tier} — {signal_text[:120]}"
        })
    
    # 2. Contract wins (recent leads with contract_win type)
    cursor.execute("""
        SELECT l.company, l.what_it_means, l.action_trigger, l.created_at, l.source_url,
               c.tier as company_tier, c.sector as company_sector
        FROM leads l
        LEFT JOIN companies c ON l.company_id = c.id
        WHERE l.lead_score IS NOT NULL AND l.lead_score > 0
           OR l.source = 'Contract Win Alert'
        ORDER BY l.created_at DESC
        LIMIT 20
    """)
    for lead in cursor.fetchall():
        lead = dict(lead)
        score = 35
        
        tier = (lead.get('company_tier') or '').upper()
        if tier in ('TIER 1', 'T1', '1'):
            score += 20
        elif tier in ('TIER 2', 'T2', '2'):
            score += 10
        
        hits.append({
            'source': 'contract_win',
            'score': score,
            'name': 'TBD — new contact',
            'title': '',
            'company': lead['company'],
            'tier': tier,
            'sector': lead.get('company_sector', ''),
            'signal': lead.get('what_it_means', ''),
            'last_contact': 'Never',
            'phone': '',
            'email': '',
            'linkedin': '',
            'action': '🔍 Research & find decision maker',
            'context': f"{lead.get('what_it_means', '')[:120]}" if lead.get('what_it_means') else f"Contract win — reach out"
        })
    
    # 3. Stale T1/T2 contacts (no interaction > 21 days = risk of relationship decay)
    from datetime import timedelta
    twenty_one_ago = (datetime.now() - timedelta(days=21)).strftime('%Y-%m-%d')
    cursor.execute("""
        SELECT co.id, co.name, co.tier, co.sector, co.active_projects,
               MAX(c.last_interaction) as last_interaction
        FROM companies co
        LEFT JOIN contacts c ON c.company = co.name
        WHERE co.tier IN ('Tier 1', 'T1', 'Tier 2', 'T2', '1', '2')
        GROUP BY co.id
        HAVING last_interaction IS NULL OR last_interaction < ?
        ORDER BY last_interaction ASC
        LIMIT 15
    """, (twenty_one_ago,))
    for comp in cursor.fetchall():
        comp = dict(comp)
        tier = (comp.get('tier') or '').upper()
        score = 25
        if tier in ('TIER 1', 'T1', '1'):
            score += 15
        elif tier in ('TIER 2', 'T2', '2'):
            score += 8
        
        last_int = comp.get('last_interaction') or 'Never'
        
        hits.append({
            'source': 'relationship_decay',
            'score': score,
            'name': 'Any DM at this company',
            'title': '',
            'company': comp['name'],
            'tier': tier,
            'sector': comp.get('sector', ''),
            'signal': comp.get('active_projects', ''),
            'last_contact': last_int,
            'phone': '',
            'email': '',
            'linkedin': '',
            'action': '💬 Check in — relationship going cold',
            'context': f"Last touch: {last_int}" if last_int and last_int != 'Never' else "No recorded interaction"
        })
    
    # Sort by score descending
    hits.sort(key=lambda x: -x['score'])
    
    # Compute stats
    hiring_signal_count = len([h for h in hits if h['source'] == 'hiring_signal'])
    contract_win_count = len([h for h in hits if h['source'] == 'contract_win'])
    stale_count = len([h for h in hits if h['source'] == 'relationship_decay'])
    
    db.close()
    
    return render_template('hitlist.html',
        hits=hits,
        total=len(hits),
        hiring_count=hiring_signal_count,
        contract_count=contract_win_count,
        stale_count=stale_count,
        today_date=datetime.now().strftime('%A, %d %B %Y')
    )

@app.route('/day-one-sim')
def day_one_sim():
    """Interactive Day One Simulator for Chris's first day at Lead Group"""
    return render_template('day-one-sim.html')

@app.route('/api/hitlist/click/<int:idx>', methods=['POST'])
def api_hitlist_click(idx):
    """Log a hitlist item as contacted"""
    data = request.json
    contact_id = data.get('contact_id')
    company = data.get('company')
    
    db = get_db()
    cursor = db.cursor()
    
    # Update decision maker last_contact if we have the ID
    if contact_id and data.get('source') == 'hiring_signal':
        cursor.execute('''
            UPDATE decision_makers SET last_contact = ?, notes = COALESCE(notes, '') || '\n' || ?
            WHERE id = ?
        ''', (datetime.now().strftime('%Y-%m-%d'), f"[{datetime.now().strftime('%d %b')}] Hitlist outreach", contact_id))
        db.commit()
    
    db.close()
    return jsonify({'success': True})
