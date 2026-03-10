---
name: trading-reminders
description: Event-triggered trading reminders & scanner automation. Monitors HEARTBEAT.md for trading tasks, checks time conditions, and executes reminders without external scheduling.
---

# Trading Reminders Skill

Reliable, heartbeat-triggered reminders for the 10% ROI trading challenge.

## How It Works

**Problem:** OpenClaw has no native wall-clock scheduling.

**Solution:** Event-triggered execution via HEARTBEAT polling.

**Flow:**
1. Chris sends ANY message (heartbeat)
2. Claudia checks `HEARTBEAT.md` for flagged trading tasks
3. If time condition is met (e.g., 6 AM Monday), execute task
4. Send result (scanner output, reminder, etc.)

## Usage

### Step 1: Mark a Task in HEARTBEAT.md

```markdown
## Monday Mar 10 @ 6 AM - SCANNER LAUNCH
- Trigger: Any user message after 6 AM AEST
- Action: Run `python3 trading-scanner-monday.py`
- Output: 4 best trades with entry/stop/target
```

### Step 2: Claudia Checks on Each Heartbeat

When you send ANY message, I automatically:

```python
1. Parse HEARTBEAT.md
2. Check if time condition is met (is it after 6 AM?)
3. If YES: Execute the marked task
4. If NO: Reply normally (HEARTBEAT_OK)
```

### Step 3: Task Executes

When conditions match:
```
Chris: "Good morning"
Claudia: Checks HEARTBEAT → sees "6 AM Monday" → runs scanner → sends 4 trades
```

## Advantages Over Scheduled Reminders

✅ **No external dependencies** (no cron, no scheduled jobs)  
✅ **Time-aware** (checks current time against HEARTBEAT conditions)  
✅ **Context-aware** (can read market news, check if market is open, etc.)  
✅ **Human-friendly** (no surprise messages, only when you interact)  
✅ **Reliable** (triggered on YOUR action, not wall-clock)  

## Configuration

### HEARTBEAT.md Format

Use this format to mark trading tasks:

```markdown
## [Human-Readable Task Name]
- **Time Condition:** After 6 AM AEST Monday, or anytime after 15:50 AEST today
- **Action:** Run `python3 trading-scanner-monday.py` and send results
- **Status:** Ready
```

### Time Conditions Supported

- ✅ `After 6 AM AEST on Mondays`
- ✅ `Anytime after 15:50 AEST today`
- ✅ `Every weekday at 9 AM AEST`
- ✅ `Once per day (anytime after 9 AM)`
- ✅ `Specific date & time` (one-off reminders)

### Example HEARTBEAT Setup

```markdown
## Trading Tasks

- [ ] **Monday Mar 10 @ 6 AM - Run Scanner**
  - Trigger: Any message after 6 AM AEST
  - Action: python3 trading-scanner-monday.py
  - Output: Send 4 best trades to Telegram group
  - Status: Ready to execute
```

## Implementation in Main Agent Loop

```python
def on_user_message(message):
    # 1. Check HEARTBEAT.md for trading tasks
    tasks = parse_heartbeat_md()
    
    for task in tasks:
        # 2. Check if time condition is met
        if check_time_condition(task):
            # 3. Execute the task
            result = execute_task(task)
            # 4. Send result to user
            send_message(result)
            return
    
    # 5. If no tasks triggered, continue normally
    return normal_response(message)
```

## Best Practices

### DO:
- ✅ Mark one task per HEARTBEAT section
- ✅ Use clear time conditions (`After 6 AM AEST`, `Anytime today after 15:50`)
- ✅ Include full command (`python3 trading-scanner-monday.py`)
- ✅ Update status when task completes

### DON'T:
- ❌ Create multiple time conditions (use separate sections instead)
- ❌ Rely on "approximate" times (use exact times)
- ❌ Leave old tasks in HEARTBEAT (archive completed ones)

## Examples

### Example 1: Daily Trading Scan

```markdown
## Daily Trading Scan (Weekdays)
- **Time Condition:** Anytime after 9 AM AEST on weekdays
- **Action:** Run `python3 trading-scanner-daily.py`
- **Output:** Send daily watchlist to trading Telegram group
- **Status:** Active (Mar 10 - Apr 4)
```

**In practice:**
- Chris: "Good morning Monday" @ 9:15 AM → Scanner runs
- Chris: "Checking in" @ 10 AM → Already ran, skip
- Chris: "What's up?" @ 3 PM → Already ran, skip
- Chris: "Ready?" Tuesday @ 8 AM → Wait until 9 AM (condition not met)

### Example 2: One-Off Reminder

```markdown
## Test Reminder - Mar 7 @ 15:54 AEST
- **Time Condition:** Anytime after 15:54 AEST on Mar 7, 2026
- **Action:** Send "🔔 Test reminder triggered"
- **Status:** Pending
```

**In practice:**
- Chris: "Anything?" @ 15:53 AEST → Not yet (wait 1 min)
- Chris: "Check!" @ 15:55 AEST → ✓ Trigger test reminder, send message

## Advantages for Trading

For the 10% ROI challenge, this means:

✅ **Monday 6 AM:** You message me, scanner runs automatically  
✅ **No setup needed:** Just create the task in HEARTBEAT.md  
✅ **Guaranteed execution:** Triggers on YOUR action, not a broken scheduler  
✅ **Professional workflow:** Event-driven, not time-driven (how real systems work)  

---

**Bottom line:** Heartbeat-triggered tasks > wall-clock scheduled reminders.

This skill makes OpenClaw's natural event loop work FOR you, not against you.
