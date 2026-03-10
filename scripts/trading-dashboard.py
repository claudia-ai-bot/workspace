#!/usr/bin/env python3
"""
Trading Dashboard Generator - Professional KPI + Charts
Generates a clean trading overview image (Wyng-style)
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
import numpy as np
from datetime import datetime

# Data
positions = {
    'NVDA': {'entry': 177.85, 'current': 182.65, 'stop': 180.00, 'target': 188.89, 'pnl': 19.20, 'shares': 4},
    'TSM': {'entry': 338.95, 'current': 348.70, 'stop': 342.00, 'target': 359.62, 'pnl': 19.50, 'shares': 2},
    'MPC': {'entry': 221.35, 'current': 215.70, 'stop': 214.00, 'target': 239.38, 'pnl': -11.30, 'shares': 2},
    'SLB': {'entry': 46.92, 'current': 47.19, 'stop': 46.50, 'target': 49.95, 'pnl': 3.78, 'shares': 14},
}

net_pnl = 27.18
goal = 100.00
progress_pct = (net_pnl / goal) * 100
days_left = 27
portfolio_heat = 50

# Colors
color_positive = '#10b981'  # Green
color_negative = '#ef4444'  # Red
color_neutral = '#6366f1'   # Indigo
color_bg = '#f8fafc'        # Light slate
color_text = '#1e293b'      # Dark slate
color_kpi_bg = '#ffffff'    # White

# Create figure
fig, axes = plt.subplots(2, 2, figsize=(14, 10), facecolor=color_bg)
fig.suptitle('Trading Challenge Dashboard', fontsize=20, fontweight='bold', color=color_text, y=0.98)

# Timestamp
timestamp = datetime.now().strftime('%Y-%m-%d %H:%M AEST')
fig.text(0.99, 0.01, timestamp, ha='right', fontsize=9, color='#64748b')

# ============ TOP LEFT: KPI CARDS ============
ax_kpi = axes[0, 0]
ax_kpi.axis('off')

y_pos = 0.85
kpi_height = 0.2

# KPI 1: Net P&L
rect = FancyBboxPatch((0.05, y_pos - kpi_height), 0.9, kpi_height, 
                       boxstyle="round,pad=0.02", 
                       edgecolor=color_positive, facecolor='#ecfdf5', linewidth=2)
ax_kpi.add_patch(rect)
ax_kpi.text(0.08, y_pos - 0.06, 'Net P&L', fontsize=11, fontweight='bold', color=color_text)
ax_kpi.text(0.08, y_pos - 0.15, f'+${net_pnl:.2f}', fontsize=18, fontweight='bold', color=color_positive)
y_pos -= 0.28

# KPI 2: Progress
rect = FancyBboxPatch((0.05, y_pos - kpi_height), 0.9, kpi_height,
                       boxstyle="round,pad=0.02",
                       edgecolor=color_neutral, facecolor='#e0e7ff', linewidth=2)
ax_kpi.add_patch(rect)
ax_kpi.text(0.08, y_pos - 0.06, 'Progress to Goal', fontsize=11, fontweight='bold', color=color_text)
ax_kpi.text(0.08, y_pos - 0.15, f'{progress_pct:.1f}% (${goal:.2f} target)', fontsize=12, fontweight='bold', color=color_neutral)
y_pos -= 0.28

# KPI 3: Heat & Days
rect = FancyBboxPatch((0.05, y_pos - kpi_height), 0.9, kpi_height,
                       boxstyle="round,pad=0.02",
                       edgecolor='#f97316', facecolor='#fff7ed', linewidth=2)
ax_kpi.add_patch(rect)
ax_kpi.text(0.08, y_pos - 0.06, 'Portfolio Heat | Days Left', fontsize=11, fontweight='bold', color=color_text)
ax_kpi.text(0.08, y_pos - 0.15, f'${portfolio_heat:.0f}/80 max | {days_left} days', fontsize=12, fontweight='bold', color='#f97316')

ax_kpi.set_xlim(0, 1)
ax_kpi.set_ylim(0, 1)

# ============ TOP RIGHT: PROGRESS BAR ============
ax_progress = axes[0, 1]
ax_progress.axis('off')

# Title
ax_progress.text(0.05, 0.92, 'Goal Progress', fontsize=14, fontweight='bold', color=color_text)

# Progress bar background
bar_y = 0.75
bar_width = 0.9
bar_height = 0.08
rect_bg = mpatches.Rectangle((0.05, bar_y - bar_height), bar_width, bar_height, 
                               facecolor='#e2e8f0', edgecolor='#94a3b8', linewidth=1)
ax_progress.add_patch(rect_bg)

# Progress bar fill
progress_fill = min(progress_pct / 100, 1.0)
rect_fill = mpatches.Rectangle((0.05, bar_y - bar_height), bar_width * progress_fill, bar_height,
                                facecolor=color_positive, edgecolor='none')
ax_progress.add_patch(rect_fill)

# Text
ax_progress.text(0.5, bar_y - bar_height/2, f'{progress_pct:.1f}%', 
                ha='center', va='center', fontsize=13, fontweight='bold', color='white')

# Positions table below
y_table = 0.55
ax_progress.text(0.05, y_table, 'Positions', fontsize=12, fontweight='bold', color=color_text)

y_table -= 0.08
for ticker, data in positions.items():
    status = '✅' if data['pnl'] >= 0 else '⚠️'
    color = color_positive if data['pnl'] >= 0 else color_negative
    
    ax_progress.text(0.05, y_table, f"{ticker}", fontsize=9, fontweight='bold', color=color_text)
    ax_progress.text(0.25, y_table, f"${data['current']:.2f}", fontsize=9, color=color_text)
    ax_progress.text(0.50, y_table, f"+${data['pnl']:.2f}" if data['pnl'] >= 0 else f"-${abs(data['pnl']):.2f}", 
                    fontsize=9, fontweight='bold', color=color)
    ax_progress.text(0.85, y_table, status, fontsize=11)
    y_table -= 0.07

ax_progress.set_xlim(0, 1)
ax_progress.set_ylim(0, 1)

# ============ BOTTOM LEFT: POSITION BREAKDOWN ============
ax_breakdown = axes[1, 0]

tickers = list(positions.keys())
pnls = [positions[t]['pnl'] for t in tickers]
colors = [color_positive if p >= 0 else color_negative for p in pnls]

bars = ax_breakdown.bar(tickers, pnls, color=colors, edgecolor='#334155', linewidth=1.5)

# Add value labels on bars
for bar, pnl in zip(bars, pnls):
    height = bar.get_height()
    ax_breakdown.text(bar.get_x() + bar.get_width()/2., height,
                     f'${pnl:.2f}', ha='center', va='bottom' if pnl >= 0 else 'top',
                     fontweight='bold', fontsize=10, color=color_text)

ax_breakdown.axhline(y=0, color='#334155', linestyle='-', linewidth=0.8)
ax_breakdown.set_ylabel('P&L ($)', fontweight='bold', fontsize=11, color=color_text)
ax_breakdown.set_title('Position P&L Breakdown', fontweight='bold', fontsize=12, color=color_text, pad=10)
ax_breakdown.grid(axis='y', alpha=0.3, linestyle='--')
ax_breakdown.set_facecolor(color_bg)

# ============ BOTTOM RIGHT: HEAT GAUGE ============
ax_heat = axes[1, 1]
ax_heat.axis('off')

# Title
ax_heat.text(0.05, 0.92, 'Risk Metrics', fontsize=14, fontweight='bold', color=color_text)

# Heat gauge
gauge_y = 0.70
gauge_width = 0.9
gauge_height = 0.10

# Zones
zones = [
    (0.05, 0.30, '#10b981'),      # Safe
    (0.35, 0.65, '#f97316'),      # Warning
    (0.70, 0.95, '#ef4444'),      # Hot
]

for x_start, x_end, zone_color in zones:
    rect = mpatches.Rectangle((x_start, gauge_y - gauge_height), x_end - x_start, gauge_height,
                              facecolor=zone_color, alpha=0.3, edgecolor=zone_color, linewidth=2)
    ax_heat.add_patch(rect)

# Current position indicator
current_pct = portfolio_heat / 80
current_x = 0.05 + (0.90 * current_pct)
ax_heat.plot([current_x, current_x], [gauge_y - gauge_height - 0.03, gauge_y + 0.03], 
            color='#1e293b', linewidth=3)
ax_heat.text(current_x, gauge_y - gauge_height - 0.08, f'${portfolio_heat:.0f}', 
            ha='center', fontweight='bold', fontsize=10, color=color_text)

# Labels
ax_heat.text(0.15, gauge_y + 0.05, 'Safe', fontsize=9, fontweight='bold', color=color_positive, ha='center')
ax_heat.text(0.50, gauge_y + 0.05, 'Warning', fontsize=9, fontweight='bold', color='#f97316', ha='center')
ax_heat.text(0.85, gauge_y + 0.05, 'Hot', fontsize=9, fontweight='bold', color=color_negative, ha='center')

ax_heat.set_xlim(0, 1)
ax_heat.set_ylim(0, 1)

# Tight layout
plt.tight_layout(rect=[0, 0.02, 1, 0.96])

# Save
output_path = '/home/chris/.openclaw/workspace/trading-dashboard.png'
plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor=color_bg)
print(f"✅ Dashboard saved: {output_path}")
plt.close()
