"""
Data Downloader for Pattern Detection System

Supports:
- Binance (cryptocurrency)
- Yahoo Finance (stocks, forex, crypto)
- Custom CSV upload
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import requests
from typing import Optional


def download_binance(
    symbol: str = "BTCUSDT",
    interval: str = "1h",
    limit: int = 1000
) -> pd.DataFrame:
    """
    Download data from Binance API

    Parameters:
    -----------
    symbol : str
        Trading pair (e.g., "BTCUSDT", "ETHUSDT")
    interval : str
        Timeframe: "1m", "5m", "15m", "1h", "4h", "1d"
    limit : int
        Number of candles (max 1000)

    Returns:
    --------
    pd.DataFrame
        OHLC data with datetime index
    """

    url = "https://api.binance.com/api/v3/klines"

    params = {
        "symbol": symbol.upper(),
        "interval": interval,
        "limit": min(limit, 1000)  # Binance max
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        df = pd.DataFrame(data, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'trades', 'taker_buy_base',
            'taker_buy_quote', 'ignore'
        ])

        # Convert to proper types
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df = df.set_index('timestamp')
        df.index.name = 'date'

        # Keep only OHLCV
        df = df[['open', 'high', 'low', 'close', 'volume']]

        # Convert to float
        for col in df.columns:
            df[col] = df[col].astype(float)

        return df

    except requests.exceptions.RequestException as e:
        raise Exception(f"Binance API error: {e}")
    except Exception as e:
        raise Exception(f"Data processing error: {e}")


def download_yfinance(
    symbol: str = "BTC-USD",
    interval: str = "1h",
    period: str = "1mo"
) -> pd.DataFrame:
    """
    Download data from Yahoo Finance

    Parameters:
    -----------
    symbol : str
        Ticker symbol (e.g., "BTC-USD", "AAPL", "EURUSD=X")
    interval : str
        Timeframe: "1m", "5m", "15m", "1h", "1d", "1wk"
    period : str
        Time period: "1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "max"

    Returns:
    --------
    pd.DataFrame
        OHLC data with datetime index
    """

    try:
        import yfinance as yf

        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval)

        if df.empty:
            raise Exception(f"No data found for {symbol}")

        # Rename columns to match our format
        df.columns = df.columns.str.lower()
        df.index.name = 'date'

        # Keep only OHLCV
        df = df[['open', 'high', 'low', 'close', 'volume']]

        return df

    except ImportError:
        raise Exception("yfinance not installed. Run: pip install yfinance")
    except Exception as e:
        raise Exception(f"Yahoo Finance error: {e}")


def download_multiple_binance(
    symbol: str = "BTCUSDT",
    interval: str = "1h",
    total_candles: int = 2000
) -> pd.DataFrame:
    """
    Download more than 1000 candles from Binance by making multiple requests

    Parameters:
    -----------
    symbol : str
        Trading pair
    interval : str
        Timeframe
    total_candles : int
        Total number of candles desired

    Returns:
    --------
    pd.DataFrame
        OHLC data
    """

    all_data = []
    limit_per_request = 1000
    requests_needed = (total_candles // limit_per_request) + 1

    end_time = None

    for i in range(requests_needed):
        url = "https://api.binance.com/api/v3/klines"

        params = {
            "symbol": symbol.upper(),
            "interval": interval,
            "limit": limit_per_request
        }

        if end_time:
            params["endTime"] = end_time

        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if not data:
                break

            all_data = data + all_data  # Prepend older data

            # Set end_time to earliest timestamp - 1ms for next request
            end_time = data[0][0] - 1

            if len(all_data) >= total_candles:
                break

        except Exception as e:
            print(f"Request {i+1} failed: {e}")
            break

    if not all_data:
        raise Exception("No data downloaded")

    # Convert to DataFrame
    df = pd.DataFrame(all_data, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_volume', 'trades', 'taker_buy_base',
        'taker_buy_quote', 'ignore'
    ])

    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df = df.set_index('timestamp')
    df.index.name = 'date'

    df = df[['open', 'high', 'low', 'close', 'volume']]

    for col in df.columns:
        df[col] = df[col].astype(float)

    # Take only requested amount
    df = df.tail(total_candles)

    return df


def validate_ohlc(df: pd.DataFrame) -> bool:
    """
    Validate OHLC data format

    Parameters:
    -----------
    df : pd.DataFrame
        Data to validate

    Returns:
    --------
    bool
        True if valid

    Raises:
    -------
    ValueError
        If data is invalid
    """

    # Check required columns
    required_cols = ['open', 'high', 'low', 'close']
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")

    # Check datetime index
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError("Index must be DatetimeIndex")

    # Check OHLC logic
    if not (df['high'] >= df['low']).all():
        raise ValueError("High must be >= Low")

    if not (df['high'] >= df['open']).all():
        raise ValueError("High must be >= Open")

    if not (df['high'] >= df['close']).all():
        raise ValueError("High must be >= Close")

    if not (df['low'] <= df['open']).all():
        raise ValueError("Low must be <= Open")

    if not (df['low'] <= df['close']).all():
        raise ValueError("Low must be <= Close")

    # Check for NaN
    if df[required_cols].isna().any().any():
        raise ValueError("Data contains NaN values")

    return True


def save_to_csv(df: pd.DataFrame, filename: str):
    """Save DataFrame to CSV"""
    df.to_csv(filename)
    print(f"✅ Saved {len(df)} candles to {filename}")


if __name__ == "__main__":
    print("📊 Data Downloader Test\n")

    # Test Binance
    print("1. Testing Binance download...")
    try:
        df = download_binance("BTCUSDT", "1h", 500)
        print(f"   ✅ Downloaded {len(df)} candles from Binance")
        print(f"   Date range: {df.index[0]} to {df.index[-1]}")
        print(f"   Price range: ${df['close'].min():.2f} - ${df['close'].max():.2f}")
        validate_ohlc(df)
        print("   ✅ Data validation passed")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    print()

    # Test multiple requests
    print("2. Testing Binance multi-request download...")
    try:
        df = download_multiple_binance("BTCUSDT", "1h", 2000)
        print(f"   ✅ Downloaded {len(df)} candles")
        print(f"   Date range: {df.index[0]} to {df.index[-1]}")
        save_to_csv(df, "BTCUSDT_2000.csv")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    print()

    # Test Yahoo Finance
    print("3. Testing Yahoo Finance download...")
    try:
        df = download_yfinance("BTC-USD", "1h", "1mo")
        print(f"   ✅ Downloaded {len(df)} candles from Yahoo Finance")
        print(f"   Date range: {df.index[0]} to {df.index[-1]}")
        validate_ohlc(df)
        print("   ✅ Data validation passed")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    print("\n✅ Data downloader ready!")
