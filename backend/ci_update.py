"""
backend/ci_update.py

Run in CI (GitHub Actions) to fetch prices and write docs/scores.json.
This is a thin wrapper around backend.etf_loader to produce a JSON output
suitable for the static frontend.

This updated version fixes two issues that caused CI failures:
- imports pandas as pd at module level so pd.isna is available
- fixes the incorrect args access in the __main__ block
- adds top-level exception handling to write a short debug file to docs/fetch_log.txt
- safely serializes rank values (allow None)
"""

import argparse
import json
import traceback
from datetime import datetime

import pandas as pd

from backend.etf_loader import read_etfs, fetch_prices, sector_scores, trailing_returns


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
    # scores_df is indexed by sector
    for sector_name, row in scores_df.reset_index().set_index('sector').iterrows():
        # safe trailing_return and zscore extraction
        tr_val = row.get("trailing_return")
        zs_val = row.get("zscore")
        rank_val = row.get("rank")
        try:
            rank_out = int(rank_val) if pd.notna(rank_val) else None
        except Exception:
            rank_out = None

        out["sectors"].append({
            "sector": sector_name,
            "trailing_return": None if pd.isna(tr_val) else float(tr_val),
            "zscore": None if pd.isna(zs_val) else float(zs_val),
            "rank": rank_out
        })

    # Also include per-ticker trailing returns (for reference)
    tr = trailing_returns(prices, lookback_days=lookback)
    ticker_returns = {}
    # tr may be a Series or DataFrame; handle Series case
    if isinstance(tr, (pd.Series,)):
        for t in tr.index:
            val = tr.loc[t]
            ticker_returns[str(t)] = None if pd.isna(val) else float(val)
    else:
        # fallback: try to convert
        try:
            for t in tr.index:
                val = tr.loc[t]
                ticker_returns[str(t)] = None if pd.isna(val) else float(val)
        except Exception:
            pass

    out["ticker_trailing_return"] = ticker_returns

    # Write to docs/scores.json
    with open("docs/scores.json", "w", encoding="utf8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)

    print("Wrote docs/scores.json")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--etf-csv", default="data/etfs.csv")
    parser.add_argument("--period", default="1y")
    parser.add_argument("--lookback", type=int, default=63)
    args = parser.parse_args()

    try:
        main(args.etf_csv, args.period, args.lookback)
    except Exception as exc:
        tb = traceback.format_exc()
        # Write a short debug file so you can inspect it from the repo if the run fails
        try:
            with open("docs/fetch_log.txt", "w", encoding="utf8") as lf:
                lf.write("Exception during CI update:\n")
                lf.write(tb)
        except Exception:
            pass
        print("Error during CI update:")
        print(tb)
        raise
