#!/usr/bin/env python3
"""Daily CRM Briefing Generator"""
import sqlite3
from datetime import datetime, timedelta

conn = sqlite3.connect('/home/chris/.openclaw/workspace/seq-crm/crm.db')
cur = conn.cursor()

print("=" * 50)
print(f"📋 DAILY RECRUITMENT BRIEFING - {datetime.now().strftime('%d %b %Y')}")
print("=" * 50)

# Pipeline
cur.execute("SELECT COUNT(*), SUM(fee_value) FROM deals WHERE stage NOT IN ('Won', 'Lost')")
pipeline_count, pipeline_value = cur.fetchone()
print(f"\n🎯 PIPELINE")
print(f"   Open Deals: {pipeline_count or 0}")
print(f"   Total Value: ${pipeline_value or 0:,}")

# Deals by stage
print(f"\n📊 DEALS BY STAGE")
cur.execute("SELECT stage, COUNT(*), SUM(fee_value) FROM deals GROUP BY stage")
for stage, count, value in cur.fetchall():
    print(f"   {stage}: {count} (${value or 0:,})")

# Candidates
print(f"\n👥 CANDIDATES")
cur.execute("SELECT COUNT(*) FROM candidates WHERE status = 'Active'")
print(f"   Active: {cur.fetchone()[0]}")

cur.execute("SELECT COUNT(*) FROM candidates WHERE next_follow_up <= date('now')")
due = cur.fetchone()[0]
print(f"   Follow-ups due: {due}")

# Companies
print(f"\n🏢 COMPANIES")
cur.execute("SELECT COUNT(*) FROM companies")
print(f"   Total: {cur.fetchone()[0]}")

# Recent activity
print(f"\n📝 RECENT ACTIVITY")
cur.execute("SELECT type, notes, created_at FROM activities ORDER BY created_at DESC LIMIT 5")
for act_type, notes, created in cur.fetchall():
    print(f"   - {notes[:50]}")

# Action items
print(f"\n⚡ ACTION ITEMS")
cur.execute("""SELECT c.name, c.next_follow_up FROM candidates c 
               WHERE c.next_follow_up <= date('now') AND c.status = 'Active' 
               LIMIT 5""")
for name, follow_up in cur.fetchall():
    print(f"   - Follow up with {name}")

conn.close()
print("\n" + "=" * 50)
