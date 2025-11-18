"""
Sample data generator for testing the pattern detection system
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def generate_sample_btc_data(
    start_date="2023-01-01",
    periods=2000,
    initial_price=40000,
    volatility=0.02
):
    """
    Generate realistic-looking OHLC data for testing

    Parameters:
    -----------
    start_date : str
        Starting date
    periods : int
        Number of candles
    initial_price : float
        Starting price
    volatility : float
        Price volatility
    """

    # Generate timestamps (hourly data)
    start = pd.to_datetime(start_date)
    dates = [start + timedelta(hours=i) for i in range(periods)]

    # Generate price movement with trends
    np.random.seed(42)

    # Create trending price with noise
    trend = np.linspace(0, 0.15, periods)  # 15% overall trend
    noise = np.random.randn(periods) * volatility

    # Add some cycles
    cycle1 = 0.02 * np.sin(np.linspace(0, 4 * np.pi, periods))
    cycle2 = 0.01 * np.sin(np.linspace(0, 10 * np.pi, periods))

    price_changes = (trend + noise + cycle1 + cycle2) * 0.01  # Scale down
    prices = initial_price * (1 + np.cumsum(price_changes))

    # Generate OHLC from close prices
    data = []
    for i, (date, close) in enumerate(zip(dates, prices)):
        # Generate realistic OHLC
        volatility_factor = abs(np.random.randn() * volatility * close)

        open_price = close * (1 + np.random.randn() * 0.001)
        high = max(open_price, close) + abs(np.random.randn() * volatility_factor)
        low = min(open_price, close) - abs(np.random.randn() * volatility_factor)

        # Ensure OHLC consistency
        high = max(high, open_price, close)
        low = min(low, open_price, close)

        volume = abs(np.random.randn() * 1000 + 5000)

        data.append({
            'date': date,
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume
        })

    df = pd.DataFrame(data)
    return df


def generate_pattern_data(pattern_type="harmonic", periods=500):
    """
    Generate data with specific patterns embedded

    Parameters:
    -----------
    pattern_type : str
        Type of pattern to embed: 'harmonic', 'hs', 'flag'
    periods : int
        Number of candles
    """

    np.random.seed(123)
    dates = pd.date_range(start='2023-01-01', periods=periods, freq='h')

    if pattern_type == "harmonic":
        # Create a Gartley-like pattern
        base_price = 50000
        prices = np.zeros(periods)

        # XA leg (upward)
        prices[0:100] = np.linspace(base_price, base_price * 1.10, 100)

        # AB leg (down 0.618 of XA)
        prices[100:180] = np.linspace(base_price * 1.10, base_price * 1.038, 80)

        # BC leg (up, 0.382-0.886 of AB)
        prices[180:260] = np.linspace(base_price * 1.038, base_price * 1.08, 80)

        # CD leg (down, 1.13-1.618 of BC)
        prices[260:350] = np.linspace(base_price * 1.08, base_price * 1.012, 90)

        # Continuation
        prices[350:] = np.linspace(base_price * 1.012, base_price * 1.15, periods - 350)

    elif pattern_type == "hs":
        # Create Head & Shoulders pattern
        base_price = 45000
        prices = np.zeros(periods)

        # Left shoulder
        prices[0:100] = np.linspace(base_price, base_price * 1.08, 100)
        prices[100:150] = np.linspace(base_price * 1.08, base_price * 1.04, 50)

        # Head
        prices[150:250] = np.linspace(base_price * 1.04, base_price * 1.12, 100)
        prices[250:300] = np.linspace(base_price * 1.12, base_price * 1.04, 50)

        # Right shoulder
        prices[300:380] = np.linspace(base_price * 1.04, base_price * 1.07, 80)
        prices[380:450] = np.linspace(base_price * 1.07, base_price * 1.02, 70)

        # Breakdown
        prices[450:] = np.linspace(base_price * 1.02, base_price * 0.90, periods - 450)

    elif pattern_type == "flag":
        # Create Bull Flag pattern
        base_price = 48000
        prices = np.zeros(periods)

        # Strong uptrend (pole)
        prices[0:150] = np.linspace(base_price, base_price * 1.15, 150)

        # Flag (slight downward consolidation)
        flag_start = base_price * 1.15
        for i in range(150, 300):
            prices[i] = flag_start - (i - 150) * 0.0002 * base_price
            prices[i] += np.random.randn() * base_price * 0.001

        # Breakout continuation
        prices[300:] = np.linspace(prices[299], base_price * 1.25, periods - 300)

    else:
        # Random walk
        base_price = 48000
        prices = base_price * (1 + np.cumsum(np.random.randn(periods) * 0.001))

    # Add noise
    prices += np.random.randn(periods) * 50

    # Generate OHLC
    data = []
    for i, (date, close) in enumerate(zip(dates, prices)):
        open_price = close * (1 + np.random.randn() * 0.001)
        high = max(open_price, close) * (1 + abs(np.random.randn() * 0.003))
        low = min(open_price, close) * (1 - abs(np.random.randn() * 0.003))
        volume = abs(np.random.randn() * 1000 + 5000)

        data.append({
            'date': date,
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume
        })

    df = pd.DataFrame(data)
    return df


if __name__ == "__main__":
    print("📊 Generating sample data files...")

    # Generate main sample data
    print("  ✓ Generating BTCUSDT3600.csv (2000 hourly candles)...")
    df = generate_sample_btc_data(periods=2000)
    df.to_csv('BTCUSDT3600.csv', index=False)
    print(f"    Saved: {len(df)} candles, Price range: ${df['close'].min():.0f} - ${df['close'].max():.0f}")

    # Generate pattern-specific samples
    print("  ✓ Generating harmonic_sample.csv...")
    df_harmonic = generate_pattern_data("harmonic", periods=500)
    df_harmonic.to_csv('harmonic_sample.csv', index=False)

    print("  ✓ Generating hs_sample.csv...")
    df_hs = generate_pattern_data("hs", periods=500)
    df_hs.to_csv('hs_sample.csv', index=False)

    print("  ✓ Generating flag_sample.csv...")
    df_flag = generate_pattern_data("flag", periods=500)
    df_flag.to_csv('flag_sample.csv', index=False)

    print("\n✅ Sample data files created successfully!")
    print("\nFiles created:")
    print("  - BTCUSDT3600.csv (Main sample - realistic BTC data)")
    print("  - harmonic_sample.csv (Data with Harmonic patterns)")
    print("  - hs_sample.csv (Data with Head & Shoulders pattern)")
    print("  - flag_sample.csv (Data with Bull Flag pattern)")
    print("\nYou can now run: streamlit run advanced_pattern_ui.py")
