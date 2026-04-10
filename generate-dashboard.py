#!/usr/bin/env python3
"""SEQ CRM Dashboard Generator"""

import sqlite3

DB_PATH = '/home/chris/.openclaw/workspace/seq-crm/crm.db'

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def fmt(n):
    return '{:,}'.format(n) if n else '0'

def get_stats():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT SUM(fee_value) as total FROM deals WHERE stage NOT IN ('Placed', 'Lost', 'Won')")
    pipeline = cur.fetchone()['total'] or 0
    cur.execute("SELECT COUNT(*) as cnt FROM deals WHERE stage NOT IN ('Placed', 'Lost', 'Won')")
    active_deals = cur.fetchone()['cnt']
    cur.execute("SELECT COUNT(*) as cnt FROM deals WHERE stage IN ('Placed', 'Won')")
    placements = cur.fetchone()['cnt']
    cur.execute("SELECT COUNT(*) as cnt FROM contacts")
    contacts = cur.fetchone()['cnt']
    cur.execute("SELECT COUNT(*) as cnt FROM companies")
    companies = cur.fetchone()['cnt']
    cur.execute("SELECT COUNT(*) as cnt FROM candidates")
    candidates = cur.fetchone()['cnt']
    conn.close()
    return {'pipeline': pipeline, 'active_deals': active_deals, 'placements': placements, 'contacts': contacts, 'companies': companies, 'candidates': candidates}

def get_deals():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM deals ORDER BY fee_value DESC")
    deals = [dict(r) for r in cur.fetchall()]
    conn.close()
    return deals

def get_companies():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM companies ORDER BY name")
    companies = [dict(r) for r in cur.fetchall()]
    conn.close()
    return companies

def get_contacts():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM contacts ORDER BY contact_name")
    contacts = [dict(r) for r in cur.fetchall()]
    conn.close()
    return contacts

def get_candidates():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM candidates ORDER BY name")
    candidates = [dict(r) for r in cur.fetchall()]
    conn.close()
    return candidates

def deal_card(d):
    prob = d.get('probability', 20)
    return '<div class="deal-card" onclick="viewDeal(' + str(d['id']) + ')"><div class="deal-company">' + d['client'] + '</div><div class="deal-role">' + str(d.get('role','')) + '</div><div class="deal-value"><span class="deal-fee">$' + fmt(d.get('fee_value', 0)) + '</span><span class="deal-prob">' + str(prob) + '%</span></div></div>'

def company_card(c):
    tier = c.get('tier', 'Tier 2')
    tier_num = '1' if tier == 'Tier 1' else '2'
    return '<div class="contact-card" onclick="viewCompany(' + str(c['id']) + ')"><div class="contact-header"><div><div class="contact-name">' + c['name'] + '</div><div class="contact-company">' + str(c.get('sector','N/A')) + '</div></div><span class="tier tier-' + tier_num + '">' + tier + '</span></div><div class="contact-meta">📍 ' + str(c.get('location','QLD')) + '</div><div class="contact-meta">Active: ' + str(c.get('active_projects','N/A')) + '</div></div>'

def contact_card(c):
    score = c.get('relationship_score', 5) or 5
    score_class = 'high' if score >= 7 else 'med' if score >= 4 else 'low'
    return '<div class="contact-card" onclick="viewContact(' + str(c['id']) + ')"><div class="contact-header"><div><div class="contact-name">' + c['contact_name'] + '</div><div class="contact-company">' + c['company'] + '</div></div><span class="score ' + score_class + '">' + str(score) + '</span></div><div class="contact-meta">' + str(c.get('type','Contact')) + '</div><div class="contact-meta">Last: ' + str(c.get('last_interaction','N/A')) + '</div></div>'

def candidate_card(c):
    return '<div class="contact-card" onclick="viewCandidate(' + str(c['id']) + ')"><div class="contact-header"><div><div class="contact-name">' + c['name'] + '</div><div class="contact-company">' + str(c.get('title','N/A')) + '</div></div></div><div class="contact-meta">🏢 ' + str(c.get('current_company','TBC')) + '</div><div class="contact-meta">💼 ' + str(c.get('specialism','N/A')) + ' • ' + str(c.get('years_experience',0)) + ' yrs</div></div>'

def generate_html():
    stats = get_stats()
    deals = get_deals()
    companies = get_companies()
    contacts = get_contacts()
    candidates = get_candidates()
    
    stage_order = ['Lead', 'Contacted', 'Interview', 'Offer', 'Placed', 'Lost']
    deals_by_stage = {s: [d for d in deals if d.get('stage', 'Lead') == s] for s in stage_order}
    other_deals = [d for d in deals if d.get('stage', 'Lead') not in stage_order]
    if other_deals:
        deals_by_stage['Lead'] = deals_by_stage.get('Lead', []) + other_deals
    
    html = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SEQ CRM</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{--primary:#1e3a5f;--accent:#ff6b35;--success:#2ecc71;--bg:#f5f6fa;--card:#ffffff;--text:#2c3e50;--text-light:#7f8c8d;--border:#e0e4e8}
body{font-family:'Inter',sans-serif;background:var(--bg);color:var(--text);min-height:100vh}
.header{background:var(--primary);color:white;padding:15px 30px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:100;box-shadow:0 2px 10px rgba(0,0,0,0.1)}
.logo{font-size:20px;font-weight:800}.logo span{color:var(--accent)}
.nav{display:flex;gap:8px}
.nav-btn{background:rgba(255,255,255,0.1);border:none;color:white;padding:10px 18px;border-radius:8px;cursor:pointer;font-size:14px;font-weight:500}
.nav-btn:hover{background:rgba(255,255,255,0.2)}.nav-btn.active{background:var(--accent)}
.header-actions{display:flex;gap:10px}
.search{background:rgba(255,255,255,0.1);border:none;color:white;padding:10px 15px;border-radius:8px;width:200px;font-size:14px}
.add-btn{background:var(--accent);border:none;color:white;padding:10px 18px;border-radius:8px;cursor:pointer;font-weight:600;font-size:14px}
.stats{display:grid;grid-template-columns:repeat(6,1fr);gap:20px;padding:25px 30px}
.stat-card{background:var(--card);border-radius:12px;padding:20px;box-shadow:0 2px 8px rgba(0,0,0,0.04);border:1px solid var(--border)}
.stat-label{font-size:12px;color:var(--text-light);text-transform:uppercase;margin-bottom:8px}
.stat-value{font-size:28px;font-weight:800;color:var(--primary)}
.stat-sub{font-size:12px;color:var(--text-light);margin-top:5px}
.stat-value.accent{color:var(--accent)}.stat-value.success{color:var(--success)}
.section{padding:0 30px 30px}
.section-title{font-size:18px;font-weight:700;margin-bottom:15px;color:var(--primary)}
.kanban{display:grid;grid-template-columns:repeat(5,1fr);gap:15px}
.column{background:var(--card);border-radius:12px;padding:15px;min-height:350px;border:1px solid var(--border)}
.column-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:15px;padding-bottom:10px;border-bottom:2px solid var(--border)}
.column-lead .column-header{border-color:#95a5a6}.column-contacted .column-header{border-color:#3498db}.column-interview .column-header{border-color:#f1c40f}.column-offer .column-header{border-color:#e67e22}.column-placed .column-header{border-color:#2ecc71}
.column-title{font-weight:700;font-size:13px;text-transform:uppercase}
.column-lead .column-title{color:#95a5a6}.column-contacted .column-title{color:#3498db}.column-interview .column-title{color:#f1c40f}.column-offer .column-title{color:#e67e22}.column-placed .column-title{color:#2ecc71}
.column-count{background:var(--bg);padding:3px 10px;border-radius:12px;font-size:12px;font-weight:600}
.deal-card{background:var(--bg);border-radius:10px;padding:12px;margin-bottom:10px;cursor:pointer;transition:all 0.2s;border:1px solid transparent}
.deal-card:hover{border-color:var(--accent);transform:translateY(-2px);box-shadow:0 4px 12px rgba(0,0,0,0.08)}
.deal-company{font-weight:700;font-size:14px;margin-bottom:3px}
.deal-role{font-size:12px;color:var(--text-light);margin-bottom:8px}
.deal-value{display:flex;justify-content:space-between;align-items:center}
.deal-fee{font-weight:700;color:var(--success);font-size:14px}
.deal-prob{font-size:11px;padding:2px 6px;border-radius:4px;background:#f0f0f0;color:var(--text-light)}
.add-deal{width:100%;padding:10px;border:2px dashed var(--border);border-radius:8px;background:transparent;color:var(--text-light);cursor:pointer;font-size:13px}
.add-deal:hover{border-color:var(--accent);color:var(--accent)}
.grid-4{display:grid;grid-template-columns:repeat(4,1fr);gap:15px}
.contact-card{background:var(--card);border-radius:12px;padding:15px;border:1px solid var(--border);transition:all 0.2s;cursor:pointer}
.contact-card:hover{border-color:var(--accent);box-shadow:0 4px 12px rgba(0,0,0,0.08)}
.contact-header{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px}
.contact-name{font-weight:700;font-size:14px}
.contact-company{font-size:12px;color:var(--text-light)}
.score{width:32px;height:32px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:12px}
.score.high{background:#d5f4e6;color:#27ae60}.score.med{background:#fef3cd;color:#f39c12}.score.low{background:#f8d7da;color:#dc3545}
.contact-meta{font-size:11px;color:var(--text-light);margin-bottom:10px}
.tier{font-size:10px;padding:2px 6px;border-radius:3px;font-weight:600;text-transform:uppercase}
.tier-1{background:#dbeafe;color:#2563eb}.tier-2{background:#fef3cd;color:#d97706}
.fab{position:fixed;bottom:30px;right:30px;width:60px;height:60px;border-radius:50%;background:var(--accent);color:white;border:none;font-size:28px;cursor:pointer;box-shadow:0 4px 20px rgba(255,107,53,0.4);display:flex;align-items:center;justify-content:center;z-index:50}
.fab:hover{transform:scale(1.1)}
.tabs{display:flex;gap:5px;padding:0 30px;border-bottom:1px solid var(--border);background:var(--card)}
.tab{padding:15px 20px;cursor:pointer;border-bottom:3px solid transparent;font-weight:600;font-size:14px;color:var(--text-light)}
.tab:hover{color:var(--primary)}.tab.active{color:var(--primary);border-bottom-color:var(--accent)}
.tab-content{display:none}.tab-content.active{display:block}
.modal-overlay{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.5);z-index:200;justify-content:center;align-items:center}
.modal-overlay.active{display:flex}
.modal{background:var(--card);border-radius:16px;width:90%;max-width:500px;max-height:80vh;overflow-y:auto;box-shadow:0 20px 60px rgba(0,0,0,0.3)}
.modal-header{padding:20px;border-bottom:1px solid var(--border);display:flex;justify-content:space-between;align-items:center}
.modal-title{font-size:18px;font-weight:700}
.modal-close{background:none;border:none;font-size:24px;cursor:pointer;color:var(--text-light)}
.modal-body{padding:20px}
.form-group{margin-bottom:15px}
.form-label{display:block;font-size:12px;font-weight:600;text-transform:uppercase;color:var(--text-light);margin-bottom:5px}
.form-input,.form-select{width:100%;padding:10px 12px;border:1px solid var(--border);border-radius:8px;font-size:14px}
.form-input:focus{outline:none;border-color:var(--accent)}
.form-row{display:grid;grid-template-columns:1fr 1fr;gap:15px}
.btn{padding:10px 20px;border-radius:8px;font-size:14px;font-weight:600;cursor:pointer;border:none}
.btn-primary{background:var(--accent);color:white}.btn-secondary{background:var(--bg);color:var(--text);border:1px solid var(--border)}
.form-actions{display:flex;gap:10px;justify-content:flex-end;margin-top:20px}
@media(max-width:1400px){.stats,.kanban,.grid-4{grid-template-columns:repeat(3,1fr)}}
@media(max-width:1024px){.stats,.kanban,.grid-4{grid-template-columns:repeat(2,1fr)}}
@media(max-width:768px){.stats,.kanban,.grid-4{grid-template-columns:1fr}.header{flex-direction:column}}
</style>
</head>
<body>
<header class="header">
<div class="logo">SEQ <span>CRM</span></div>
<nav class="nav">
<button class="nav-btn active" onclick="showTab('dashboard')">📊 Dashboard</button>
<button class="nav-btn" onclick="showTab('pipeline')">📋 Pipeline</button>
<button class="nav-btn" onclick="showTab('companies')">🏢 Companies</button>
<button class="nav-btn" onclick="showTab('contacts')">👥 Contacts</button>
<button class="nav-btn" onclick="showTab('candidates')">👔 Candidates</button>
</nav>
<div class="header-actions">
<input type="text" class="search" placeholder="🔍 Search...">
<button class="add-btn" onclick="showAddModal()">+ Add</button>
</div>
</header>

<div id="dashboard" class="tab-content active">
<div class="stats">
<div class="stat-card"><div class="stat-label">Pipeline Value</div><div class="stat-value accent">$''' + fmt(stats['pipeline']) + '''</div><div class="stat-sub">''' + str(stats['active_deals']) + ''' Active Deals</div></div>
<div class="stat-card"><div class="stat-label">Placements</div><div class="stat-value">''' + str(stats['placements']) + '''</div><div class="stat-sub">This Month</div></div>
<div class="stat-card"><div class="stat-label">Companies</div><div class="stat-value">''' + str(stats['companies']) + '''</div><div class="stat-sub">In Network</div></div>
<div class="stat-card"><div class="stat-label">Contacts</div><div class="stat-value">''' + str(stats['contacts']) + '''</div><div class="stat-sub">Decision Makers</div></div>
<div class="stat-card"><div class="stat-label">Candidates</div><div class="stat-value success">''' + str(stats['candidates']) + '''</div><div class="stat-sub">Active</div></div>
<div class="stat-card"><div class="stat-label">Win Rate</div><div class="stat-value">25%</div><div class="stat-sub">Last 30 Days</div></div>
</div>
<div class="section">
<div class="section-title">📋 Pipeline Overview</div>
<div class="kanban">
<div class="column column-lead"><div class="column-header"><span class="column-title">Lead</span><span class="column-count">''' + str(len(deals_by_stage.get('Lead', []))) + '''</span></div>
''' + ''.join([deal_card(d) for d in deals_by_stage.get('Lead', [])]) + '''
<button class="add-deal" onclick="showAddDealModal('Lead')">+ Add Deal</button></div>
<div class="column column-contacted"><div class="column-header"><span class="column-title">Contacted</span><span class="column-count">''' + str(len(deals_by_stage.get('Contacted', []))) + '''</span></div>
''' + ''.join([deal_card(d) for d in deals_by_stage.get('Contacted', [])]) + '''
<button class="add-deal" onclick="showAddDealModal('Contacted')">+ Add Deal</button></div>
<div class="column column-interview"><div class="column-header"><span class="column-title">Interview</span><span class="column-count">''' + str(len(deals_by_stage.get('Interview', []))) + '''</span></div>
''' + ''.join([deal_card(d) for d in deals_by_stage.get('Interview', [])]) + '''
<button class="add-deal" onclick="showAddDealModal('Interview')">+ Add Deal</button></div>
<div class="column column-offer"><div class="column-header"><span class="column-title">Offer</span><span class="column-count">''' + str(len(deals_by_stage.get('Offer', []))) + '''</span></div>
''' + ''.join([deal_card(d) for d in deals_by_stage.get('Offer', [])]) + '''
<button class="add-deal" onclick="showAddDealModal('Offer')">+ Add Deal</button></div>
<div class="column column-placed"><div class="column-header"><span class="column-title">Placed</span><span class="column-count">''' + str(len(deals_by_stage.get('Placed', []))) + '''</span></div>
''' + ''.join([deal_card(d) for d in deals_by_stage.get('Placed', [])]) + '''
</div></div></div></div>

<div id="pipeline" class="tab-content">
<div class="section"><div class="section-title">📋 All Deals</div>
<div style="background:var(--card);border-radius:12px;padding:20px;border:1px solid var(--border);">
<table style="width:100%;border-collapse:collapse;">
<tr style="border-bottom:2px solid var(--border);"><th style="text-align:left;padding:10px;font-size:12px;text-transform:uppercase;color:var(--text-light);">Client</th><th style="text-align:left;padding:10px;font-size:12px;text-transform:uppercase;color:var(--text-light);">Role</th><th style="text-align:left;padding:10px;font-size:12px;text-transform:uppercase;color:var(--text-light);">Stage</th><th style="text-align:right;padding:10px;font-size:12px;text-transform:uppercase;color:var(--text-light);">Fee</th><th style="text-align:right;padding:10px;font-size:12px;text-transform:uppercase;color:var(--text-light);">Prob</th></tr>
''' + ''.join(['<tr style="cursor:pointer;border-bottom:1px solid var(--border);" onclick="viewDeal(' + str(d['id']) + ')"><td style="padding:12px;font-weight:600;">' + d['client'] + '</td><td style="padding:12px;color:var(--text-light);">' + str(d.get('role','')) + '</td><td style="padding:12px;"><span class="tier tier-' + ('1' if d.get('stage') in ['Lead','Contacted'] else '2') + '">' + str(d.get('stage','Lead')) + '</span></td><td style="padding:12px;text-align:right;font-weight:700;color:var(--success);">$' + fmt(d.get('fee_value',0)) + '</td><td style="padding:12px;text-align:right;">' + str(d.get('probability',20)) + '%</td></tr>' for d in deals]) + '''
</table></div></div></div>

<div id="companies" class="tab-content"><div class="section"><div class="section-title">🏢 Companies (''' + str(len(companies)) + ''')</div><div class="grid-4">''' + ''.join([company_card(c) for c in companies]) + '''</div></div></div>
<div id="contacts" class="tab-content"><div class="section"><div class="section-title">👥 Contacts (''' + str(len(contacts)) + ''')</div><div class="grid-4">''' + ''.join([contact_card(c) for c in contacts]) + '''</div></div></div>
<div id="candidates" class="tab-content"><div class="section"><div class="section-title">👔 Candidates (''' + str(len(candidates)) + ''')</div><div class="grid-4">''' + ''.join([candidate_card(c) for c in candidates]) + '''</div></div></div>

<button class="fab" onclick="showAddModal()">+</button>

<div class="modal-overlay" id="addModal">
<div class="modal"><div class="modal-header"><span class="modal-title" id="modalTitle">Add New</span><button class="modal-close" onclick="closeModal()">×</button></div><div class="modal-body" id="modalBody"></div></div></div>

<script>
function showTab(t){document.querySelectorAll('.tab-content').forEach(x=>x.classList.remove('active'));document.querySelectorAll('.nav-btn').forEach(x=>x.classList.remove('active'));document.getElementById(t).classList.add('active');event.target.classList.add('active');}
function closeModal(){document.getElementById('addModal').classList.remove('active');}
function showAddModal(){document.getElementById('modalTitle').textContent='Add New';document.getElementById('modalBody').innerHTML='<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;"><button class="btn btn-primary" onclick="showAddCompany()">🏢 Company</button><button class="btn btn-primary" onclick="showAddContact()">👥 Contact</button><button class="btn btn-primary" onclick="showAddDealModal(\'Lead\')">📋 Deal</button><button class="btn btn-primary" onclick="showAddCandidate()">👔 Candidate</button></div>';document.getElementById('addModal').classList.add('active');}
function showAddCompany(){document.getElementById('modalTitle').textContent='Add Company';document.getElementById('modalBody').innerHTML='<form onsubmit="saveCompany(event)"><div class="form-group"><label class="form-label">Company Name</label><input type="text" name="name" class="form-input" required></div><div class="form-row"><div class="form-group"><label class="form-label">Sector</label><input type="text" name="sector" class="form-input"></div><div class="form-group"><label class="form-label">Location</label><input type="text" name="location" class="form-input"></div></div><div class="form-group"><label class="form-label">Active Projects</label><input type="text" name="active_projects" class="form-input"></div><div class="form-group"><label class="form-label">Tier</label><select name="tier" class="form-select"><option value="Tier 2">Tier 2</option><option value="Tier 1">Tier 1</option></select></div><div class="form-actions"><button type="button" class="btn btn-secondary" onclick="showAddModal()">Back</button><button type="submit" class="btn btn-primary">Save</button></div></form>';}
function saveCompany(e){e.preventDefault();const f=e.target;fetch('/api/company',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:f.name.value,sector:f.sector.value,location:f.location.value,active_projects:f.active_projects.value,tier:f.tier.value})}).then(r=>r.json()).then(d=>{alert('Company added!');location.reload();}).catch(e=>alert('Error: '+e));}
function showAddContact(){document.getElementById('modalTitle').textContent='Add Contact';document.getElementById('modalBody').innerHTML='<form onsubmit="saveContact(event)"><div class="form-group"><label class="form-label">Name</label><input type="text" name="contact_name" class="form-input" required></div><div class="form-group"><label class="form-label">Company</label><input type="text" name="company" class="form-input" required></div><div class="form-row"><div class="form-group"><label class="form-label">Type</label><select name="type" class="form-select"><option value="Decision Maker">Decision Maker</option><option value="Hiring Manager">Hiring Manager</option><option value="HR">HR</option></select></div><div class="form-group"><label class="form-label">Score</label><input type="number" name="relationship_score" class="form-input" value="5" min="1" max="10"></div></div><div class="form-group"><label class="form-label">Email</label><input type="email" name="email" class="form-input"></div><div class="form-group"><label class="form-label">Phone</label><input type="text" name="phone" class="form-input"></div><div class="form-actions"><button type="button" class="btn btn-secondary" onclick="showAddModal()">Back</button><button type="submit" class="btn btn-primary">Save</button></div></form>';}
function saveContact(e){e.preventDefault();const f=e.target;fetch('/api/contact',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({contact_name:f.contact_name.value,company:f.company.value,type:f.type.value,relationship_score:parseInt(f.relationship_score.value),email:f.email.value,phone:f.phone.value})}).then(r=>r.json()).then(d=>{alert('Contact added!');location.reload();}).catch(e=>alert('Error: '+e));}
function showAddDealModal(stage){document.getElementById('modalTitle').textContent='Add Deal';document.getElementById('modalBody').innerHTML='<form onsubmit="saveDeal(event)"><input type="hidden" name="stage" value="'+stage+'"><div class="form-group"><label class="form-label">Client/Company</label><input type="text" name="client" class="form-input" required></div><div class="form-group"><label class="form-label">Role</label><input type="text" name="role" class="form-input" placeholder="e.g. Project Manager"></div><div class="form-row"><div class="form-group"><label class="form-label">Fee ($)</label><input type="number" name="fee_value" class="form-input"></div><div class="form-group"><label class="form-label">Prob (%)</label><input type="number" name="probability" class="form-input" value="20" min="1" max="100"></div></div><div class="form-actions"><button type="button" class="btn btn-secondary" onclick="showAddModal()">Back</button><button type="submit" class="btn btn-primary">Save</button></div></form>';}
function saveDeal(e){e.preventDefault();const f=e.target;fetch('/api/lead',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({client:f.client.value,role:f.role.value,stage:f.stage.value,fee_value:parseInt(f.fee_value.value)||0,probability:parseInt(f.probability.value)||20})}).then(r=>r.json()).then(d=>{alert('Deal added!');location.reload();}).catch(e=>alert('Error: '+e));}
function showAddCandidate(){document.getElementById('modalTitle').textContent='Add Candidate';document.getElementById('modalBody').innerHTML='<form onsubmit="saveCandidate(event)"><div class="form-group"><label class="form-label">Name</label><input type="text" name="name" class="form-input" required></div><div class="form-group"><label class="form-label">Title</label><input type="text" name="title" class="form-input"></div><div class="form-row"><div class="form-group"><label class="form-label">Current Company</label><input type="text" name="current_company" class="form-input"></div><div class="form-group"><label class="form-label">Years Exp</label><input type="number" name="years_experience" class="form-input"></div></div><div class="form-group"><label class="form-label">Specialism</label><input type="text" name="specialism" class="form-input"></div><div class="form-group"><label class="form-label">Salary Band</label><input type="text" name="salary_band" class="form-input"></div><div class="form-actions"><button type="button" class="btn btn-secondary" onclick="showAddModal()">Back</button><button type="submit" class="btn btn-primary">Save</button></div></form>';}
function saveCandidate(e){e.preventDefault();const f=e.target;fetch('/api/candidate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:f.name.value,title:f.title.value,current_company:f.current_company.value,years_experience:parseInt(f.years_experience.value)||0,specialism:f.specialism.value,salary_band:f.salary_band.value})}).then(r=>r.json()).then(d=>{alert('Candidate added!');location.reload();}).catch(e=>alert('Error: '+e));}
function viewCompany(id){window.open('/company/'+id,'_blank');}
function viewContact(id){window.open('/contact/'+id,'_blank');}
function viewDeal(id){window.open('/lead/'+id,'_blank');}
function viewCandidate(id){window.open('/candidate/'+id,'_blank');}
</script>
</body>
</html>'''
    return html

if __name__ == '__main__':
    html = generate_html()
    with open('/home/chris/.openclaw/workspace/seq-crm/dashboard.html', 'w') as f:
        f.write(html)
    print('Dashboard generated!')
