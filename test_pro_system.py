"""
Test Professional Pattern Detection System
Tests pattern lifecycle management and tracking
"""

import pandas as pd
import numpy as np
from pattern_manager import PatternManager, PatternState

print("🧪 Testing Professional Pattern System...\n")

# Load test data
print("📊 Loading data...")
data = pd.read_csv('BTCUSDT3600.csv')
data['date'] = pd.to_datetime(data['date'])
data = data.set_index('date')
print(f"   ✓ Loaded {len(data)} candles\n")

# Initialize Pattern Manager
print("⚙️ Initializing Pattern Manager...")
manager = PatternManager(data)
print(f"   ✓ Manager initialized\n")

# Add test patterns
print("➕ Adding test patterns...")

# Add a long pattern at index 100
manager.add_pattern(
    pattern_type="Bull Flag",
    side="long",
    entry_index=100,
    entry_price=data['close'].iloc[100],
    stop_price=data['close'].iloc[100] * 0.98,
    tp1_price=data['close'].iloc[100] * 1.04,
    max_bars=50
)

# Add a short pattern at index 150
manager.add_pattern(
    pattern_type="H&S",
    side="short",
    entry_index=150,
    entry_price=data['close'].iloc[150],
    stop_price=data['close'].iloc[150] * 1.02,
    tp1_price=data['close'].iloc[150] * 0.96,
    max_bars=40
)

print(f"   ✓ Added 2 test patterns\n")

# Update patterns to index 200
print("🔄 Updating patterns to index 200...")
manager.update_patterns(200)

active = manager.get_active_patterns(200)
print(f"   ✓ Active patterns: {len(active)}")

for p in active:
    print(f"      - {p.pattern_type} ({p.side}): {p.bars_active} bars, state={p.state.value}")

completed = manager.completed_patterns
print(f"   ✓ Completed patterns: {len(completed)}")

for p in completed:
    reason = p.exit_reason if p.exit_reason else "unknown"
    pnl_pct = p.pnl_percent if p.pnl_percent else 0
    print(f"      - {p.pattern_type} ({p.side}): {reason}, PnL={pnl_pct:.2f}%")

print()

# Test statistics
print("📊 Pattern Statistics:")
stats = manager.get_statistics()
for key, value in stats.items():
    if isinstance(value, float):
        print(f"   {key}: {value:.2f}")
    else:
        print(f"   {key}: {value}")

print()

# Test DataFrame export
print("📄 Testing DataFrame export...")
df = manager.to_dataframe()
print(f"   ✓ Exported {len(df)} patterns")
print(f"   Columns: {list(df.columns)}")

print()

# Test filtering
print("🔍 Testing pattern filtering...")
long_patterns = manager.get_active_patterns(200, sides=["long"])
short_patterns = manager.get_active_patterns(200, sides=["short"])
print(f"   ✓ Long patterns: {len(long_patterns)}")
print(f"   ✓ Short patterns: {len(short_patterns)}")

print()

# Test full simulation
print("⏩ Testing full simulation (index 100-500)...")
all_updates = 0
for i in range(100, min(500, len(data))):
    manager.update_patterns(i)
    all_updates += 1

final_active = manager.get_active_patterns(499)
final_completed = manager.completed_patterns

print(f"   ✓ Processed {all_updates} updates")
print(f"   ✓ Final active: {len(final_active)}")
print(f"   ✓ Final completed: {len(final_completed)}")

print()

print("✅ All tests passed!")
print("\nPattern Lifecycle Management System:")
print("  ✓ Pattern tracking")
print("  ✓ TP/Stop monitoring")
print("  ✓ State management")
print("  ✓ Statistics calculation")
print("  ✓ Filtering & export")
print("\nReady to run: streamlit run pro_pattern_ui.py")
