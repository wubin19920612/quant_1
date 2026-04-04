# BTC Options IV/RV Monitor

A terminal UI application for monitoring BTC options implied volatility (IV) versus realized volatility (RV) across Deribit and OKX, with real-time alerts and cross-exchange divergence detection.

## Features

- Real-time IV/RV dashboard with cross-exchange comparison
- Volatility smile plot by strike
- Term structure plot by expiry
- IV spike alert detection
- Cross-exchange IV divergence alerts
- Telegram notifications
- Async SQLite storage for historical data

## Installation

```bash
pip install -e .
# or
pip install -r requirements.txt
```

Dependencies: `textual`, `textual-plotext`, `websockets`, `aiosqlite`, `scipy`, `numpy`, `pyyaml`, `httpx`

## Usage

```bash
python -m src.main
# or, if installed via pip
btc-options-monitor
```

The app loads `config.yaml` from the working directory on startup.

## Configuration

`config.yaml` example:

```yaml
exchanges:
  deribit:
    enabled: true
    ws_url: "wss://www.deribit.com/ws/api/v2"
  okx:
    enabled: true
    ws_url: "wss://ws.okx.com:8443/ws/v5/public"

alerts:
  iv_rv_ratio_high: 1.5
  iv_rv_ratio_low: 0.5
  iv_spike_pct: 0.20
  iv_spike_window_min: 30
  cross_exchange_iv_diff: 0.05
  cooldown_min: 5
  telegram:
    enabled: false
    bot_token: ""
    chat_id: ""
```

## Architecture

```
src/
  models.py                  # OptionTicker, AlertEvent, Signal
  storage/db.py              # async SQLite storage
  analytics/
    iv_calc.py               # BSM implied volatility (brentq solver)
    rv_calc.py               # realized volatility calculator
    scorer.py                # IV/RV scoring
    alerts.py                # alert engine
  exchanges/
    base.py                  # WebSocket base adapter
    deribit.py               # Deribit adapter
    okx.py                   # OKX adapter
  notifications/
    telegram.py              # Telegram notification client
  ui/
    dashboard.py             # IV/RV dashboard panel
    vol_smile.py             # volatility smile plot
    term_structure.py        # term structure plot
    alert_log.py             # alert log panel
  app.py                     # MonitorApp (Textual App)
  main.py                    # CLI entry point
```

## Testing

```bash
pytest
```

Target: 80%+ coverage.

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| F1  | IV/RV Dashboard |
| F2  | Volatility Smile |
| F3  | Term Structure |
| F4  | Alert Log |
| Q   | Quit |
