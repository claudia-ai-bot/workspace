#!/bin/bash
# Restart SEQ CRM to pick up new routes
fuser -k 8090/tcp 2>/dev/null
sleep 2
cd /home/chris/.openclaw/workspace/seq-crm
nohup python3 app.py > /tmp/crm.log 2>&1 &
echo "SEQ CRM restarted (PID: $!)"
sleep 2
curl -s -o /dev/null -m 3 http://127.0.0.1:8090/ && echo "Dashboard: OK" || echo "Dashboard: FAIL"
curl -s -o /dev/null -m 3 http://127.0.0.1:8090/hitlist && echo "Hitlist: OK" || echo "Hitlist: may need route check"
curl -s -o /dev/null -m 3 http://127.0.0.1:8090/day-one-sim && echo "Day One Sim: OK" || echo "Day One Sim: may need route check"
