#!/usr/bin/env python3
"""Portfolio Tracker - Logs daily portfolio value to CSV"""
import csv
import os
from datetime import datetime

PORTFOLIO_FILE = "/home/chris/.openclaw/workspace/memory/portfolio-tracker.csv"
TARGET = 2500000

def log_portfolio(value):
    """Log portfolio value with timestamp"""
    os.makedirs(os.path.dirname(PORTFOLIO_FILE), exist_ok=True)
    
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Check if file exists and get last entry
    entries = []
    if os.path.exists(PORTFOLIO_FILE):
        with open(PORTFOLIO_FILE, 'r') as f:
            reader = csv.DictReader(f)
            entries = list(reader)
    
    # Check if already logged today
    if entries and entries[-1].get('date') == today:
        print(f"Already logged today: ${value:,.0f}")
        return
    
    # Calculate days to target
    days_remaining = (50 - 40) * 365  # Rough estimate
    daily_needed = (TARGET - value) / days_remaining if days_remaining > 0 else 0
    
    # Append new entry
    with open(PORTFOLIO_FILE, 'a', newline='') as f:
        writer = csv.writer(f)
        if not entries:
            writer.writerow(['date', 'value', 'target', 'daily_needed'])
        writer.writerow([today, value, TARGET, f"{daily_needed:,.0f}"])
    
    print(f"Logged: ${value:,.0f} | Target: ${TARGET:,} | Need: ${daily_needed:,.0f}/day")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        value = float(sys.argv[1].replace(',', ''))
    else:
        # Default from memory
        value = 673570
    log_portfolio(value)
