from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.constants import CURRENCIES
from app.main import create_app
from app.services.money import rounded


def payload():
    return {'base': 'CNY', 'date': '2026-11-17', 'rates': {code: 0.125 for code in CURRENCIES[1:]}}


@pytest.fixture
def app(tmp_path):
    return create_app(tmp_path / 'core.db', today_provider=lambda: date(2026, 11, 18), rates_fetcher=payload)


def test_rounding_uses_half_up_and_supports_valid_large_values():
    assert rounded('2.675') == 2.68
    assert rounded('-2.675') == -2.68
    assert rounded('1000000000000000000000000000000') == 1e30


@pytest.mark.parametrize('bad_payload', [
    {'base': 'USD', 'date': '2026-11-18', 'rates': {code: 1 for code in CURRENCIES[1:]}},
    {'base': 'CNY', 'rates': {}},
    {'base': 'CNY', 'rates': {code: 0 for code in CURRENCIES[1:]}},
    {'base': 'CNY', 'rates': {code: float('inf') for code in CURRENCIES[1:]}},
    {'base': 'CNY', 'rates': {code: 5e-324 for code in CURRENCIES[1:]}},
])
def test_bad_rate_response_preserves_entire_cache(app, bad_payload):
    with TestClient(app) as client:
        assert client.get('/api/currencies').status_code == 200
        app.state.rates_fetcher = lambda: bad_payload
        result = client.post('/api/rates/refresh')
        assert result.status_code == 200
        assert result.json()['refreshed'] is False
        assert next(r for r in result.json()['currencies'] if r['code'] == 'USD')['rate'] == 8


def test_offline_empty_dashboard_supports_cny_without_fake_rates(tmp_path):
    def unavailable():
        raise ConnectionError('offline')
    app = create_app(tmp_path / 'offline.db', rates_fetcher=unavailable)
    with TestClient(app) as client:
        response = client.get('/api/dashboard')
        assert response.status_code == 200
        assert response.json()['net_worth'] == {'total_cny': 0, 'trend': []}
        assert response.json()['rates_stale'] is True
        currencies = client.get('/api/currencies').json()['currencies']
        assert currencies[0]['rate'] == 1
        assert all(row['rate'] is None for row in currencies[1:])
        assert client.post('/api/transactions', json={'type': 'income', 'amount': 50, 'currency': 'CNY', 'tx_date': '2026-11-18', 'category': 'salary'}).status_code == 201
        assert client.post('/api/transactions', json={'type': 'income', 'amount': 50, 'currency': 'USD', 'tx_date': '2026-11-18', 'category': 'salary'}).status_code == 409


def test_refresh_does_not_fetch_twice_on_first_call(tmp_path):
    calls = []
    def fetch():
        calls.append(1)
        return payload()
    app = create_app(tmp_path / 'fetch.db', rates_fetcher=fetch)
    with TestClient(app) as client:
        assert client.post('/api/rates/refresh').status_code == 200
        assert len(calls) == 1


def test_delete_closed_holding_preserves_realized_pnl_and_trade_history(app):
    with TestClient(app) as client:
        holding = client.post('/api/investments/holdings', json={'symbol': 'TEST', 'name': '测试', 'asset_type': 'stock', 'quantity': 10, 'avg_cost': 5, 'current_price': 6}).json()
        trade = client.post('/api/investments/trades', json={'holding_id': holding['id'], 'action': 'sell', 'quantity': 10, 'price': 7, 'fee': 1, 'trade_date': '2026-11-18'})
        assert trade.json()['realized_pnl'] == 19
        assert client.delete(f"/api/investments/{holding['id']}").status_code == 204
        assert client.get('/api/investments/summary').json()['realized_pnl_all_cny'] == 19
        trades = client.get('/api/investments/trades').json()
        assert len(trades) == 2
        assert trades[0]['symbol'] == 'TEST'
        assert trades[0]['holding_id'] is None


def test_duplicate_dream_purchase_after_reset_requires_expense_removal(app):
    with TestClient(app) as client:
        dream = client.post('/api/dreams', json={'name': '相机', 'price': 100}).json()
        purchase = client.post(f"/api/dreams/{dream['id']}/purchase", json={}).json()
        assert client.put(f"/api/dreams/{dream['id']}", json={'status': 'pending'}).status_code == 200
        assert client.post(f"/api/dreams/{dream['id']}/purchase", json={}).status_code == 409
        assert client.delete(f"/api/transactions/{purchase['transaction']['id']}").status_code == 204
        assert client.post(f"/api/dreams/{dream['id']}/purchase", json={}).status_code == 200


@pytest.mark.parametrize('patch', [{'name': ''}, {'balance': None}, {'balance': -1}, {'unknown': 2}])
def test_failed_asset_update_does_not_change_balance_or_snapshot(app, patch):
    with TestClient(app) as client:
        asset = client.post('/api/assets', json={'name': '现金', 'category': 'cash', 'balance': 100}).json()
        result = client.put(f"/api/assets/{asset['id']}", json=patch)
        assert result.status_code == 422
        assert client.get('/api/assets').json()['total_cny'] == 100
        assert client.get('/api/networth/history').json()[0]['total_cny'] == 100
