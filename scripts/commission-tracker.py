#!/usr/bin/env python3
"""Commission Tracker - Tracks progress to Lead Group bonus targets"""
import json
from datetime import datetime

# Lead Group Commission Structure (assumed - can update)
TARGETS = {
    "monthly_gross_margin": 15000,  # $15k monthly gross margin target
    "quarterly_bonus": 10000,       # $10k bonus at $60k quarterly GP
    "yearly_otb": 25000,            # $25k OTE bonus
}

def calculate_progress(current_gp):
    """Calculate progress to bonus targets"""
    monthly = current_gp
    quarterly = monthly * 3
    yearly = monthly * 12
    
    progress = {
        "monthly": {
            "current": monthly,
            "target": TARGETS["monthly_gross_margin"],
            "percent": min(100, (monthly / TARGETS["monthly_gross_margin"]) * 100),
            "needed": max(0, TARGETS["monthly_gross_margin"] - monthly),
        },
        "quarterly": {
            "current": quarterly,
            "target": 60000,
            "percent": min(100, (quarterly / 60000) * 100),
            "needed": max(0, 60000 - quarterly),
        },
        "yearly": {
            "current": yearly,
            "target": 180000,
            "percent": min(100, (yearly / 180000) * 100),
            "needed": max(0, 180000 - yearly),
        }
    }
    return progress

def display_dashboard(current_gp=8500):
    """Show commission dashboard"""
    p = calculate_progress(current_gp)
    
    print("=" * 50)
    print("💰 COMMISSION TRACKER - Lead Group")
    print("=" * 50)
    print(f"Current Monthly GP: ${p['monthly']['current']:,.0f}")
    print()
    print("Monthly Target: ${:,.0f}".format(TARGETS["monthly_gross_margin"]))
    print(f"  Progress: {p['monthly']['percent']:.0f}%")
    print(f"  Need: ${p['monthly']['needed']:,.0f} more")
    print()
    print("Quarterly Target: $60,000")
    print(f"  Progress: {p['quarterly']['percent']:.0f}%")
    print(f"  Need: ${p['quarterly']['needed']:,.0f} more")
    print()
    print("Yearly OTE Bonus: $25k at $180k GP")
    print(f"  Progress: {p['yearly']['percent']:.0f}%")
    print(f"  Need: ${p['yearly']['needed']:,.0f} more")
    print("=" * 50)
    return p

if __name__ == "__main__":
    import sys
    gp = float(sys.argv[1]) if len(sys.argv) > 1 else 8500
    display_dashboard(gp)
