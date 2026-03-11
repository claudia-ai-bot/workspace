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
from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file
import json

app = Flask(__name__)
app.config['DATABASE'] = os.path.expanduser("~/.openclaw/workspace/seq-crm/crm.db")

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
    
    db.close()
    
    return render_template('dashboard.html', 
                         companies=company_count, 
                         dms=dm_count, 
                         warm=warm_count,
                         candidates=candidate_count,
                         deals=deal_count)

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

if __name__ == '__main__':
    init_db()
    app.run(host='127.0.0.1', port=8080, debug=True)
