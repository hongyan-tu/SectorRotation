"""
backend/etf_loader.py

Utilities to load the ETF list, fetch price data from yfinance, and compute simple
sector-level scores suitable for a sector-rotation model.

Dependencies: pandas, numpy, yfinance

Functions:
- read_etfs(path='data/etfs.csv') -> pandas.DataFrame
- fetch_prices(tickers, start=None, end=None, period=None, interval='1d') -> DataFrame of adjusted close prices
- compute_returns(prices) -> DataFrame of simple pct change returns
- trailing_returns(prices, lookback_days) -> Series of trailing returns per ticker
- sector_scores(etfs_df, prices, lookback_days=63, agg='mean') -> DataFrame with sector metrics and scores

Example usage (module run as script):
    etfs = read_etfs()
    tickers = etfs.ticker.tolist()
    prices = fetch_prices(tickers, period='1y')
    scores = sector_scores(etfs, prices, lookback_days=63)
    print(scores)

"""

from typing import List, Optional
import pandas as pd
import numpy as np
import yfinance as yf


def read_etfs(path: str = "data/etfs.csv") -> pd.DataFrame:
    """Read the CSV of ETFs into a DataFrame.

    Expected minimal schema: ticker,name,sector,type
    """
    df = pd.read_csv(path, dtype=str)
    df.columns = [c.strip() for c in df.columns]
    # Normalize column names
    for col in ("ticker", "name", "sector", "type"):
        if col not in df.columns:
            raise ValueError(f"Expected column '{col}' in {path}")
    df = df[["ticker", "name", "sector", "type"]].copy()
    df["ticker"] = df["ticker"].str.strip().str.upper()
    return df


def fetch_prices(tickers: List[str], start: Optional[str] = None, end: Optional[str] = None,
                 period: Optional[str] = None, interval: str = "1d") -> pd.DataFrame:
    """Fetch historical adjusted close prices for tickers using yfinance.

    - tickers: list of symbols; yfinance accepts a space or list-separated string
    - start/end: YYYY-MM-DD strings (optional)
    - period: if provided (e.g., "1y", "6mo") it overrides start/end
    - interval: data frequency, e.g. '1d', '1wk'

    Returns a DataFrame of adjusted close prices indexed by date, columns=tickers.
    """
    if not tickers:
        return pd.DataFrame()
    tickers_str = " ".join(tickers)
    # yfinance returns a DataFrame with columns like ('Adj Close', ticker) when multiple
    data = yf.download(tickers_str, start=start, end=end, period=period, interval=interval, group_by='ticker', auto_adjust=True, threads=True)

    # When multiple tickers are fetched, yfinance returns a DataFrame with a column level
    # ['Adj Close'] or similar. Simpler: try to extract 'Adj Close' if present, otherwise use Close.
    if isinstance(data.columns, pd.MultiIndex):
        if "Adj Close" in data.columns.levels[0]:
            prices = data["Adj Close"].copy()
        elif "Close" in data.columns.levels[0]:
            prices = data["Close"].copy()
        else:
            # fallback: pick the last level as price
            prices = data.iloc[:, data.columns.get_level_values(1).duplicated(keep='first') == False]
    else:
        # Single ticker case: data is a regular DataFrame with columns like Open, Close, etc.
        if "Adj Close" in data.columns:
            prices = data["Adj Close"].to_frame()
            prices.columns = [tickers[0]]
        elif "Close" in data.columns:
            prices = data["Close"].to_frame()
            prices.columns = [tickers[0]]
        else:
            raise RuntimeError("Unexpected yfinance data format")

    # Ensure columns are ticker symbols and sorted as requested
    prices = prices.reindex(columns=tickers)
    prices.sort_index(inplace=True)
    return prices


def compute_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """Compute simple percent-change returns from price DataFrame."""
    return prices.pct_change().dropna(how='all')


def trailing_returns(prices: pd.DataFrame, lookback_days: int = 63) -> pd.Series:
    """Compute trailing simple return over lookback_days for each ticker.

    Uses price[today] / price[lookback_days_ago] - 1. If not enough history for a ticker,
    that ticker will be NaN.
    """
    if prices.shape[0] <= lookback_days:
        # Not enough rows to compute; return percent change from first to last
        return (prices.iloc[-1] / prices.iloc[0] - 1).rename("trailing_return")

    past = prices.shift(lookback_days).iloc[-1]
    latest = prices.iloc[-1]
    tr = (latest / past - 1).rename("trailing_return")
    return tr


def sector_scores(etfs_df: pd.DataFrame, prices: pd.DataFrame, lookback_days: int = 63,
                  agg: str = "mean") -> pd.DataFrame:
    """Compute simple sector-level scores using trailing returns.

    Steps:
      1. Compute trailing returns per ticker over lookback_days
      2. Aggregate returns by sector (mean or median)
      3. Standardize across sectors to produce a z-score (higher = better)
      4. Return DataFrame with sector, trailing_return, zscore, rank

    Returns a DataFrame indexed by sector.
    """
    # Ensure tickers in etfs_df exist in prices
    tickers = etfs_df["ticker"].tolist()
    missing = [t for t in tickers if t not in prices.columns]
    if missing:
        # Allow benchmarks like SPY/QQQ to be missing if user didn't fetch them, but warn via NaN
        # We'll drop tickers that are completely missing prices
        tickers = [t for t in tickers if t in prices.columns]

    if not tickers:
        raise ValueError("No tickers with price data available for scoring")

    tr = trailing_returns(prices[tickers], lookback_days=lookback_days)
    # Merge trailing returns into the etfs_df
    etfs = etfs_df.set_index("ticker").loc[tr.index if isinstance(tr, pd.Series) and False else etfs_df["ticker"]]  # keep original order
    # Convert tr to Series indexed by ticker
    if isinstance(tr, pd.Series):
        tr_series = tr
    else:
        tr_series = tr

    # Build DataFrame of ticker -> trailing_return
    tr_df = pd.DataFrame({"ticker": tr_series.index, "trailing_return": tr_series.values})
    merged = etfs_df.merge(tr_df, on="ticker", how="left")

    # Only aggregate rows with type == 'sector' when producing sector-level signals
    sector_rows = merged[merged.type == "sector"].copy()
    if sector_rows.empty:
        raise ValueError("No sector ETFs found in etfs_df (type=='sector')")

    if agg == "mean":
        sector_ret = sector_rows.groupby("sector")["trailing_return"].mean()
    elif agg == "median":
        sector_ret = sector_rows.groupby("sector")["trailing_return"].median()
    else:
        raise ValueError("agg must be 'mean' or 'median'")

    sector_df = sector_ret.to_frame(name="trailing_return")
    # Standardize (z-score) across sectors
    mu = sector_df["trailing_return"].mean()
    sigma = sector_df["trailing_return"].std(ddof=0)
    if sigma == 0 or np.isnan(sigma):
        sector_df["zscore"] = 0.0
    else:
        sector_df["zscore"] = (sector_df["trailing_return"] - mu) / sigma

    sector_df["rank"] = sector_df["trailing_return"].rank(ascending=False, method="min").astype(int)
    sector_df.sort_values("rank", inplace=True)
    return sector_df


if __name__ == "__main__":
    # Example quick run
    import argparse

    parser = argparse.ArgumentParser(description="Fetch ETF prices and compute simple sector scores")
    parser.add_argument("--etf-csv", default="data/etfs.csv", help="path to ETF CSV (ticker,name,sector,type)")
    parser.add_argument("--period", default="1y", help="yfinance period (e.g., 1y,6mo)")
    parser.add_argument("--lookback", type=int, default=63, help="lookback days for trailing returns (default 63)")
    args = parser.parse_args()

    etfs = read_etfs(args.etf_csv)
    tickers = etfs.ticker.tolist()
    print(f"Fetching prices for: {', '.join(tickers)}")
    prices = fetch_prices(tickers, period=args.period)
    if prices.empty:
        raise SystemExit("No price data fetched. Check yfinance or ticker symbols.")

    scores = sector_scores(etfs, prices, lookback_days=args.lookback)
    print("\nSector scores (higher = better):\n")
    print(scores.to_string())
