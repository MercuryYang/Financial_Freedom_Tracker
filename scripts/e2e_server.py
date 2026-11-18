"""Isolated browser-test application; never used by the production entry point."""

import os
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.main import create_app


def create_test_app():
    # Explicit fixture values make UI conversion assertions independent of markets.
    cny_rates = {"USD": 7.2}
    fixed_day = date(2026, 11, 18)
    return create_app(
        db_path=os.environ["FFT_E2E_DB_PATH"],
        today_provider=lambda: fixed_day,
        rates_fetcher=lambda: {
            "base": "CNY", "date": fixed_day.isoformat(),
            "rates": {currency: 1 / rate for currency, rate in cny_rates.items()},
        },
    )
