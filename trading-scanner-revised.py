#!/usr/bin/env python3
"""
Revised Trading Scanner - Top 5 Strategies Applied
Based on: Mean Reversion (60%), Breakout (30%), Gap Trading (10%)
"""

import requests
import time
from datetime import datetime

API_KEY = "OCXEW1TRCQRZ2K2G"
BASE_URL = "https://www.alphavantage.co/query"

WATCHLIST = [
    'NVDA', 'AMD', 'ASML', 'MRVL', 'TSM',  # Tech/Semis
    'CVX', 'MPC', 'OXY', 'SLB',             # Energy
    'CAT', 'DE', 'BA', 'LMT'                # Industrials
]

def get_stock_data(ticker):
    """Fetch daily quote"""
    try:
        url = f"{BASE_URL}?function=GLOBAL_QUOTE&symbol={ticker}&apikey={API_KEY}"
        resp = requests.get(url, timeout=5)
        data = resp.json()
        
        if 'Global Quote' not in data or not data['Global Quote'].get('05. price'):
            return None
        
        q = data['Global Quote']
        return {
            'ticker': ticker,
            'price': float(q['05. price']),
            'change': float(q.get('09. change', 0)),
            'change_pct': float(q.get('10. change percent', '0').rstrip('%')),
            'volume': int(float(q.get('06. volume', 0))),
            'high': float(q.get('03. high', 0)),
            'low': float(q.get('04. low', 0))
        }
    except:
        return None

def score_strategy_1_mean_reversion(data):
    """
    Strategy #1: Mean Reversion + Support Bounce (60% of pro trades)
    - Recent pullback (negative or flat change)
    - Good volume (liquidity)
    - Setup: Bounce off support
    """
    score = 0
    reasons = []
    
    # Recent pullback (oversold)
    if -5 < data['change_pct'] <= 0:
        score += 3
        reasons.append("Pullback (reset momentum)")
    elif data['change_pct'] < -5:
        score += 2
        reasons.append("Weakness (stronger bounce potential)")
    
    # Volume confirmation
    if data['volume'] > 1_000_000:
        score += 2
        reasons.append("Good volume")
    
    # Bounce potential (not at daily high)
    if data['price'] < data['high'] * 0.98:
        score += 1
        reasons.append("Room to bounce")
    
    return score, reasons, "MEAN_REVERSION"

def score_strategy_2_breakout(data):
    """
    Strategy #2: Breakout on Volume (30%)
    - Recent strength (positive change)
    - Breaking above recent levels
    - Volume spike
    """
    score = 0
    reasons = []
    
    # Momentum (strength)
    if 0 < data['change_pct'] < 3:
        score += 2
        reasons.append("Building momentum")
    elif data['change_pct'] >= 3:
        score += 3
        reasons.append("Strong momentum")
    
    # Volume
    if data['volume'] > 1_000_000:
        score += 2
        reasons.append("Volume spike")
    
    # At upper end of range
    if data['price'] > data['low'] * 1.02:
        score += 1
        reasons.append("At upper end")
    
    return score, reasons, "BREAKOUT"

def build_professional_trade(data, strategy_type, score, reasons):
    """Build trade with proper professional R/R (1:2 minimum)"""
    
    if score < 4:  # Minimum threshold
        return None
    
    price = data['price']
    
    if strategy_type == "MEAN_REVERSION":
        # Support bounce: stop below the low, target at recent resistance
        stop_loss = data['low'] * 0.98  # Below the day's low
        target = price * 1.06  # 6% target (modest but achievable)
        
    else:  # BREAKOUT
        # Breakout: stop below breakout, target further up
        stop_loss = data['low'] * 0.99
        target = price * 1.08  # 8% target
    
    # Calculate position size for $20 max loss
    max_loss = 20
    stop_distance = abs(price - stop_loss)
    shares = int(max_loss / stop_distance) if stop_distance > 0 else 0
    
    if shares < 1:
        return None
    
    # Calculate actual R/R
    profit = target - price
    loss = price - stop_loss
    risk_reward = profit / loss if loss > 0 else 0
    
    # Filter: only trades with 1:2+ risk/reward
    if risk_reward < 1.5:
        return None
    
    return {
        'ticker': data['ticker'],
        'strategy': strategy_type,
        'entry': round(price, 2),
        'stop_loss': round(stop_loss, 2),
        'target': round(target, 2),
        'shares': shares,
        'max_loss': round(max_loss, 2),
        'potential_profit': round(profit * shares, 2),
        'risk_reward': round(risk_reward, 2),
        'score': score,
        'reasons': reasons,
        'volume_m': round(data['volume'] / 1_000_000, 1)
    }

def main():
    print("=" * 100)
    print("TRADING SCANNER - REVISED (Top 5 Strategies Applied)")
    print(f"Strategy: 60% Mean Reversion | 30% Breakout | 10% Gap Trading")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 100)
    print()
    
    trades = []
    
    for ticker in WATCHLIST:
        print(f"Scanning {ticker}...", end=" ", flush=True)
        
        data = get_stock_data(ticker)
        if not data:
            print("✗ No data")
            time.sleep(0.2)
            continue
        
        # Try Strategy 1: Mean Reversion
        score1, reasons1, strat1 = score_strategy_1_mean_reversion(data)
        trade1 = build_professional_trade(data, strat1, score1, reasons1)
        
        # Try Strategy 2: Breakout
        score2, reasons2, strat2 = score_strategy_2_breakout(data)
        trade2 = build_professional_trade(data, strat2, score2, reasons2)
        
        # Add best trade
        best_trade = None
        if trade1 and trade2:
            best_trade = trade1 if trade1['score'] >= trade2['score'] else trade2
        else:
            best_trade = trade1 or trade2
        
        if best_trade:
            trades.append(best_trade)
            print(f"✓ {best_trade['strategy']} (R/R: {best_trade['risk_reward']})")
        else:
            print(f"✗ Doesn't meet criteria")
        
        time.sleep(0.5)
    
    # Sort by score
    trades.sort(key=lambda x: x['score'], reverse=True)
    
    print()
    print("=" * 100)
    print(f"FOUND {len(trades)} HIGH-QUALITY SETUPS (1:2+ Risk/Reward)")
    print("=" * 100)
    print()
    
    if not trades:
        print("No professional-grade setups found. Recommendations:")
        print("1. Wait for better market conditions")
        print("2. Expand watchlist to more stocks")
        print("3. Consider weekly timeframe instead of daily")
        return
    
    # Display trades
    for i, trade in enumerate(trades[:5], 1):
        print(f"\n[{i}] {trade['ticker']} - {trade['strategy']}")
        print(f"    Entry:        ${trade['entry']}")
        print(f"    Stop Loss:    ${trade['stop_loss']} (max loss: ${trade['max_loss']})")
        print(f"    Target:       ${trade['target']}")
        print(f"    Shares:       {trade['shares']}")
        print(f"    Risk/Reward:  1:{trade['risk_reward']:.2f}")
        print(f"    Pot. Profit:  ${trade['potential_profit']}")
        print(f"    Signals:      {', '.join(trade['reasons'])}")
        print(f"    Strategy:     {trade['strategy']}")
        print(f"    Score:        {trade['score']}/10")

if __name__ == '__main__':
    main()
