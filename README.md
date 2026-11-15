# ORBIT AI v28.0 — Supreme Institutional Quantitative Matrix

A cutting-edge, ultra-high-performance algorithmic cryptocurrency trading intelligence suite scanning **all 9 timeframes (`1m`, `3m`, `5m`, `15m`, `30m`, `1h`, `4h`, `1d`, `1w`)** across **120+ Institutional Smart Money Concepts (SMC), Advanced Order-Flow Imbalances, Liquidity Engineering, Wyckoff Accumulation/Distribution, and Dynamic Volatility Factors**.

## Architecture Overview
- **`engine/`**: Core multi-threaded Python quantitative engine implementing 120+ advanced algorithmic rules, Kelly Criterion optimal sizing, multi-timeframe structural mapping, and automated MFE/MAE performance tracking.
- **`backend/`**: High-performance FastAPI & WebSocket server (`server.py`) streaming live Binance Futures order books, executing real-time tensor computations, and broadcasting high-conviction setups.
- **`frontend/`**: Cyberpunk-inspired tactical command dashboard (`index.html`) featuring real-time telemetry charts, advanced factor inspection modals, live matrix heatmaps, and instant deployment tools.

## Quick Start
```bash
cd backend
pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 8000 --reload
