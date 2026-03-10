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
    
    db.close()
    
    return render_template('dashboard.html', 
                         companies=company_count, 
                         dms=dm_count, 
                         warm=warm_count)

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
