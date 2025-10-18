# data_manager.py

import pandas as pd
import yfinance as yf

VALID_PERIODS = ["1m", "5m", "15m", "30m", "60m", "1h", "1d", "1wk", "1mo"]

def fetch_data(ticker: str, start_date: str, end_date: str, period: str = "1d") -> pd.DataFrame:
    """
    Fetch OHLC data from Yahoo Finance for a given ticker and period.

    Args:
        ticker (str): Ticker symbol (e.g., 'AAPL').
        start_date (str): Start date in 'YYYY-MM-DD' format.
        end_date (str): End date in 'YYYY-MM-DD' format.
        period (str): Data frequency/interval ('1m', '5m', '15m', '1h', '1d', '1wk', '1mo').

    Returns:
        pd.DataFrame: OHLCV data with forward-filled missing/zero values.
    """
    period = period.lower()
    if period not in VALID_PERIODS:
        raise ValueError(f"Invalid period '{period}'. Valid options: {VALID_PERIODS}")

    # Download data
    df = yf.download(ticker, start=start_date, end=end_date, interval=period, progress=False)

    if df.empty:
        raise ValueError(f"No data returned for {ticker} between {start_date} and {end_date} at interval {period}.")

    # Replace 0 or NaN values with forward fill
    df.replace(0, pd.NA, inplace=True)
    df.fillna(method="ffill", inplace=True)

    # Print info
    print(f"Downloaded {len(df)} rows for {ticker} from {df.index.min().date()} to {df.index.max().date()} at interval {period}")

    return df
