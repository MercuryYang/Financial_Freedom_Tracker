import logging
import math
import os
from datetime import date, datetime, timedelta, timezone

import httpx
from sqlalchemy import select

from ..constants import CURRENCIES
from ..models import ExchangeRate, utcnow

logger = logging.getLogger(__name__)


def fetch_rates():
    url = os.getenv('RATES_URL', 'https://api.frankfurter.dev/v1/latest')
    response = httpx.get(url, params={'base': 'CNY', 'symbols': ','.join(CURRENCIES[1:])}, timeout=5, follow_redirects=True)
    response.raise_for_status()
    return response.json()


def naive_utc(value):
    return value.astimezone(timezone.utc).replace(tzinfo=None) if value and value.tzinfo else value


def ensure_rates_fresh(db, state, force=False):
    now = utcnow()
    rows = list(db.scalars(select(ExchangeRate)))
    latest = min((naive_utc(r.fetched_at) for r in rows), default=None)
    complete = all(code in {r.currency for r in rows} for code in CURRENCIES[1:])
    if not force and complete and latest and now - latest < timedelta(hours=24):
        return True
    attempt = getattr(state, 'rates_last_attempt', None)
    if not force and attempt and now - attempt < timedelta(seconds=60):
        return False
    try:
        payload = state.rates_fetcher()
        if payload.get('base', 'CNY') != 'CNY':
            raise ValueError('Expected CNY base')
        rates = payload['rates']
        reference_date = date.fromisoformat(payload['date']) if payload.get('date') else None
        # Validate the entire response before changing any cached row.
        parsed = {}
        for code in CURRENCIES[1:]:
            value = float(rates[code])
            if not math.isfinite(value) or value <= 0:
                raise ValueError('Invalid exchange rate')
            inverse = 1 / value
            if not math.isfinite(inverse):
                raise ValueError('Invalid inverse exchange rate')
            parsed[code] = inverse
    except Exception as exc:
        state.rates_last_attempt = now
        logger.warning('Exchange-rate refresh unavailable; preserving cache: %s', type(exc).__name__)
        return False
    # A later business error can roll this transaction back. Successful fetches
    # must not set a throttle that would prevent rebuilding the missing cache.
    state.rates_last_attempt = None
    existing = {row.currency: row for row in rows}
    for code, value in parsed.items():
        row = existing.get(code)
        if row is None:
            row = ExchangeRate(currency=code, rate=value, fetched_at=now)
            db.add(row)
        row.rate = value
        row.fetched_at = now
        row.reference_date = reference_date
    db.flush()
    return True


def rate_status(db):
    rows = list(db.scalars(select(ExchangeRate)))
    fetched = min((naive_utc(row.fetched_at) for row in rows), default=None)
    complete = all(code in {r.currency for r in rows} for code in CURRENCIES[1:])
    stale = not complete or not fetched or utcnow() - fetched >= timedelta(hours=24)
    updated = fetched.isoformat(timespec='seconds') + 'Z' if fetched else None
    reference = min((row.reference_date for row in rows if row.reference_date), default=None)
    return {'rates_stale': bool(stale), 'rates_updated_at': updated, 'rates_reference_date': reference}


def currency_payload(db):
    rows = {row.currency: row for row in db.scalars(select(ExchangeRate))}
    return {
        'currencies': [
            {'code': code, 'rate': 1.0 if code == 'CNY' else (rows[code].rate if code in rows else None),
             'fetched_at': (naive_utc(rows[code].fetched_at).isoformat(timespec='seconds') + 'Z') if code in rows else None}
            for code in CURRENCIES
        ],
        **rate_status(db),
    }
