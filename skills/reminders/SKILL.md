---
name: reminders
description: Schedule reminders at specific times and dates. One-time or recurring (daily, weekly, monthly). Reminders are sent via Telegram at the scheduled time.
---

# Reminders Skill

Set reminders that fire at exact times. No more forgotten tasks.

## Usage

### Set a one-time reminder:
```bash
python3 scripts/remind.py "Check IBKR positions" "09:30 2026-03-10"
```

### Set a recurring reminder:
```bash
python3 scripts/remind.py "Daily market check" "09:30" --recurring daily
python3 scripts/remind.py "Weekly review" "Sunday 10:00" --recurring weekly
python3 scripts/remind.py "Monthly rebalance" "1st of month 09:00" --recurring monthly
```

### View all reminders:
```bash
python3 scripts/remind.py --list
```

### Delete a reminder:
```bash
python3 scripts/remind.py --delete <id>
```

## Time Format

- **One-time:** `HH:MM YYYY-MM-DD` (e.g., `14:30 2026-03-15`)
- **Daily:** `HH:MM` (e.g., `09:30`)
- **Weekly:** `DAY HH:MM` (e.g., `Monday 14:00`)
- **Monthly:** `Nth of month HH:MM` (e.g., `1st of month 09:00`)

## Features

- ✅ One-time reminders
- ✅ Daily, weekly, monthly recurring
- ✅ Sent via Telegram (direct message)
- ✅ Stores reminders in JSON
- ✅ Easy list/delete management
- ✅ Works in background (cron-based)

## Storage

Reminders stored in: `~/.openclaw/workspace/reminders.json`

## How It Works

1. You set a reminder with the script
2. OpenClaw cron scheduler checks at the scheduled time
3. When time matches, reminder fires → Telegram DM sent
4. One-time reminders auto-delete after firing
5. Recurring reminders stay active indefinitely

## Examples

```bash
# Trading challenge check (daily at market open)
python3 scripts/remind.py "Check trading positions" "09:30" --recurring daily

# Weekly Friday review
python3 scripts/remind.py "Weekly P&L review" "Friday 16:00" --recurring weekly

# One-time: SEQ recruitment campaign kickoff
python3 scripts/remind.py "Launch SEQ construction outreach" "08:00 2026-03-15"
```
