#!/bin/bash
# SEQ CRM Auto-Restart Script
while true; do
    cd /home/chris/.openclaw/workspace/seq-crm
    python3 app.py >> crm.log 2>&1
    echo "CRM crashed, restarting in 5s..." >> crm.log
    sleep 5
done
