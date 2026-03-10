# HEARTBEAT.md

## URGENT - Saturday 7 March @ 1pm AEST
→ **Airtable Setup Time**
→ If within 1 hour of 1pm (12pm-2pm): Flag immediately with "⏰ Airtable time! Ready?"
→ I'll walk you through the 30-min setup live in this chat
→ Need: Your email address only

---

# Keep this file empty (or with only comments) to skip heartbeat API calls.

# Add tasks below when you want the agent to check something periodically.

## TRADING CHALLENGE (This Chat Only)

- [x] **Trading Playbook** (Completed: Mar 8) — Full strategy ready
- [x] **Trading Group Setup** (DONE - Mar 9)
  - Group: "Trading Challenge" (-5218024251)
  - Ready for daily scans, fills, P/L, lessons
  
- [x] **Monday Mar 9 - SCANNER LAUNCH & TRADES OPENED** ⏰⏰⏰ COMPLETE
  - Scanned 12 candidates, found 5 setups (NVDA, TSM, SLB, DE, ASML)
  - All 5 trades executed as limit orders
  - Tracking file: memory/trading-log-2026-03-09.md
  
- [ ] **DAILY TRADING MONITOR** ⏰ Active Until Positions Close
  - Check each morning (or anytime Chris messages during market hours)
  - Pull current price for all 5 open positions
  - Log: Current price vs entry/stop/target
  - Alert if any stop hit or target hit
  - Update trading-log daily with unrealized P/L

---

## REMINDERS ⏰ (RUN EVERY HEARTBEAT)

**CRITICAL: Execute reminder checker during every heartbeat**

```bash
python3 ~/.openclaw/workspace/skills/reminders/scripts/check-reminders-aest.py
```

This script:
- Uses AEST timezone (UTC+10)
- Checks all active reminders in `~/.openclaw/workspace/reminders.json`
- Fires reminders within 5-minute windows (handles heartbeat polling jitter)
- Sends Telegram messages for matches
- Marks one-time reminders as inactive after firing
- Handles: one-time, daily, weekly, monthly reminders

**How to set reminders:**
```bash
# One-time (exact date & time in AEST)
python3 ~/.openclaw/workspace/skills/reminders/scripts/remind.py "Message" "10:30 2026-03-10"

# Daily (time in AEST, fires every day)
python3 ~/.openclaw/workspace/skills/reminders/scripts/remind.py "Message" "10:30" --recurring daily

# Weekly (day + time in AEST)
python3 ~/.openclaw/workspace/skills/reminders/scripts/remind.py "Message" "Monday 10:30" --recurring weekly

# Monthly
python3 ~/.openclaw/workspace/skills/reminders/scripts/remind.py "Message" "1st of month 10:30" --recurring monthly

# List all
python3 ~/.openclaw/workspace/skills/reminders/scripts/remind.py --list

# Delete
python3 ~/.openclaw/workspace/skills/reminders/scripts/remind.py --delete <ID>
```

**Key:** Reminders fire within ~5 minutes of scheduled time (heartbeat window). For exact timing, increase heartbeat frequency or set slightly earlier.

---

## SEQ CONSTRUCTION DAEMON (Recruitment Group Only)

**Discussion:** Use recruitment group ONLY for this project
- Answer 7 requirements in recruitment group
- Build daemon (Week 2-3)
- Daily briefings in recruitment group
