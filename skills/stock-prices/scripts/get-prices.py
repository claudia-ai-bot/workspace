#!/usr/bin/env python3
"""
Get real-time stock prices using yfinance
"""

import sys
import yfinance as yf
from datetime import datetime

def get_prices(tickers):
    """Fetch prices for given tickers"""
    if not tickers:
        print("Usage: python3 get-prices.py NVDA TSM MPC SLB")
        sys.exit(1)
    
    # Download data
    data = yf.download(tickers, period="1d", progress=False)
    
    # Single ticker returns Series, multiple returns DataFrame
    if isinstance(data, type(data)) and len(tickers) == 1:
        data = data.to_frame().T
    
    print(f"\n📊 Stock Prices ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})\n")
    
    for ticker in tickers:
        try:
            ticker_obj = yf.Ticker(ticker)
            info = ticker_obj.info
            
            # Get current price and daily change
            current_price = info.get('currentPrice') or info.get('regularMarketPrice', 'N/A')
            prev_close = info.get('previousClose', 'N/A')
            bid = info.get('bid', 'N/A')
            ask = info.get('ask', 'N/A')
            
            # Calculate daily change %
            if current_price != 'N/A' and prev_close != 'N/A':
                change_pct = ((current_price - prev_close) / prev_close) * 100
                change_str = f"{change_pct:+.2f}%"
            else:
                change_str = "N/A"
            
            # Format output
            price_str = f"${current_price:.2f}" if current_price != 'N/A' else "N/A"
            bid_str = f"${bid:.2f}" if bid != 'N/A' else "N/A"
            ask_str = f"${ask:.2f}" if ask != 'N/A' else "N/A"
            
            print(f"{ticker:5s}: {price_str:>10s} (bid: {bid_str:>10s}, ask: {ask_str:>10s}) | {change_str:>8s}")
        
        except Exception as e:
            print(f"{ticker}: Error - {e}")
    
    print()

if __name__ == "__main__":
    tickers = sys.argv[1:] if len(sys.argv) > 1 else ["NVDA", "TSM", "MPC", "SLB"]
    get_prices(tickers)
