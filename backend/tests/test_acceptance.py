"""Independent API acceptance checks for CONSTRUCTION.md §11.

These checks use a fresh on-disk SQLite database and a deterministic fake rate
provider. They do not depend on live exchange-rate services or user data.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient


EXCHANGE_TO_CNY = {
    "USD": 7.2, "EUR": 8.0, "HKD": 0.92, "JPY": 0.048,
    "GBP": 9.2, "SGD": 5.3, "AUD": 4.8, "CAD": 5.2,
    "CHF": 8.1, "KRW": 0.0052,
}


def fake_rates():
    return {
        "base": "CNY",
        "date": "2026-11-18",
        "rates": {code: 1 / rate for code, rate in EXCHANGE_TO_CNY.items()},
    }


def offline_rates():
    raise ConnectionError("isolated acceptance test: network unavailable")


@pytest.fixture
def ledger(tmp_path):
    from app.main import create_app

    clock = [date(2026, 11, 18)]
    database = tmp_path / "acceptance.sqlite3"
    app = create_app(
        db_path=str(database), today_provider=lambda: clock[0], rates_fetcher=fake_rates,
    )
    with TestClient(app) as client:
        yield client, app, clock, database
    app.state.engine.dispose()


def request_json(client, method, path, payload=None):
    kwargs = {} if payload is None else {"json": payload}
    response = client.request(method, "/api" + path, **kwargs)
    assert 200 <= response.status_code < 300, response.text
    return None if response.status_code == 204 else response.json()


def transaction(client, *, kind="expense", amount=100, currency="CNY", category="food", day="2026-11-18"):
    return request_json(client, "POST", "/transactions", {
        "type": kind, "amount": amount, "currency": currency,
        "category": category, "tx_date": day, "note": "验收测试",
    })


def test_usd_income_preserves_original_and_updates_monthly_dashboard(ledger):
    client, _, _, _ = ledger
    created = transaction(client, kind="income", amount=100, currency="USD", category="salary")
    assert created["amount"] == 100
    assert created["currency"] == "USD"
    assert created["amount_cny"] == pytest.approx(720)
    rows = request_json(client, "GET", "/transactions?month=2026-11&type=income")
    assert len(rows) == 1
    assert rows[0]["amount_cny"] == pytest.approx(720)
    summary = request_json(client, "GET", "/transactions/summary?month=2026-11")
    assert summary["income_cny"] == pytest.approx(720)
    assert summary["expense_cny"] == 0
    assert summary["net_cny"] == pytest.approx(720)
    dashboard = request_json(client, "GET", "/dashboard")
    assert dashboard["month"]["income_cny"] == pytest.approx(720)
    assert dashboard["recent_transactions"][0]["id"] == created["id"]


def test_recurring_month_end_clamping_idempotency_pause_and_resume(ledger):
    client, _, clock, _ = ledger
    clock[0] = date(2026, 1, 31)
    rule = request_json(client, "POST", "/recurring", {
        "type": "expense", "amount": 3000, "currency": "CNY",
        "category": "housing", "day_of_month": 31, "note": "月租",
    })
    first = request_json(client, "GET", "/transactions?source=recurring")
    assert [row["tx_date"] for row in first] == ["2026-01-31"]
    clock[0] = date(2026, 2, 28)
    second = request_json(client, "GET", "/transactions?source=recurring")
    assert {row["tx_date"] for row in second} == {"2026-01-31", "2026-02-28"}
    assert len(request_json(client, "GET", "/transactions?source=recurring")) == 2
    request_json(client, "PUT", f"/recurring/{rule['id']}", {"active": False})
    clock[0] = date(2026, 3, 31)
    assert len(request_json(client, "GET", "/transactions?source=recurring")) == 2
    clock[0] = date(2026, 4, 30)
    request_json(client, "PUT", f"/recurring/{rule['id']}", {"active": True})
    resumed = request_json(client, "GET", "/transactions?source=recurring")
    # The documented cursor-based resume policy backfills paused months.
    assert {row["tx_date"] for row in resumed} == {
        "2026-01-31", "2026-02-28", "2026-03-31", "2026-04-30",
    }
    assert len(resumed) == 4
    request_json(client, "DELETE", f"/recurring/{rule['id']}")
    assert len(request_json(client, "GET", "/transactions?source=recurring")) == 4


def test_budget_uses_month_and_cny_total_including_foreign_currency(ledger):
    client, _, _, _ = ledger
    request_json(client, "PUT", "/budgets", {"category": "food", "month": "2026-11", "amount_cny": 3000})
    transaction(client, amount=2500)
    transaction(client, amount=100, currency="USD")
    transaction(client, amount=10000, day="2026-10-18")
    budgets = request_json(client, "GET", "/budgets?month=2026-11")
    food = next(row for row in budgets if row["category"] == "food")
    assert food["budget_cny"] == 3000
    assert food["spent_cny"] == pytest.approx(3220)
    assert food["over_budget"] is True
    request_json(client, "PUT", "/budgets", {"category": "food", "month": "2026-11", "amount_cny": None})
    food = next(row for row in request_json(client, "GET", "/budgets?month=2026-11") if row["category"] == "food")
    assert food["budget_cny"] is None
    assert food["spent_cny"] == pytest.approx(3220)
    assert food["over_budget"] is False


def test_goal_two_currencies_and_contribution_delete(ledger):
    client, _, _, _ = ledger
    goal = request_json(client, "POST", "/goals", {
        "name": "应急基金", "target_amount": 10000, "currency": "CNY", "deadline": "2027-01-01",
    })
    request_json(client, "POST", f"/goals/{goal['id']}/contributions", {
        "amount": 5000, "currency": "CNY", "contributed_at": "2026-11-18",
    })
    usd = request_json(client, "POST", f"/goals/{goal['id']}/contributions", {
        "amount": 100, "currency": "USD", "contributed_at": "2026-11-18",
    })
    result = request_json(client, "GET", "/goals")[0]
    assert result["contributed_cny"] == pytest.approx(5720)
    assert result["remaining_cny"] == pytest.approx(4280)
    assert result["progress"] == pytest.approx(0.572)
    assert len(request_json(client, "GET", f"/goals/{goal['id']}/contributions")) == 2
    request_json(client, "DELETE", f"/contributions/{usd['id']}")
    assert request_json(client, "GET", "/goals")[0]["contributed_cny"] == 5000
    request_json(client, "DELETE", f"/goals/{goal['id']}")
    assert request_json(client, "GET", "/goals") == []


def test_assets_and_investments_share_one_same_day_networth_snapshot(ledger):
    client, _, _, _ = ledger
    assert request_json(client, "GET", "/networth/history") == []
    cash = request_json(client, "POST", "/assets", {
        "name": "人民币账户", "category": "checking", "currency": "CNY", "balance": 1000,
    })
    request_json(client, "PUT", f"/assets/{cash['id']}", {"balance": 1250})
    usd = request_json(client, "POST", "/assets", {
        "name": "美元账户", "category": "cash", "currency": "USD", "balance": 100,
    })
    holding = request_json(client, "POST", "/investments/holdings", {
        "symbol": "TEST", "name": "测试持仓", "asset_type": "stock", "currency": "USD",
        "quantity": 10, "avg_cost": 10, "current_price": 20,
    })
    request_json(client, "PUT", f"/investments/{holding['id']}", {"current_price": 25})
    assets = request_json(client, "GET", "/assets")
    assert len(assets["accounts"]) == 2
    assert assets["investment_portfolio_cny"] == pytest.approx(1800)
    assert assets["total_cny"] == pytest.approx(3770)
    assert sum(row["amount_cny"] for row in assets["by_category"]) == pytest.approx(3770)
    history = request_json(client, "GET", "/networth/history")
    assert len(history) == 1
    assert history[0]["date"] == "2026-11-18"
    assert history[0]["total_cny"] == pytest.approx(3770)
    assert request_json(client, "GET", "/dashboard")["net_worth"]["total_cny"] == pytest.approx(3770)
    request_json(client, "DELETE", f"/assets/{cash['id']}")
    request_json(client, "DELETE", f"/assets/{usd['id']}")
    request_json(client, "POST", "/investments/trades", {
        "holding_id": holding["id"], "action": "sell", "quantity": 10,
        "price": 25, "fee": 0, "trade_date": "2026-11-18",
    })
    assert request_json(client, "GET", "/networth/history")[0]["total_cny"] == 0
    assert len(request_json(client, "GET", "/networth/history")) == 1


def test_removing_last_asset_records_zero_after_real_history(ledger):
    client, _, _, _ = ledger
    asset = request_json(client, "POST", "/assets", {
        "name": "唯一账户", "category": "cash", "currency": "CNY", "balance": 100,
    })
    request_json(client, "DELETE", f"/assets/{asset['id']}")
    history = request_json(client, "GET", "/networth/history")
    assert len(history) == 1
    assert history[0]["total_cny"] == 0
    assert request_json(client, "GET", "/assets")["total_cny"] == 0


def test_dream_purchase_overrides_price_once_and_creates_shopping_expense(ledger):
    client, _, _, _ = ledger
    dream = request_json(client, "POST", "/dreams", {
        "name": "机械键盘", "price": 100, "currency": "USD", "priority": "high",
    })
    request_json(client, "POST", f"/dreams/{dream['id']}/purchase", {"amount": 95, "currency": "USD"})
    duplicate = client.post(f"/api/dreams/{dream['id']}/purchase", json={})
    assert duplicate.status_code in (200, 409), duplicate.text
    rows = request_json(client, "GET", "/transactions?source=dream")
    assert len(rows) == 1
    assert rows[0]["amount"] == 95
    assert rows[0]["amount_cny"] == pytest.approx(684)
    assert rows[0]["type"] == "expense"
    assert rows[0]["category"] == "shopping"
    assert rows[0]["dream_item_id"] == dream["id"]
    assert request_json(client, "GET", "/dreams?status=pending") == []
    assert request_json(client, "GET", "/dreams?status=purchased")[0]["purchased_at"] == "2026-11-18"
    request_json(client, "PUT", f"/dreams/{dream['id']}", {"status": "pending"})
    assert len(request_json(client, "GET", "/transactions?source=dream")) == 1
    assert request_json(client, "GET", "/dreams?status=pending")[0]["purchased_at"] is None


def test_dream_status_cannot_bypass_purchase_accounting(ledger):
    client, _, _, _ = ledger
    dream = request_json(client, "POST", "/dreams", {"name": "相机", "price": 1000, "currency": "CNY"})
    response = client.put(f"/api/dreams/{dream['id']}", json={"status": "purchased"})
    assert response.status_code in (400, 409, 422), response.text
    assert request_json(client, "GET", "/dreams")[0]["status"] == "pending"
    assert request_json(client, "GET", "/transactions?source=dream") == []


def test_concurrent_dream_purchase_never_creates_duplicate_expenses(ledger):
    client, _, _, _ = ledger
    dream = request_json(client, "POST", "/dreams", {"name": "耳机", "price": 300, "currency": "CNY"})
    with ThreadPoolExecutor(max_workers=4) as pool:
        responses = list(pool.map(lambda _: client.post(f"/api/dreams/{dream['id']}/purchase", json={}), range(4)))
    assert all(response.status_code in (200, 201, 409) for response in responses), [r.text for r in responses]
    rows = request_json(client, "GET", "/transactions?source=dream")
    assert len(rows) == 1
    assert rows[0]["amount_cny"] == 300


def test_investment_fees_oversell_realized_profit_and_new_cost_after_liquidation(ledger):
    client, _, _, _ = ledger
    holding = request_json(client, "POST", "/investments/holdings", {
        "symbol": "ETFTEST", "name": "测试基金", "asset_type": "etf",
        "currency": "CNY", "current_price": 130,
    })

    def trade(action, quantity, price, fee):
        return request_json(client, "POST", "/investments/trades", {
            "holding_id": holding["id"], "action": action, "quantity": quantity,
            "price": price, "fee": fee, "trade_date": "2026-11-18",
        })

    trade("buy", 10, 100, 10)
    trade("buy", 10, 120, 10)
    current = request_json(client, "GET", "/investments/holdings")[0]
    assert current["quantity"] == 20
    assert current["avg_cost"] == pytest.approx(111)
    assert current["pnl"] == pytest.approx(380)
    trade("sell", 5, 130, 5)
    trades = request_json(client, "GET", f"/investments/trades?holding_id={holding['id']}")
    assert sum(row["realized_pnl"] for row in trades) == pytest.approx(90)
    oversell = client.post("/api/investments/trades", json={
        "holding_id": holding["id"], "action": "sell", "quantity": 16,
        "price": 130, "fee": 0, "trade_date": "2026-11-18",
    })
    assert oversell.status_code in (400, 409, 422), oversell.text
    assert request_json(client, "GET", "/investments/holdings")[0]["quantity"] == 15
    assert len(request_json(client, "GET", "/investments/trades")) == 3
    trade("sell", 15, 110, 5)
    empty = request_json(client, "GET", "/investments/holdings")[0]
    assert empty["quantity"] == 0
    assert empty["avg_cost"] == 0
    assert empty["pnl"] == 0
    assert request_json(client, "GET", "/investments/summary")["realized_pnl_all_cny"] == pytest.approx(70)
    trade("buy", 2, 50, 2)
    request_json(client, "PUT", f"/investments/{holding['id']}", {"current_price": 60})
    restarted = request_json(client, "GET", "/investments/holdings")[0]
    assert restarted["avg_cost"] == pytest.approx(51)
    assert restarted["market_value"] == pytest.approx(120)
    assert restarted["pnl"] == pytest.approx(18)


def test_fractional_quantity_liquidation_has_no_residual(ledger):
    client, _, _, _ = ledger
    holding = request_json(client, "POST", "/investments/holdings", {
        "symbol": "FRACTION", "name": "小数份额", "asset_type": "fund", "currency": "CNY", "current_price": 10,
    })
    for action, quantity in [("buy", 0.1), ("buy", 0.2), ("sell", 0.3)]:
        request_json(client, "POST", "/investments/trades", {
            "holding_id": holding["id"], "action": action, "quantity": quantity,
            "price": 10, "fee": 0, "trade_date": "2026-11-18",
        })
    current = request_json(client, "GET", "/investments/holdings")[0]
    assert current["quantity"] == 0
    assert current["avg_cost"] == 0


def test_concurrent_sales_cannot_oversell_a_holding(ledger):
    client, _, _, _ = ledger
    holding = request_json(client, "POST", "/investments/holdings", {
        "symbol": "RACE", "name": "并发卖出", "asset_type": "stock", "currency": "CNY",
        "quantity": 10, "avg_cost": 10, "current_price": 12,
    })
    payload = {"holding_id": holding["id"], "action": "sell", "quantity": 8,
               "price": 12, "fee": 1, "trade_date": "2026-11-18"}
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda _: client.post("/api/investments/trades", json=payload), range(2)))
    assert sum(200 <= response.status_code < 300 for response in responses) == 1
    assert all(response.status_code in (200, 201, 400, 409, 422) for response in responses), [r.text for r in responses]
    assert request_json(client, "GET", "/investments/holdings")[0]["quantity"] == 2
    trades = request_json(client, "GET", "/investments/trades")
    sales = [row for row in trades if row["action"] == "sell"]
    assert len(sales) == 1
    assert sales[0]["realized_pnl"] == pytest.approx(15)


def test_failed_first_request_does_not_poison_rate_refresh_for_valid_write(ledger):
    client, _, _, _ = ledger
    missing = client.put("/api/assets/999999", json={"balance": 100})
    assert missing.status_code == 404, missing.text
    created = transaction(client, kind="income", amount=100, currency="USD", category="salary")
    assert created["amount_cny"] == pytest.approx(720)


def test_stale_rates_survive_provider_failure_and_database_reopen(ledger):
    from app.main import create_app
    from app.models import ExchangeRate

    client, app, clock, database = ledger
    transaction(client, kind="income", amount=100, currency="USD", category="salary")
    with app.state.session_factory() as session:
        for rate in session.query(ExchangeRate).all():
            rate.fetched_at = datetime.now(timezone.utc) - timedelta(days=3)
        session.commit()
    reopened = create_app(db_path=str(database), today_provider=lambda: clock[0], rates_fetcher=offline_rates)
    with TestClient(reopened) as other:
        dashboard = request_json(other, "GET", "/dashboard")
        assert dashboard["month"]["income_cny"] == pytest.approx(720)
        assert dashboard["rates_stale"] is True
        assert dashboard["rates_updated_at"] is not None
        assert len(request_json(other, "GET", "/transactions")) == 1
    reopened.state.engine.dispose()


def test_empty_offline_database_works_for_cny_and_rolls_back_missing_fx(tmp_path):
    from app.main import create_app

    app = create_app(db_path=str(tmp_path / "offline.sqlite3"), today_provider=lambda: date(2026, 11, 18), rates_fetcher=offline_rates)
    with TestClient(app) as client:
        dashboard = request_json(client, "GET", "/dashboard")
        assert dashboard["net_worth"]["total_cny"] == 0
        assert dashboard["month"]["income_cny"] == 0
        assert dashboard["rates_stale"] is True
        assert request_json(client, "GET", "/networth/history") == []
        for path, payload in [
            ("/transactions", {"type": "income", "amount": 100, "currency": "USD", "category": "salary", "tx_date": "2026-11-18"}),
            ("/assets", {"name": "未知汇率账户", "category": "cash", "currency": "USD", "balance": 100}),
        ]:
            response = client.post("/api" + path, json=payload)
            assert response.status_code == 409, response.text
        assert request_json(client, "GET", "/transactions") == []
        assert request_json(client, "GET", "/assets")["accounts"] == []
        transaction(client, amount=50)
        assert request_json(client, "GET", "/dashboard")["month"]["expense_cny"] == 50
    app.state.engine.dispose()


@pytest.mark.parametrize("changes", [
    {"amount": -1}, {"amount": 0}, {"amount": "NaN"}, {"amount": "Infinity"},
    {"category": "salary"}, {"currency": "FAKE"}, {"tx_date": "2026-02-30"},
])
def test_invalid_transaction_never_reaches_storage(ledger, changes):
    client, _, _, _ = ledger
    payload = {"type": "expense", "amount": 100, "currency": "CNY", "category": "food", "tx_date": "2026-11-18"}
    payload.update(changes)
    response = client.post("/api/transactions", json=payload)
    assert response.status_code == 422, response.text
    assert request_json(client, "GET", "/transactions") == []
