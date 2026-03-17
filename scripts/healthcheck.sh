#!/bin/bash
# OpenClaw Healthcheck - Run when things freeze

echo "=== OPENCLAW HEALTHCHECK ==="
echo ""

echo "📅 Date/Time:"
date
echo ""

echo "🔄 OpenClaw Status:"
openclaw status 2>&1 | head -30
echo ""

echo "🧠 Context Usage:"
grep -o '"totalTokens":[0-9]*' ~/.openclaw/agents/main/sessions/*.jsonl 2>/dev/null | tail -1 || echo "Could not find"
echo ""

echo "💻 Server Resources:"
echo "CPU/Memory/Disk:"
free -h
df -h / | tail -1
echo ""

echo "🔗 Services:"
systemctl --user list-units --type=service --state=running | grep -E "openclaw|gateway|node" || echo "No user services"
echo ""

echo "🛑 Stuck Processes:"
ps aux --sort=-%cpu | head -10
echo ""

echo "=== END HEALTHCHECK ==="
