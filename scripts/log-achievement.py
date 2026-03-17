#!/usr/bin/env python3
"""
Log overnight achievement
Usage: python3 log-achievement.py "What you did"
"""
import sys
import os
from datetime import datetime

ACHIEVEMENTS_FILE = "/home/chris/.openclaw/workspace/.overnight_achievements.md"

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 log-achievement.py 'Achievement description'")
        sys.exit(1)
    
    achievement = sys.argv[1]
    
    with open(ACHIEVEMENTS_FILE, 'a') as f:
        f.write(f"- {achievement}\n")
    
    print(f"✅ Logged: {achievement}")
