from typing import Annotated, Literal

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, Response
from pydantic import ValidationError
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from .. import models as m, schemas as s
from ..services.money import decimal, rounded, to_cny
from ..services.rates import currency_payload, ensure_rates_fresh, rate_status
from ..services.recurring import ensure_recurring_due
from ..services.reporting import (assets_data, budgets_data, data, dream_data, goal_data,
                                  holding_data, investment_summary, month_range,
                                  networth_history, transaction_data, transaction_summary)
from ..services.snapshots import take_snapshot

router = APIRouter(prefix='/api')


def get_db(request: Request):
    with request.app.state.session_factory() as db:
        # Acquire the writer lock before reading any state to make read/modify/
        # write operations (recurring, purchases, trades) atomic across requests.
        db.execute(text('BEGIN IMMEDIATE'))
        try:
            if request.url.path != '/api/rates/refresh':
                ensure_rates_fresh(db, request.app.state)
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise


DB = Annotated[Session, Depends(get_db, scope='function')]


def today(request):
    return request.app.state.today_provider()


def get_or_404(db, model, identity):
    row = db.get(model, identity)
    if row is None:
        raise HTTPException(404, '记录不存在或已删除')
    return row


def update_validated(row, patch, schema):
    unknown = set(patch) - set(schema.model_fields)
    if unknown:
        raise HTTPException(422, '不支持修改字段：' + ', '.join(sorted(unknown)))
    merged = {key: getattr(row, key) for key in schema.model_fields}
    merged.update(patch)
    try:
        validated = schema.model_validate(merged)
    except ValidationError as exc:
        errors = '; '.join(f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in exc.errors())
        raise HTTPException(422, errors) from exc
    for key, value in validated.model_dump().items():
        setattr(row, key, value)
    return row


def recurring_data(db, row):
    count = db.scalar(select(func.count()).select_from(m.Transaction).where(m.Transaction.recurring_rule_id == row.id))
    return {**data(row), 'amount_cny': to_cny(db, row.amount, row.currency), 'generated_count': count}


@router.get('/health')
def health():
    return {'status': 'ok'}


@router.get('/currencies')
def currencies(db: DB):
    return currency_payload(db)


@router.post('/rates/refresh')
def refresh_rates(request: Request, db: DB):
    success = ensure_rates_fresh(db, request.app.state, force=True)
    payload = currency_payload(db)
    return {**payload, 'refreshed': success,
            'message': '汇率已更新' if success else '汇率服务暂时不可用，已有缓存继续使用'}


@router.get('/transactions/summary')
def transactions_summary(request: Request, db: DB, month: str | None = None):
    ensure_recurring_due(db, today(request))
    return transaction_summary(db, month or today(request).strftime('%Y-%m'))


@router.get('/transactions')
def transactions(request: Request, db: DB, type: Literal['income', 'expense'] | None = None,
                 month: str | None = None, category: str | None = None,
                 source: Literal['manual', 'recurring', 'dream'] | None = None,
                 limit: int = Query(500, ge=1, le=10000)):
    ensure_recurring_due(db, today(request))
    query = select(m.Transaction)
    if month:
        start, end = month_range(month)
        query = query.where(m.Transaction.tx_date >= start, m.Transaction.tx_date < end)
    for field, value in [('type', type), ('category', category), ('source', source)]:
        if value:
            query = query.where(getattr(m.Transaction, field) == value)
    rows = db.scalars(query.order_by(m.Transaction.tx_date.desc(), m.Transaction.id.desc()).limit(limit))
    return [transaction_data(db, row) for row in rows]


@router.post('/transactions', status_code=201)
def create_transaction(payload: s.TransactionInput, db: DB):
    to_cny(db, payload.amount, payload.currency)
    row = m.Transaction(**payload.model_dump(), source='manual')
    db.add(row)
    db.flush()
    return transaction_data(db, row)


@router.put('/transactions/{identity}')
def update_transaction(identity: int, payload: dict, db: DB):
    row = update_validated(get_or_404(db, m.Transaction, identity), payload, s.TransactionInput)
    return transaction_data(db, row)


@router.delete('/transactions/{identity}', status_code=204)
def delete_transaction(identity: int, db: DB):
    db.delete(get_or_404(db, m.Transaction, identity))
    return Response(status_code=204)


@router.get('/recurring')
def recurring(db: DB):
    return [recurring_data(db, row) for row in db.scalars(select(m.RecurringRule).order_by(m.RecurringRule.id.desc()))]


@router.post('/recurring', status_code=201)
def create_recurring(payload: s.RecurringInput, request: Request, db: DB):
    to_cny(db, payload.amount, payload.currency)
    row = m.RecurringRule(**payload.model_dump(), created_date=today(request))
    db.add(row)
    db.flush()
    return recurring_data(db, row)


@router.put('/recurring/{identity}')
def update_recurring(identity: int, payload: dict, db: DB):
    row = update_validated(get_or_404(db, m.RecurringRule, identity), payload, s.RecurringInput)
    return recurring_data(db, row)


@router.delete('/recurring/{identity}', status_code=204)
def delete_recurring(identity: int, db: DB):
    db.delete(get_or_404(db, m.RecurringRule, identity))
    return Response(status_code=204)


@router.get('/budgets/months')
def budget_months(db: DB):
    return list(db.scalars(select(m.Budget.month).distinct().order_by(m.Budget.month.desc())))


@router.get('/budgets')
def budgets(request: Request, db: DB, month: str | None = None):
    ensure_recurring_due(db, today(request))
    return budgets_data(db, month or today(request).strftime('%Y-%m'))


@router.put('/budgets')
def upsert_budget(payload: s.BudgetInput, db: DB):
    month_range(payload.month)
    row = db.scalar(select(m.Budget).where(m.Budget.category == payload.category, m.Budget.month == payload.month))
    if payload.amount_cny is None:
        if row:
            db.delete(row)
    elif row:
        row.amount_cny = payload.amount_cny
    else:
        db.add(m.Budget(**payload.model_dump()))
    db.flush()
    return next(r for r in budgets_data(db, payload.month) if r['category'] == payload.category)


@router.get('/goals')
def goals(db: DB):
    return [goal_data(db, row) for row in db.scalars(select(m.SavingsGoal).order_by(m.SavingsGoal.id.desc()))]


@router.post('/goals', status_code=201)
def create_goal(payload: s.GoalInput, db: DB):
    to_cny(db, payload.target_amount, payload.currency)
    row = m.SavingsGoal(**payload.model_dump())
    db.add(row)
    db.flush()
    return goal_data(db, row)


@router.put('/goals/{identity}')
def update_goal(identity: int, payload: dict, db: DB):
    return goal_data(db, update_validated(get_or_404(db, m.SavingsGoal, identity), payload, s.GoalInput))


@router.delete('/goals/{identity}', status_code=204)
def delete_goal(identity: int, db: DB):
    db.delete(get_or_404(db, m.SavingsGoal, identity))
    return Response(status_code=204)


@router.get('/goals/{identity}/contributions')
def contributions(identity: int, db: DB):
    get_or_404(db, m.SavingsGoal, identity)
    rows = db.scalars(select(m.SavingsContribution).where(m.SavingsContribution.goal_id == identity).order_by(m.SavingsContribution.contributed_at.desc(), m.SavingsContribution.id.desc()))
    return [{**data(row), 'amount_cny': to_cny(db, row.amount, row.currency)} for row in rows]


@router.post('/goals/{identity}/contributions', status_code=201)
def create_contribution(identity: int, payload: s.ContributionInput, db: DB):
    get_or_404(db, m.SavingsGoal, identity)
    to_cny(db, payload.amount, payload.currency)
    row = m.SavingsContribution(**payload.model_dump(), goal_id=identity)
    db.add(row)
    db.flush()
    return {**data(row), 'amount_cny': to_cny(db, row.amount, row.currency)}


@router.delete('/contributions/{identity}', status_code=204)
def delete_contribution(identity: int, db: DB):
    db.delete(get_or_404(db, m.SavingsContribution, identity))
    return Response(status_code=204)


@router.get('/assets')
def assets(db: DB):
    return assets_data(db)


@router.post('/assets', status_code=201)
def create_asset(payload: s.AssetInput, request: Request, db: DB):
    row = m.AssetAccount(**payload.model_dump())
    db.add(row)
    take_snapshot(db, today(request))
    return {**data(row), 'balance_cny': to_cny(db, row.balance, row.currency)}


@router.put('/assets/{identity}')
def update_asset(identity: int, payload: dict, request: Request, db: DB):
    row = update_validated(get_or_404(db, m.AssetAccount, identity), payload, s.AssetInput)
    row.updated_at = m.utcnow()
    take_snapshot(db, today(request))
    return {**data(row), 'balance_cny': to_cny(db, row.balance, row.currency)}


@router.delete('/assets/{identity}', status_code=204)
def delete_asset(identity: int, request: Request, db: DB):
    db.delete(get_or_404(db, m.AssetAccount, identity))
    take_snapshot(db, today(request))
    return Response(status_code=204)


@router.get('/networth/history')
def history(db: DB, limit: int = Query(90, ge=1, le=10000)):
    return networth_history(db, limit)


@router.get('/dreams')
def dreams(db: DB, status: Literal['pending', 'purchased'] | None = None):
    query = select(m.DreamItem)
    if status:
        query = query.where(m.DreamItem.status == status)
    rows = list(db.scalars(query))
    rows.sort(key=lambda row: ({'high': 0, 'medium': 1, 'low': 2}[row.priority], -row.id))
    return [dream_data(db, row) for row in rows]


@router.post('/dreams', status_code=201)
def create_dream(payload: s.DreamInput, db: DB):
    if payload.status != 'pending':
        raise HTTPException(422, '新心愿应为待购，请使用购买操作记录支出')
    to_cny(db, payload.price, payload.currency)
    row = m.DreamItem(**payload.model_dump())
    db.add(row)
    db.flush()
    return dream_data(db, row)


@router.put('/dreams/{identity}')
def update_dream(identity: int, payload: dict, db: DB):
    row = get_or_404(db, m.DreamItem, identity)
    if payload.get('status') == 'purchased' and row.status != 'purchased':
        raise HTTPException(422, '请使用购买操作，自动生成对应支出')
    update_validated(row, payload, s.DreamInput)
    if row.status == 'pending':
        row.purchased_at = None
    return dream_data(db, row)


@router.delete('/dreams/{identity}', status_code=204)
def delete_dream(identity: int, db: DB):
    db.delete(get_or_404(db, m.DreamItem, identity))
    return Response(status_code=204)


@router.post('/dreams/{identity}/purchase')
def purchase(identity: int, request: Request, db: DB, payload: s.PurchaseInput = Body(default_factory=s.PurchaseInput)):
    row = get_or_404(db, m.DreamItem, identity)
    if row.status == 'purchased' or db.scalar(select(m.Transaction.id).where(m.Transaction.dream_item_id == identity)):
        raise HTTPException(409, '该心愿已记录购买支出，请勿重复购买')
    amount = payload.amount if payload.amount is not None else row.price
    currency = payload.currency or row.currency
    to_cny(db, amount, currency)
    transaction = m.Transaction(type='expense', amount=amount, currency=currency, tx_date=today(request),
                                category='shopping', note=f'Dream 购入: {row.name}', source='dream', dream_item_id=row.id)
    db.add(transaction)
    row.status = 'purchased'
    row.purchased_at = today(request)
    db.flush()
    return {**dream_data(db, row), 'transaction': transaction_data(db, transaction)}


@router.get('/investments/holdings')
def holdings(db: DB):
    rows = [holding_data(db, row) for row in db.scalars(select(m.InvestmentHolding))]
    return sorted(rows, key=lambda row: row['market_value_cny'], reverse=True)


@router.post('/investments/holdings', status_code=201)
def create_holding(payload: s.HoldingInput, request: Request, db: DB):
    row = m.InvestmentHolding(**payload.model_dump())
    if row.quantity == 0:
        row.avg_cost = 0
    db.add(row)
    db.flush()
    if row.quantity:
        db.add(m.InvestmentTrade(holding_id=row.id, symbol=row.symbol, name=row.name, currency=row.currency,
                                action='buy', quantity=row.quantity, price=row.avg_cost, fee=0,
                                trade_date=today(request), realized_pnl=0, note='初始建仓'))
    take_snapshot(db, today(request))
    return holding_data(db, row)


@router.get('/investments/trades')
def trades(db: DB, holding_id: int | None = None):
    query = select(m.InvestmentTrade)
    if holding_id is not None:
        query = query.where(m.InvestmentTrade.holding_id == holding_id)
    return [{**data(row), 'amount': rounded(decimal(row.quantity) * decimal(row.price)),
             'amount_cny': to_cny(db, decimal(row.quantity) * decimal(row.price), row.currency),
             'realized_pnl_cny': to_cny(db, row.realized_pnl, row.currency)}
            for row in db.scalars(query.order_by(m.InvestmentTrade.trade_date.desc(), m.InvestmentTrade.id.desc()))]


@router.post('/investments/trades', status_code=201)
def create_trade(payload: s.TradeInput, request: Request, db: DB):
    holding = get_or_404(db, m.InvestmentHolding, payload.holding_id)
    quantity, cost = decimal(holding.quantity), decimal(holding.avg_cost)
    q, price, fee = decimal(payload.quantity), decimal(payload.price), decimal(payload.fee)
    if payload.action == 'buy':
        new_quantity = quantity + q
        holding.avg_cost = float((quantity * cost + q * price + fee) / new_quantity)
        holding.quantity = float(new_quantity)
        realized = 0
    else:
        if q > quantity:
            raise HTTPException(409, '卖出数量不能超过当前持仓')
        realized = rounded((price - cost) * q - fee)
        holding.quantity = float(quantity - q)
        if holding.quantity == 0:
            holding.avg_cost = 0
    holding.updated_at = m.utcnow()
    trade = m.InvestmentTrade(**payload.model_dump(), symbol=holding.symbol, name=holding.name,
                              currency=holding.currency, realized_pnl=realized)
    db.add(trade)
    take_snapshot(db, today(request))
    return {**data(trade), 'realized_pnl_cny': to_cny(db, realized, holding.currency), 'holding': holding_data(db, holding)}


@router.get('/investments/summary')
def investments_summary(db: DB):
    return investment_summary(db)


@router.put('/investments/{identity}')
def update_holding(identity: int, payload: s.HoldingUpdate, request: Request, db: DB):
    row = get_or_404(db, m.InvestmentHolding, identity)
    patch = payload.model_dump(exclude_unset=True)
    if any(value is None for value in patch.values()):
        raise HTTPException(422, '名称和现价不能为空')
    for key, value in patch.items():
        setattr(row, key, value)
    row.updated_at = m.utcnow()
    take_snapshot(db, today(request))
    return holding_data(db, row)


@router.delete('/investments/{identity}', status_code=204)
def delete_holding(identity: int, request: Request, db: DB, force: bool = False):
    row = get_or_404(db, m.InvestmentHolding, identity)
    if row.quantity and not force:
        raise HTTPException(409, '持仓尚未清空；请先记录卖出，或明确强制删除')
    db.delete(row)
    take_snapshot(db, today(request))
    return Response(status_code=204)


@router.get('/dashboard')
def dashboard(request: Request, db: DB):
    current = today(request)
    ensure_recurring_due(db, current)
    assets = assets_data(db)
    return {
        'net_worth': {'total_cny': assets['total_cny'], 'trend': networth_history(db)},
        'month': transaction_summary(db, current.strftime('%Y-%m')),
        'goals': [goal_data(db, row) for row in db.scalars(select(m.SavingsGoal).where(m.SavingsGoal.status == 'active').order_by(m.SavingsGoal.id.desc()))],
        'budgets': budgets_data(db, current.strftime('%Y-%m')),
        'investments': investment_summary(db),
        'recent_transactions': [transaction_data(db, row) for row in db.scalars(select(m.Transaction).order_by(m.Transaction.tx_date.desc(), m.Transaction.id.desc()).limit(10))],
        **rate_status(db),
    }
