# Sector Rotation Agent

## Overview
Name: Sector Rotation Agent
Purpose: Predict and explain short-to-medium-term sector rotation signals and expose them for an iPhone dashboard that displays ranked sectors, confidence, time-series charts, and natural-language explanations.

Core responsibilities:
- Ingest sector/ETF price and optional fundamentals data
- Compute technical and fundamental indicators
- Produce a combined sector score and rank with confidence and reasons
- Provide endpoints for dashboard payloads, backtests, and explanations

## UX Goals
- Dashboard: ranked sectors with score, confidence, sparkline, and explanation
- Drilldown: time-series chart and indicator overlays for each sector
- Backtest: allow date range + rebalance frequency and show metrics
- Refresh: manual and scheduled daily updates

## Inputs
- Price series (OHLCV) per sector ETF/ticker
- Sector mapping (ETF ↔ sector)
- Optional fundamentals / factor data
- User parameters: lookbacks, rebalance freq, universe

## Outputs
- ranking: [{ ticker, sector, score, confidence, weight_breakdown }]
- chart_data: per-ticker series for plotting
- explanation_text: LLM-generated human explanation per ticker
- backtest result + metrics

## Skills / API Capabilities (each exposed as a backend endpoint)
1) fetch_market_data
- Purpose: return OHLCV for tickers & range
- Input: { tickers: [string], start: ISODate, end: ISODate, granularity: "daily"|"hourly" }
- Output: { ticker: string, data: [{date, open, high, low, close, volume}, ...] }

2) compute_indicators
- Purpose: calculate SMA, EMA, RSI, MACD, momentum, volatility, returns
- Input: { ticker: string, data: [...], indicators: ["SMA_50","RSI_14",...] }
- Output: { ticker, indicators: {SMA_50: value, RSI_14: value, ...} }

3) score_sectors
- Purpose: combine indicators into a single score and confidence
- Input: { tickers: [string], indicator_matrix: {...}, strategy_params: {...} }
- Output: { rankings: [{ticker, score, weights:{momentum:..,vol:..,value:..}, confidence}], timestamp }

4) explain_score
- Purpose: produce human-readable explanation for a sector’s score
- Input: { ticker, score, weight_breakdown, recent_sample: [{date,close}, ...], tone: "concise"|"detailed" }
- Output: { explanation_text }

5) generate_dashboard_payload
- Purpose: aggregate ranking + charts + explanations for the app
- Input: { rankings, chart_data, backtest_summary }
- Output: { dashboard_json }

6) backtest_strategy
- Purpose: run historical backtest for chosen strategy
- Input: { tickers, start, end, rebalance_period: "weekly"|"monthly", transaction_costs }
- Output: { returns_series, metrics: {CAGR, max_drawdown, vol, sharpe, turnover} }

7) manage_credentials
- Purpose: securely store or retrieve API keys for data/LLM
- Input: { action:"get"|"set"|"delete", key_name, encrypted_value? }
- Output: { success, details }

8) schedule_job (optional)
- Purpose: schedule periodic scoring runs (cron)
- Input: { job_name, cron_expression, payload_endpoint }
- Output: { job_id, status }

## Minimal API (REST) — example endpoints
GET  /api/v1/dashboard?tickers=XLK,XLV&start=2024-01-01&end=2026-07-20
POST /api/v1/score  -> Body: { tickers, strategy_params }  => Response: rankings + timestamp
POST /api/v1/backtest -> Body: { tickers, start, end, rebalance_period } => Response: metrics + returns
POST /api/v1/explain -> Body: { ticker, score, weight_breakdown, sample } => Response: explanation_text

## Data Sources (pick one)
- Prototyping: Yahoo Finance (yfinance / yfinance-HTTP) — free but rate-limited
- Production: Polygon.io, IEX Cloud, or Quandl — paid, reliable
- Sector mapping: use official ETF tickers (XLF, XLK, XLY, XLP, XLI, XLE, XLV, XLB, XLRE, XLU, XLC, XBI, etc.) or S&P sector membership

## Models & scoring ideas
- Momentum-based core: 3/6/12m returns, normalized to z-scores
- Add volatility penalty, low-vol bonus, fundamental factor if available
- Score = weighted sum (momentum_z*wm + accel_z*wa - vol_z*wv + fundamental_z*wf)
- Confidence = function(data_completeness, dispersion, recent volatility)

## iOS Integration (architecture)
- SwiftUI + Combine
- Networking: URLSession or Alamofire
- Charting: Apple Charts (iOS 16+) or Swift Charts package
- Local cache: Core Data or SQLite; secrets in Keychain
- Data format: compact JSON with arrays for time series

## Security
- Do not embed data provider API keys in the app. Use backend secrets or short-lived tokens.
- Use HTTPS, authenticate endpoints (API key or OAuth) if the backend is private.

## Implementation roadmap (MVP)
1. Prototype backend: fetch_market_data (yfinance) + compute_indicators + score_sectors (simple momentum)
2. API: /score and /dashboard returning mock chart_data
3. iOS app: SwiftUI that calls /dashboard and renders ranking + one chart
4. Add explain_score using LLM API
5. Backtest endpoint and scheduled daily scoring

## Next steps
- Choose: (A) Backend-hosted pipeline or (B) On-device-only (limited)
- Choose a data provider and whether to use an LLM provider (OpenAI/Anthropic) or local model
- I can scaffold backend or iOS skeleton on request
