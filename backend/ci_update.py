"""
backend/ci_update.py

Run in CI (GitHub Actions) to fetch prices and write docs/scores.json.
This is a thin wrapper around backend.etf_loader to produce a JSON output
suitable for the static frontend.
"""

import argparse
import json
from datetime import datetime

from backend.etf_loader import read_etfs, fetch_prices, sector_scores


def main(etf_csv: str, period: str, lookback: int):
    etfs = read_etfs(etf_csv)
    tickers = etfs.ticker.tolist()
    print(f"Tickers: {tickers}")

    # Fetch prices; allow partial failures but proceed with what we have
    prices = fetch_prices(tickers, period=period)
    if prices.empty:
        raise SystemExit("No price data fetched. Exiting.")

    scores_df = sector_scores(etfs, prices, lookback_days=lookback)

    # Build output structure
    out = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "period": period,
        "lookback": lookback,
        "sectors": []
    }

    out["sectors"] = []
    for sector_name, row in scores_df.reset_index().set_index('sector').iterrows():
        out["sectors"].append({
            "sector": sector_name,
            "trailing_return": None if pd.isna(row["trailing_return"]) else float(row["trailing_return"]),
            "zscore": None if pd.isna(row["zscore"]) else float(row["zscore"]),
            "rank": int(row["rank"])
        })

    # Also include per-ticker trailing returns (for reference)
    # reuse trailing_returns from etf_loader
    from backend.etf_loader import trailing_returns
    tr = trailing_returns(prices, lookback_days=lookback)
    ticker_returns = {}
    for t in tr.index:
        val = tr.loc[t]
        ticker_returns[t] = None if pd.isna(val) else float(val)
    out["ticker_trailing_return"] = ticker_returns

    # Write to docs/scores.json
    with open("docs/scores.json", "w", encoding="utf8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)

    print("Wrote docs/scores.json")


if __name__ == "__main__":
    import pandas as pd

    parser = argparse.ArgumentParser()
    parser.add_argument("--etf-csv", default="data/etfs.csv")
    parser.add_argument("--period", default="1y")
    parser.add_argument("--lookback", type=int, default=63)
    args = parser.parse_args()
    main(args.etf_csv, args.args.period if hasattr(args, 'args') else args.period, args.lookback)
