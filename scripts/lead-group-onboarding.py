#!/usr/bin/env python3
"""
Lead Group Onboarding Checklist
Start date: May 4, 2026
"""
from datetime import datetime, timedelta

START_DATE = datetime(2026, 5, 4)
TODAY = datetime.now()
DAYS_UNTIL = (START_DATE - TODAY).days

TASKS = {
    "week_4": [
        ("Monday Apr 6", "Submit LEAD Kit marketing form"),
        ("Tuesday Apr 7", "Confirm desk/sector allocation"),
        ("Wednesday Apr 8", "Set up CommSec + IBKR accounts"),
        ("Thursday Apr 9", "Review Lead Group LinkedIn presence"),
        ("Friday Apr 10", "Research construction clients in SEQ"),
    ],
    "week_3": [
        ("Monday Apr 13", "Finalise CV and personal branding"),
        ("Tuesday Apr 14", "Set up Salesforce/CRM training"),
        ("Wednesday Apr 15", "Book 3 coffee meetings with industry contacts"),
        ("Thursday Apr 16", "Create target company list (50 companies)"),
        ("Friday Apr 17", "Practice pitch with Bec"),
    ],
    "week_2": [
        ("Monday Apr 20", "Lead Group office induction"),
        ("Tuesday Apr 21", "Meet team members"),
        ("Wednesday Apr 22", "Set up email + LinkedIn Premium"),
        ("Thursday Apr 23", "Review compensation structure in detail"),
        ("Friday Apr 24", "30-day plan draft"),
    ],
    "week_1": [
        ("Monday Apr 27", "Finalise 30-day plan with manager"),
        ("Tuesday Apr 28", "Prepare client visit kit (cards, iPad, notes)"),
        ("Wednesday Apr 29", "Set up daily routine + commute"),
        ("Thursday Apr 30", "Review pipeline + warm leads"),
        ("Friday May 1", "Rest + prepare for Monday"),
    ],
    "week_1_day": [
        ("Monday May 4", "FIRST DAY - Report to Lead Group"),
    ]
}

def show_checklist():
    global TODAY, DAYS_UNTIL
    
    print("=" * 60)
    print("🎯 LEAD GROUP ONBOARDING CHECKLIST")
    print(f"Start Date: May 4, 2026 | Days until: {DAYS_UNTIL}")
    print("=" * 60)
    
    for week, tasks in TASKS.items():
        print(f"\n{week.replace('_', ' ').title()}:")
        for task in tasks:
            print(f"  ☐ {task[0]}: {task[1]}")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    show_checklist()
