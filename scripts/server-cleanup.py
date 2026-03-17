#!/usr/bin/env python3
"""Weekly Server Cleanup Script"""
import os
import glob
from datetime import datetime

def cleanup():
    """Clean temp files and logs"""
    workspace = "/home/chris/.openclaw/workspace"
    cleaned = []
    
    # Clear log files
    for log in glob.glob(f"{workspace}/**/*.log", recursive=True):
        try:
            size = os.path.getsize(log)
            with open(log, 'w') as f:
                f.write(f"# Cleared {datetime.now().isoformat()}\n")
            cleaned.append(f"Log: {log.replace(workspace + '/', '')} ({size} bytes)")
        except:
            pass
    
    # Clear __pycache__
    for pycache in glob.glob(f"{workspace}/**/__pycache__", recursive=True):
        try:
            os.rmdir(pycache)
            cleaned.append(f"Pycache: {pycache.replace(workspace + '/', '')}")
        except:
            pass
    
    print(f"🧹 Server Cleanup - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Cleaned {len(cleaned)} items:")
    for c in cleaned:
        print(f"  • {c}")
    
    return cleaned

if __name__ == "__main__":
    cleanup()
