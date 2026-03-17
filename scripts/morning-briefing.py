#!/usr/bin/env python3
"""
Morning Briefing - Weather + Markets + Overnight Achievements
Runs at 6am AEST daily
"""
import urllib.request
import json
import sys
from datetime import datetime
import os

ACHIEVEMENTS_FILE = "/home/chris/.openclaw/workspace/.overnight_achievements.md"

def get_weather():
    try:
        url = 'https://wttr.in/Brisbane?format=%c%t'
        req = urllib.request.Request(url, headers={'User-Agent': 'curl'})
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.read().decode().strip()
    except:
        return "Brisbane: unavailable"

def get_markets():
    results = []
    
    tickers = {
        '^AXJO': 'ASX200',
        '^SPX': 'S&P500',
        '^DJI': 'Dow'
    }
    
    for ticker, name in tickers.items():
        try:
            url = f'https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=2d'
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read())
                result = data.get('chart', {}).get('result', [{}])[0]
                if result:
                    closes = result.get('indicators', {}).get('quote', [{}])[0].get('close', [])
                    closes = [c for c in closes if c is not None]
                    if len(closes) >= 2:
                        price = closes[-1]
                        prev = closes[-2]
                        pct = ((price - prev) / prev * 100)
                        results.append(f"{name}: {price:,.0f} ({pct:+.2f}%)")
                    elif len(closes) == 1:
                        results.append(f"{name}: {closes[0]:,.0f}")
        except Exception as e:
            results.append(f"{name}: error")
    
    return results

def get_achievements():
    """Read overnight achievements from file"""
    if os.path.exists(ACHIEVEMENTS_FILE):
        with open(ACHIEVEMENTS_FILE, 'r') as f:
            content = f.read().strip()
            if content:
                return content
    return None

def clear_achievements():
    """Clear achievements after displaying"""
    if os.path.exists(ACHIEVEMENTS_FILE):
        os.remove(ACHIEVEMENTS_FILE)

if __name__ == "__main__":
    print("=" * 50)
    print("☀️ MORNING BRIEFING")
    print("=" * 50)
    
    weather = get_weather()
    print(f"\n📍 Brisbane: {weather}")
    
    print("\n📈 Markets:")
    for m in get_markets():
        print(f"   {m}")
    
    # Check for overnight achievements
    achievements = get_achievements()
    if achievements:
        print("\n🌙 WHILE YOU SLEPT:")
        print(achievements)
        clear_achievements()
    
    print("\n" + "=" * 50)
