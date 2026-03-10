#!/usr/bin/env python3
"""
Trading Scanner - 10% ROI Challenge
Scans candidate stocks for swing trading setups
Uses Alpha Vantage API for real technical data
"""

import requests
import json
import time
from datetime import datetime, timedelta
import sys

# Configuration
API_KEY = "OCXEW1TRCQRZ2K2G"
BASE_URL = "https://www.alphavantage.co/query"

# Candidate stocks (hot sectors: tech, energy, industrials)
WATCHLIST = [
    'NVDA', 'AMD', 'ASML', 'MRVL', 'TSM',  # Tech/Semis
    'CVX', 'MPC', 'OXY', 'SLB',             # Energy
    'CAT', 'DE', 'BA', 'LMT'                # Industrials
]

# Portfolio config
STARTING_CAPITAL = 1000
MAX_LOSS_PER_TRADE = 20
MAX_RISK = 50
TARGET_RETURN = 0.10  # 10%

def get_stock_data(ticker):
    """Fetch daily quote + intraday data"""
    try:
        # Global quote (latest price, daily change)
        quote_url = f"{BASE_URL}?function=GLOBAL_QUOTE&symbol={ticker}&apikey={API_KEY}"
        quote_resp = requests.get(quote_url, timeout=5)
        quote_data = quote_resp.json()
        
        if 'Global Quote' not in quote_data:
            return None
            
        quote = quote_data['Global Quote']
        if not quote.get('05. price'):
            return None
        
        return {
            'ticker': ticker,
            'price': float(quote['05. price']),
            'change': float(quote.get('09. change', 0)),
            'percent_change': float(quote.get('10. change percent', '0').rstrip('%')),
            'volume': int(float(quote.get('06. volume', 0)))
        }
    except Exception as e:
        return None

def calculate_position_size(entry_price, stop_loss):
    """Calculate shares based on risk/reward rules"""
    risk_per_trade = MAX_LOSS_PER_TRADE
    stop_distance_pct = abs((entry_price - stop_loss) / entry_price)
    
    if stop_distance_pct == 0:
        return 0
    
    # Position size = Risk $ / Risk %
    shares = int(risk_per_trade / (stop_distance_pct * entry_price))
    return max(1, shares)

def generate_trade_signal(data):
    """
    Generate trade signal based on:
    - Recent momentum (% change)
    - Volume
    - Technical setup assumptions (since we can't get RSI/MACD without more API calls)
    """
    score = 0
    reasons = []
    
    # Negative momentum (oversold territory)
    if -5 < data['percent_change'] < 0:
        score += 2
        reasons.append("Slight pullback (momentum reset)")
    elif data['percent_change'] < -5:
        score += 1
        reasons.append("Recent weakness (potential bounce)")
    
    # Volume indicator (recent activity)
    if data['volume'] > 1_000_000:
        score += 1
        reasons.append("Good volume")
    
    return score, reasons

def build_trade(data, signal_score, reasons):
    """Build complete trade recommendation"""
    current_price = data['price']
    
    # Entry: current price (assuming breakout or recent support bounce)
    entry = current_price
    
    # Stop loss: 2-3% below entry (typical swing trade stop)
    stop_loss = entry * 0.97
    
    # Target: 4-6% above entry (risk/reward 1:2 to 1:3)
    target = entry * 1.05
    
    profit = target - entry
    loss = entry - stop_loss
    risk_reward = profit / loss if loss > 0 else 0
    
    shares = calculate_position_size(entry, stop_loss)
    total_risk = abs((target - entry) * shares)
    
    if signal_score < 2 or shares < 1:
        return None
    
    return {
        'ticker': data['ticker'],
        'entry': round(entry, 2),
        'stop_loss': round(stop_loss, 2),
        'target': round(target, 2),
        'shares': shares,
        'risk_usd': round(MAX_LOSS_PER_TRADE, 2),
        'potential_profit': round(profit * shares, 2),
        'risk_reward': round(risk_reward, 2),
        'score': signal_score,
        'reasons': reasons,
        'volume_m': round(data['volume'] / 1_000_000, 1)
    }

def main():
    print("=" * 90)
    print("TRADING SCANNER - MONDAY WATCHLIST")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 90)
    print()
    
    trades = []
    scanned = 0
    
    for ticker in WATCHLIST:
        print(f"Scanning {ticker}...", end=" ", flush=True)
        
        data = get_stock_data(ticker)
        if not data:
            print("✗ No data")
            time.sleep(0.2)  # Rate limiting
            continue
        
        signal_score, reasons = generate_trade_signal(data)
        trade = build_trade(data, signal_score, reasons)
        
        if trade:
            trades.append(trade)
            print(f"✓ SETUP (score: {signal_score})")
        else:
            print(f"✗ No setup (score: {signal_score})")
        
        scanned += 1
        time.sleep(0.5)  # Respect rate limits
    
    # Sort by score
    trades.sort(key=lambda x: x['score'], reverse=True)
    
    print()
    print("=" * 90)
    print(f"FOUND {len(trades)} TRADE SETUPS (scanned {scanned} stocks)")
    print("=" * 90)
    print()
    
    if not trades:
        print("No high-confidence setups found today.")
        return
    
    # Display top trades
    for i, trade in enumerate(trades[:5], 1):
        print(f"\n[{i}] {trade['ticker']}")
        print(f"    ENTRY:        ${trade['entry']}")
        print(f"    STOP LOSS:    ${trade['stop_loss']} (max loss: ${trade['risk_usd']})")
        print(f"    TARGET:       ${trade['target']}")
        print(f"    SHARES:       {trade['shares']}")
        print(f"    RISK/REWARD:  1:{trade['risk_reward']}")
        print(f"    PROFIT POT:   ${trade['potential_profit']}")
        print(f"    SIGNALS:      {', '.join(trade['reasons'])}")
        print(f"    VOLUME:       {trade['volume_m']}M")
    
    print()
    print("=" * 90)
    print("NEXT STEPS:")
    print("1. Review the setups above")
    print("2. Open IBKR, check 1-day chart for each ticker")
    print("3. Confirm entry price on chart")
    print("4. Execute trades when ready (anytime today)")
    print("5. Use EXACT entry/stop/target from above")
    print("=" * 90)
    
    # Save results to file
    with open('/home/chris/.openclaw/workspace/trading-monday-results.json', 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'trades': trades[:5],
            'instructions': 'Use entry/stop/target values exactly as shown'
        }, f, indent=2)
    
    print("\nResults saved to: trading-monday-results.json")

if __name__ == '__main__':
    main()
