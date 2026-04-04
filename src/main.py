from __future__ import annotations
import argparse
import logging
import os

def main() -> None:
    parser = argparse.ArgumentParser(description="BTC Options IV/RV Monitor")
    parser.add_argument("-c", "--config", default="config.yaml", help="Path to config file")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")
    args = parser.parse_args()
    level = logging.DEBUG if args.verbose else logging.WARNING
    logging.basicConfig(level=level, format="%(asctime)s %(name)s %(levelname)s %(message)s", filename="data/monitor.log")
    os.makedirs("data", exist_ok=True)
    from src.app import MonitorApp
    app = MonitorApp(config_path=args.config)
    app.run()

if __name__ == "__main__":
    main()
