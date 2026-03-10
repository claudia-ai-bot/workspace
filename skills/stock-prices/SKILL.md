---
name: stock-prices
description: Get real-time stock prices for any ticker. Returns current price, bid/ask spread, and recent change. Use for live market data without API delays.
---

# Stock Prices Skill

Fetch real-time stock prices instantly for tracking positions, P&L, and market moves.

## Usage

Get current prices for any stock ticker:

```bash
python3 scripts/get-prices.py NVDA TSM MPC SLB
```

## Output

```
NVDA: $188.50 (bid: 188.48, ask: 188.52) | +5.65% today
TSM: $341.20 (bid: 341.15, ask: 341.25) | +0.64% today
MPC: $225.30 (bid: 225.25, ask: 225.35) | +1.79% today
SLB: $48.75 (bid: 48.73, ask: 48.77) | +3.91% today
```

## Features

- Real-time bid/ask spreads
- Daily % change
- Multiple ticker support
- Fast, reliable data

## No Setup Required

Just run the script — it pulls data from yfinance (installed in most Python envs).
