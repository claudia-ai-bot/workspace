# MEMORY.md - Long-Term Memory

## Active Projects

### Trading Challenge (Started: Mar 7, 2026)
**Goal:** Generate 10% ROI ($1000 AUD → $1100) in 28 days via IBKR paper trading

**Setup:**
- Platform: IBKR paper trading (Chris executes, Claudia advises)
- Timeframe: 28 days from Mar 7
- Style: Mixed (surprise approach)
- Constraints: No specific sectors off-limits, go wild

**Deliverable:** Trading Playbook with:
- Market analysis (March 2026 sectors/trends)
- Technical signals & entry/exit rules
- Risk management framework
- Position sizing strategy
- Daily trading checklist

**Daily time:** 5 minutes for execution (not time-sensitive — can execute anytime same trading day)
**Status:** Playbook COMPLETE (Mar 8). Ready to launch Monday Mar 10.
**Strategy approach:** Day/swing trades. Chris pulls data (tickers + RSI/MACD/price), Claudia analyzes + gives entry/stop/target + position sizing

**Data solution:** Alpha Vantage API (free, no IBKR access needed)
- API Key: OCXEW1TRCQRZ2K2G (stored safely)
- Provides: Real-time quotes, volume, daily momentum
- Scanner: trading-scanner-monday.py (fully built & tested)
- Output: trading-monday-results.json (5 best setups with entry/stop/target)

**Monday workflow (READY):**
1. Claudia runs `python3 trading-scanner-monday.py` at 6 AM AEST Monday
2. Scanner pulls data for 12 candidate stocks (tech, energy, industrials)
3. Identifies best setups: momentum + volume + entry/stop/target ready
4. Outputs: Top 5 trades with exact execution parameters
5. Chris: Open IBKR, confirm charts, execute trades anytime Monday
6. Position sizing already calculated (max $20 loss per trade)

---

## Tasks & Reminders

### Tomorrow (Mar 8, 2026) - URGENT
- **Create new Telegram group for trading challenge**
  - Name suggestion: "10% ROI Trading Challenge" or "Trading War Room"
  - Invite Claudia (this bot)
  - Purpose: Daily scans, trade fills, P/L logs, strategy adjustments
  - This will be the hub for all Monday+ trading updates

---

## New Projects (Approved)

### SEQ Construction Opportunity Monitor (24/7 Daemon)
**Status:** APPROVED & CONFIRMED (Mar 7, 2026) - Requirements phase

**Goal:** Automated lead generation for white-collar construction recruitment in SEQ
- Monitor construction project announcements 24/7
- Extract hiring needs + decision makers
- Rank opportunities by fit
- Send daily briefing with top 5-10 leads
- Research automation (LinkedIn, web, company data)

**Value Prop (Chris's words):**
> "Traditional recruiting: 5 hrs/day admin, 3 hrs relationship building
> 24/7 OpenClaw: Bot does 5 hrs overnight, you wake to 10 qualified leads ranked by fit"

**Time savings:** ~3 hours/day of manual research
**Quality gain:** Data-driven lead scoring vs gut-feel
**Cost:** ~$0 (just VPS electricity)

**Pending:** Answer 7 requirement questions in recruitment group
1. Data sources (council tenders, LinkedIn, BuilderTV, etc.)
2. Project criteria (value range, sectors, geography, hiring stage)
3. Decision maker roles (PM, Director, HR, Estimator, Safety, etc.)
4. Briefing format (email, Telegram, CSV, dashboard, Slack)
5. Ranking priorities (size, timing, fit, competition, seniority)
6. Research depth (names only vs full background)
7. Outreach automation level (manual, templates, auto-send, tracking)

**UI/UX Enhancement:** Telegram Mini App Dashboard - Phase 2
- Real-time P/L tracker, trade management, analytics
- Built AFTER Monday fundamentals proven working (Week 2+)
- Decision: Phased approach (solid trading first, shiny UI second)

**Phase 1 (Week 1):** Text briefings + manual execution (proven & rock solid)
**Phase 2 (Week 2+):** Telegram Mini App dashboard (beautiful, interactive)

---

## Lessons Learned
- **Write everything down immediately.** Session restarts kill memory. MEMORY.md is persistence.
- **Create task files or reminders** when commitments span sessions.
- Don't rely on context carryover — assume fresh start.
- **Organization matters.** Separate themes (trading vs recruitment) into different spaces.
