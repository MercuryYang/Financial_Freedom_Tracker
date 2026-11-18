from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.main import create_app
from app import models


@pytest.fixture
def ledger(tmp_path):
    app = create_app(
        tmp_path / 'currencies.db',
        today_provider=lambda: date(2026, 11, 18),
        rates_fetcher=lambda: {
            'base': 'CNY', 'date': '2026-11-17', 'rates': {'USD': 0.125},
        },
    )
    with TestClient(app) as client:
        yield app, client


def test_currency_api_accepts_usd_only_rate_response(ledger):
    _, client = ledger
    response = client.post('/api/rates/refresh')
    assert response.status_code == 200
    payload = response.json()
    assert payload['refreshed'] is True
    assert payload['rates_stale'] is False
    assert [(row['code'], row['rate']) for row in payload['currencies']] == [
        ('CNY', 1), ('USD', 8),
    ]
    assert [row['code'] for row in client.get('/api/currencies').json()['currencies']] == ['CNY', 'USD']
    created = client.post('/api/transactions', json={
        'type': 'income', 'amount': 100, 'currency': 'USD',
        'tx_date': '2026-11-18', 'category': 'salary',
    })
    assert created.status_code == 201
    assert created.json()['amount_cny'] == 800


@pytest.mark.parametrize('path,update_path,model,payload', [
    ('/transactions', '/transactions', models.Transaction,
     {'type': 'income', 'amount': 100, 'tx_date': '2026-11-18', 'category': 'salary'}),
    ('/recurring', '/recurring', models.RecurringRule,
     {'type': 'income', 'amount': 100, 'day_of_month': 30, 'category': 'salary'}),
    ('/goals', '/goals', models.SavingsGoal,
     {'name': '目标', 'target_amount': 1000}),
    ('/assets', '/assets', models.AssetAccount,
     {'name': '账户', 'category': 'cash', 'balance': 100}),
    ('/dreams', '/dreams', models.DreamItem,
     {'name': '心愿', 'price': 100}),
    ('/investments/holdings', '/investments', models.InvestmentHolding,
     {'name': '标的', 'symbol': 'TEST', 'asset_type': 'stock', 'current_price': 10}),
])
def test_unsupported_currency_rejected_without_changing_records(ledger, path, update_path, model, payload):
    app, client = ledger
    rejected = client.post('/api' + path, json={**payload, 'currency': 'EUR'})
    assert rejected.status_code == 422, rejected.text
    with app.state.session_factory() as db:
        assert db.scalar(select(func.count()).select_from(model)) == 0

    created = client.post('/api' + path, json={**payload, 'currency': 'CNY'})
    assert created.status_code == 201, created.text
    identity = created.json()['id']
    rejected = client.put(f'/api{update_path}/{identity}', json={'currency': 'EUR'})
    assert rejected.status_code == 422, rejected.text
    with app.state.session_factory() as db:
        assert db.get(model, identity).currency == 'CNY'


def test_unsupported_contribution_and_purchase_do_not_create_money_movements(ledger):
    app, client = ledger
    goal = client.post('/api/goals', json={'name': '目标', 'target_amount': 1000}).json()
    response = client.post(f"/api/goals/{goal['id']}/contributions", json={
        'amount': 100, 'currency': 'EUR', 'contributed_at': '2026-11-18',
    })
    assert response.status_code == 422
    assert client.get(f"/api/goals/{goal['id']}/contributions").json() == []

    dream = client.post('/api/dreams', json={'name': '心愿', 'price': 100}).json()
    response = client.post(f"/api/dreams/{dream['id']}/purchase", json={'currency': 'EUR'})
    assert response.status_code == 422
    with app.state.session_factory() as db:
        assert db.get(models.DreamItem, dream['id']).status == 'pending'
        assert db.scalar(select(func.count()).select_from(models.Transaction)) == 0


def test_stale_legacy_rate_does_not_expire_supported_usd_cache(ledger):
    app, client = ledger
    fresh = models.utcnow()
    with app.state.session_factory() as db:
        db.add_all([
            models.ExchangeRate(currency='USD', rate=7.2, fetched_at=fresh,
                                reference_date=date(2026, 11, 17)),
            models.ExchangeRate(currency='EUR', rate=8, fetched_at=fresh - timedelta(days=3),
                                reference_date=date(2026, 11, 14)),
        ])
        db.commit()
    calls = []

    def unexpected_fetch():
        calls.append(True)
        raise ConnectionError('The fresh USD cache should be sufficient offline')

    app.state.rates_fetcher = unexpected_fetch
    response = client.get('/api/currencies')
    assert response.status_code == 200
    payload = response.json()
    assert payload['rates_stale'] is False
    assert payload['rates_updated_at'] == fresh.isoformat(timespec='seconds') + 'Z'
    assert payload['rates_reference_date'] == '2026-11-17'
    assert [(row['code'], row['rate']) for row in payload['currencies']] == [('CNY', 1), ('USD', 7.2)]
    assert client.get('/api/dashboard').json()['rates_stale'] is False
    assert calls == []
    with app.state.session_factory() as db:
        legacy = db.scalar(select(models.ExchangeRate).where(models.ExchangeRate.currency == 'EUR'))
        assert legacy is not None and legacy.rate == 8  # Existing records are not deleted.
