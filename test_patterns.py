"""
Quick test script to verify pattern detection is working
"""

import pandas as pd
import numpy as np

from head_shoulders import find_hs_patterns
from flags_pennants import find_flags_pennants_trendline
from harmonic_patterns import find_xabcd
from directional_change import get_extremes

print("🔍 Testing Pattern Detection System...\n")

# Load test data
print("📊 Loading sample data...")
data = pd.read_csv('BTCUSDT3600.csv')
data['date'] = pd.to_datetime(data['date'])
data = data.set_index('date')
print(f"   Loaded {len(data)} candles")
print(f"   Price range: ${data['close'].min():.2f} - ${data['close'].max():.2f}\n")

# Test on a subset
test_data = data.iloc[:500].copy()

# Convert to log prices
for col in ['open', 'high', 'low', 'close']:
    test_data[col] = np.log(test_data[col])

log_close = test_data['close'].to_numpy()

# Test Head & Shoulders
print("🎯 Testing Head & Shoulders Detection...")
try:
    hs_patterns, ihs_patterns = find_hs_patterns(log_close, order=6, early_find=False)
    print(f"   ✓ Found {len(hs_patterns)} H&S patterns")
    print(f"   ✓ Found {len(ihs_patterns)} Inverse H&S patterns")
except Exception as e:
    print(f"   ✗ Error: {e}")

# Test Flags & Pennants
print("\n🚩 Testing Flags & Pennants Detection...")
try:
    bull_flags, bear_flags, bull_pennants, bear_pennants = find_flags_pennants_trendline(log_close, order=10)
    print(f"   ✓ Found {len(bull_flags)} Bull Flags")
    print(f"   ✓ Found {len(bear_flags)} Bear Flags")
    print(f"   ✓ Found {len(bull_pennants)} Bull Pennants")
    print(f"   ✓ Found {len(bear_pennants)} Bear Pennants")
except Exception as e:
    print(f"   ✗ Error: {e}")

# Test Harmonic Patterns
print("\n🎵 Testing Harmonic Patterns Detection...")
try:
    # Need to use original data for harmonics
    test_ohlc = data.iloc[:500].copy()
    test_ohlc['r'] = np.log(test_ohlc['close']).diff().shift(-1)
    extremes = get_extremes(test_ohlc, sigma=0.02)
    harmonic_output = find_xabcd(test_ohlc, extremes, err_thresh=0.5)

    total_harmonics = 0
    for pattern_name, info in harmonic_output.items():
        bull_count = len(info['bull_patterns'])
        bear_count = len(info['bear_patterns'])
        if bull_count > 0 or bear_count > 0:
            print(f"   ✓ {pattern_name}: {bull_count} bull, {bear_count} bear")
            total_harmonics += bull_count + bear_count

    if total_harmonics == 0:
        print("   ℹ No harmonic patterns found (this is normal with random data)")
except Exception as e:
    print(f"   ✗ Error: {e}")

# Test Directional Change
print("\n⚡ Testing Directional Change...")
try:
    dc_extremes = get_extremes(data.iloc[:500], sigma=0.02)
    print(f"   ✓ Found {len(dc_extremes)} directional change extremes")
    tops = len(dc_extremes[dc_extremes['type'] == 1])
    bottoms = len(dc_extremes[dc_extremes['type'] == -1])
    print(f"   ✓ Tops: {tops}, Bottoms: {bottoms}")
except Exception as e:
    print(f"   ✗ Error: {e}")

print("\n✅ Pattern detection test completed!")
print("\nNext step: Run the UI with:")
print("   streamlit run advanced_pattern_ui.py")
