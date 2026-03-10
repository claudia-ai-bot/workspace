# Monday Execution Guide
**10% ROI Trading Challenge - March 10, 2026**

---

## What Happens Monday Morning

**6 AM (or anytime before market):**
1. I run the scanner: `python3 trading-scanner-monday.py`
2. It pulls real stock data via Alpha Vantage API
3. Identifies the 5 best setups for the day
4. Outputs the results to: `trading-monday-results.json`
5. I send you the watchlist

---

## What You Do

### Step 1: Get the Watchlist (I'll send)
```
Expected output:
[1] NVDA - ENTRY: $177.82 | STOP: $172.49 | TARGET: $186.71 | SHARES: 3
[2] TSM  - ENTRY: $338.89 | STOP: $328.72 | TARGET: $355.83 | SHARES: 1
... etc (5 trades total)
```

### Step 2: Review Each Trade (2 min)
- Open IBKR charting
- Pull up each stock on 1-day chart
- Look at the entry price — does it look reasonable?
- If it's within ~1% of our entry, it's good

### Step 3: Execute Trades (5 min total)

**For each stock:**

1. **Market order** → Buy at the ENTRY price shown
2. **Set Stop Loss** → Create a sell order at STOP price
3. **Set Profit Target** → Create a sell order at TARGET price
4. **Leave it running** → IBKR handles the exits automatically

**Example (NVDA):**
```
BUY 3 shares @ $177.82 (ENTRY)
SET STOP @ $172.49 (automatic sell if price drops)
SET TARGET @ $186.71 (automatic sell if price rises)
```

### Step 4: Report Back
Once all trades are filled, just tell me:
```
"Executed: NVDA (3@$177.82), TSM (1@$338.89), SLB (14@$46.90)"
```

---

## Position Sizing Explained

**Max Loss Per Trade: $20**
- If you hit the stop loss, you lose $20 max
- Position size is already calculated (shown as SHARES)
- Don't change the share quantities

**Risk/Reward Ratio: 1:1.67 minimum**
- Risking $20 to make ~$27-30+ per trade
- Solid risk/reward for short-term trading

---

## Important Rules

✅ **DO:**
- Execute at or near the entry prices shown
- Use the exact stop-loss + target prices
- Leave stops/targets active (auto-exit)
- Take profits when they hit targets (don't be greedy)
- Accept losses if stopped out (move to next trade)

❌ **DON'T:**
- Change the entry prices (we've calculated them carefully)
- Move the stops (defeats risk management)
- Chase trades above entry (wait for next signal)
- Over-leverage (stick to position size)
- Revenge trade if you get stopped out

---

## What If Something Goes Wrong?

**"My entry price is way different from the scanner output"**
- Market moved since scan (normal, happens fast)
- Use your entry within ~2% tolerance
- Or skip that trade and wait for next signal

**"I can't execute all 5 trades at once"**
- That's OK — execute what you can during the day
- No rush, they're day trades but not time-sensitive
- Anytime Monday is fine

**"One of my trades closed at stop loss"**
- Good — stop losses work
- Accept the $20 loss, move on
- Log it: "SLB stopped out at $45.49"

---

## Daily Tracking

After each day, log your trades:

```
DATE: Mar 10, 2026
STOCK: NVDA
ENTRY: $177.82 @ 9:35 AM
EXIT: $186.71 @ 2:15 PM
PROFIT: +$26.67
STATUS: Hit target ✓
```

This helps me adjust strategy if needed.

---

## Timeline

- **Mar 10 (Monday):** First trade batch
- **Mar 11-31:** Daily scans, trading continues
- **Apr 4 (Saturday):** 28 days complete, review results
- **Goal:** $1,000 → $1,100 (10% return)

---

## Questions?

Hit me up anytime. That's what I'm here for. Let's crush this. 🚀
