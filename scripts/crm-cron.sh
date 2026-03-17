#!/bin/bash
# CRM Agent Cron Runner
# Runs daily at 8am AEST to check CRM and spawn Tim

cd ~/.openclaw/workspace

# Log file
LOG=~/.openclaw/logs/crm-cron.log

echo "=== CRM Check $(date) ===" >> $LOG

# Check if CRM is running
if curl -s http://localhost:8090 > /dev/null 2>&1; then
    echo "CRM: OK" >> $LOG
else
    echo "CRM: DOWN - Restarting..." >> $LOG
    cd ~/.openclaw/workspace/seq-crm
    nohup python3 app.py >> ~/.openclaw/workspace/seq-crm/crm.log 2>&1 &
    sleep 2
    echo "CRM restarted" >> $LOG
fi

# Log deal count
DEALS=$(curl -s http://localhost:8090/api/deals 2>/dev/null | grep -o '"id"' | wc -l)
echo "Deals in pipeline: $DEALS" >> $LOG

echo "=== End CRM Check ===" >> $LOG
