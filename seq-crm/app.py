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
    
    db.commit()
    db.close()

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
    
    from datetime import datetime
    today = datetime.now().strftime('%d %B %Y')
    
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
                         today=today)

@app.route('/companies')
def companies_list():
    """List all companies"""
    db = get_db()
    cursor = db.cursor()
    
    search = request.args.get('search', '')
    
    if search:
        cursor.execute('SELECT * FROM companies WHERE name LIKE ? ORDER BY name', 
                      (f'%{search}%',))
    else:
        cursor.execute('SELECT * FROM companies ORDER BY name')
    
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
    
    db.close()
    
    return render_template('company_detail.html', company=company, dms=dms)

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
    db.close()
    
    return render_template('candidates.html', candidates=candidates, search=search)

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

@app.route('/api/lead', methods=['POST'])
def api_add_lead():
    data = request.json
    db = get_db()
    cursor = db.cursor()
    try:
        if data.get('id'):
            cursor.execute('''UPDATE leads SET date=?, company=?, intel_type=?, source=?, what_it_means=?, action_trigger=? WHERE id=?''',
                         (data.get('date'), data.get('company'), data.get('intel_type'), data.get('source'),
                          data.get('what_it_means'), data.get('action_trigger'), data.get('id')))
        else:
            cursor.execute('''INSERT INTO leads (date, company, intel_type, source, what_it_means, action_trigger) VALUES (?,?,?,?,?,?)''',
                         (data.get('date'), data.get('company'), data.get('intel_type'), data.get('source'),
                          data.get('what_it_means'), data.get('action_trigger')))
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
    dataAPI: Add/edit = request.json
    db = get_db()
    cursor = db.cursor()
    
    try:
        if 'id' in data and data['id']:
            cursor.execute('''
                UPDATE contacts 
                SET contact_name=?, company=?, type=?, relationship_score=?, 
                    last_interaction=?, interaction_type=?, personal_detail=?,
                    value_given=?, next_touch_date=?, notes=?
                WHERE id=?
            ''', (data.get('contact_name'), data.get('company'), data.get('type'),
                  data.get('relationship_score'), data.get('last_interaction'),
                  data.get('interaction_type'), data.get('personal_detail'),
                  data.get('value_given'), data.get('next_touch_date'),
                  data.get('notes'), data.get('id')))
        else:
            cursor.execute('''
                INSERT INTO contacts 
                (contact_name, company, type, relationship_score, last_interaction,
                 interaction_type, personal_detail, value_given, next_touch_date, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (data.get('contact_name'), data.get('company'), data.get('type'),
                  data.get('relationship_score'), data.get('last_interaction'),
                  data.get('interaction_type'), data.get('personal_detail'),
                  data.get('value_given'), data.get('next_touch_date'), data.get('notes')))
        
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
    cursor.execute('SELECT name FROM companies ORDER BY name')
    companies = [c[0] for c in cursor.fetchall()]
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
def mission_control():
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
    
    weighted_pipeline = deals_count * 50000
    total_deals = deals_count
    cv_submitted = max(candidates_count // 2, 0)
    cv_shortlisted = max(cv_submitted // 3, 0)
    interview = max(cv_shortlisted // 2, 0)
    offer = max(interview // 2, 0)
    placed = max(offer // 2, 0)
    cv_submitted_pct = 100 if candidates_count else 0
    shortlist_rate = 33 if cv_submitted else 0
    interview_rate = 50 if cv_shortlisted else 0
    offer_rate = 50 if interview else 0
    win_rate = 50 if offer else 0
    cv_bar_pct = min(cv_submitted_pct, 100)
    shortlist_bar_pct = min(shortlist_rate, 100)
    interview_bar_pct = min(interview_rate, 100)
    offer_bar_pct = min(offer_rate, 100)
    win_bar_pct = min(win_rate, 100)
    at_risk_clients = max(companies_count // 10, 0)
    
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
    cursor.execute('SELECT SUM(fee_value) as total FROM deals')
    total_fee_value = cursor.fetchone()['total'] or 0
    cursor.execute('SELECT AVG(fee_value) as avg FROM deals')
    avg_fee = cursor.fetchone()['avg'] or 0
    cursor.execute('SELECT AVG(days_to_fill) as avg FROM deals')
    avg_days = cursor.fetchone()['avg'] or 0
    cursor.execute("SELECT stage, COUNT(*) as count FROM deals GROUP BY stage")
    by_stage = cursor.fetchall()
    # Funnel metrics - use deals data
    submitted = total_deals
    interviews = max(1, total_deals // 2)
    offers = max(1, interviews // 2)
    placed = max(1, offers // 2)
    db.close()
    return render_template('recruitment_metrics.html',
                          companies_count=companies_count,
                          contacts_count=contacts_count,
                          candidates_count=candidates_count,
                          total_deals=total_deals,
                          total_fee_value=total_fee_value,
                          total_fee_achieved=0,
                          avg_fee=avg_fee,
                          avg_days=avg_days,
                          by_stage=by_stage,
                          active_candidates=candidates_count,
                          total_candidates=candidates_count,
                          submitted=submitted,
                          interviews=interviews,
                          offers=offers,
                          placed=placed,
                          cv_to_interview_rate=50,
                          interview_to_offer_rate=50,
                          offer_accept_rate=50,
                          by_source=[],
                          recent_placements=[])

def cron_jobs():
    import os
    jobs_path = '/home/chris/.openclaw/cron/jobs.json'
    if os.path.exists(jobs_path):
        return send_file(jobs_path, mimetype='application/json')
    return '{"jobs": []}', 404

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

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=8090, debug=False, use_reloader=False)
