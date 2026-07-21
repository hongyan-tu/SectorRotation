# SectorRotation

An experimental project to build an iPhone dashboard that predicts stock market sector rotation. This repository includes an agent manifest describing the capabilities and a starter scaffold for a FastAPI backend and SwiftUI app.

## Quick start

1. Open this repository in the GitHub mobile app or website.
2. Review agents/sector-rotation-agent.md for the API and architecture.
3. Start the backend (see backend/README or run with Docker) and run the iOS app skeleton in Xcode.

## Contents
- agents/sector-rotation-agent.md — Agent manifest and skills
- backend/ — FastAPI scaffold
- ios/ — SwiftUI app skeleton
- CHAT_WITH_COPILOT.md — Chat summary and transcript

## Next actions
- Choose a data provider (Yahoo/Polygon/IEX)
- Configure API keys in backend/.env (not included)
- Implement fetch_market_data and compute_indicators endpoints
