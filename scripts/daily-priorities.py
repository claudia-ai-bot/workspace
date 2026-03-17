#!/usr/bin/env python3
"""Daily Priorities Generator - Creates focus areas for the day"""
import random
from datetime import datetime

PRIORITIES = [
    "Make 10 recruiter calls",
    "Send 5 personalized emails to candidates",
    "Follow up on 3 pending submissions",
    "Post 1 job on Seek/Indeed",
    "Network: 3 new connections on LinkedIn",
    "Market mapping: research 1 new company",
    "Interview 1 candidate",
    "Submit 2 candidates to jobs",
    "Update CRM with yesterday's activities",
]

def generate_daily():
    """Generate 3 focus areas for today"""
    today = datetime.now().strftime("%A, %B %d")
    selected = random.sample(PRIORITIES, 3)
    
    print(f"📋 DAILY PRIORITIES - {today}")
    print("=" * 40)
    for i, p in enumerate(selected, 1):
        print(f"{i}. {p}")
    print("=" * 40)
    
    return selected

if __name__ == "__main__":
    generate_daily()
