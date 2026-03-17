#!/bin/bash
# Trading Morning Check - runs daily at 9:30 AM AEST
# Checks all open positions and sends Telegram alert if needed

API_KEY="OCXEW1TRCQRZ2K2G"
TELEGRAM_TOKEN=$(cat ~/.openclaw/config.json | python3 -c "import sys,json; print(json.load(sys.stdin).get('telegram',{}).get('bot_token',''))" 2>/dev/null)
CHAT_ID="8636795192"

# AEST offset
TZ="Australia/Brisbane"

# Positions file
LOG_FILE="$HOME/.openclaw/workspace/memory/trading-log-2026-03-09.md"

# Get current prices
get_price() {
    curl -s "https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=$1&apikey=$API_KEY" | \
    python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('Global Quote',{}).get('05. price','ERROR'))" 2>/dev/null
}

# Check positions
check_positions() {
    echo "Checking positions..."
    prices=""
    for ticker in NVDA TSM DE; do
        price=$(get_price "$ticker")
        prices="$prices$ticker:$price "
        sleep 12
    done
    
    # Build message
    msg="🛑 TRADING CHECK %0A"
    msg="${msg}Time: $(date '+%Y-%m-%d %H:%M AEST')%0A%0A"
    msg="${msg}Current Prices: $prices%0A%0A"
    msg="${msg}Check log for full P/L"
    
    # Send to Telegram (basic - just price check)
    if [ -n "$TELEGRAM_TOKEN" ]; then
        curl -s "https://api.telegram.org/bot$TELEGRAM_TOKEN/sendMessage?chat_id=$CHAT_ID&text=$msg" >/dev/null 2>&1
    fi
    
    echo "Prices: $prices"
}

check_positions
