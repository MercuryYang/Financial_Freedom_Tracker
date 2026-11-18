from collections import defaultdict
from datetime import date, datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select

from ..constants import EXPENSE_CATEGORIES
from ..models import AssetAccount, Budget, DreamItem, InvestmentHolding, InvestmentTrade, NetWorthSnapshot, SavingsContribution, SavingsGoal, Transaction
from .money import decimal, rounded, to_cny, total


def data(row):
    result = {column.name: getattr(row, column.name) for column in row.__table__.columns}
    for key, value in result.items():
        if isinstance(value, datetime) and value.tzinfo is None:
            result[key] = value.replace(tzinfo=timezone.utc)
    return result


def transaction_data(db, row):
    return {**data(row), 'amount_cny': to_cny(db, row.amount, row.currency)}


def holding_data(db, row):
    market = decimal(row.quantity) * decimal(row.current_price)
    cost = decimal(row.quantity) * decimal(row.avg_cost)
    return {
        **data(row), 'market_value': rounded(market), 'cost': rounded(cost), 'pnl': rounded(market - cost),
        'pnl_rate': float((decimal(row.current_price) - decimal(row.avg_cost)) / decimal(row.avg_cost)) if row.avg_cost else 0,
        'market_value_cny': to_cny(db, market, row.currency), 'cost_cny': to_cny(db, cost, row.currency),
        'pnl_cny': to_cny(db, market - cost, row.currency),
    }


def investment_summary(db):
    holdings = [holding_data(db, row) for row in db.scalars(select(InvestmentHolding))]
    market = total(row['market_value_cny'] for row in holdings)
    cost = total(row['cost_cny'] for row in holdings)
    realized = total(to_cny(db, row.realized_pnl, row.currency) for row in db.scalars(select(InvestmentTrade)))
    return {'market_value_cny': market, 'total_cost_cny': cost, 'cost_cny': cost,
            'unrealized_pnl_cny': rounded(decimal(market) - decimal(cost)),
            'realized_pnl_all_cny': realized, 'realized_pnl_cny': realized}


def assets_data(db):
    accounts = [{**data(row), 'balance_cny': to_cny(db, row.balance, row.currency)} for row in db.scalars(select(AssetAccount).order_by(AssetAccount.id))]
    categories = defaultdict(list)
    for row in accounts:
        categories[row['category']].append(row['balance_cny'])
    portfolio = investment_summary(db)['market_value_cny']
    if db.scalar(select(InvestmentHolding.id).limit(1)) is not None:
        categories['investment_portfolio'].append(portfolio)
    breakdown = [{'category': category, 'amount_cny': total(values)} for category, values in categories.items()]
    return {'accounts': accounts, 'total_cny': total(row['amount_cny'] for row in breakdown),
            'by_category': breakdown, 'investment_portfolio_cny': portfolio}


def goal_data(db, row):
    target = to_cny(db, row.target_amount, row.currency)
    contributed = total(to_cny(db, c.amount, c.currency) for c in db.scalars(select(SavingsContribution).where(SavingsContribution.goal_id == row.id)))
    return {**data(row), 'target_cny': target, 'contributed_cny': contributed,
            'progress': min(contributed / target, 1) if target else 0,
            'remaining_cny': max(rounded(decimal(target) - decimal(contributed)), 0)}


def dream_data(db, row):
    return {**data(row), 'price_cny': to_cny(db, row.price, row.currency)}


def month_range(month):
    try:
        year, number = map(int, month.split('-'))
        start = date(year, number, 1)
        end = date(year + (number == 12), 1 if number == 12 else number + 1, 1)
        if month != start.strftime('%Y-%m'):
            raise ValueError()
        return start, end
    except (ValueError, OverflowError):
        raise HTTPException(422, '月份格式应为 YYYY-MM')


def month_transactions(db, month):
    start, end = month_range(month)
    return list(db.scalars(select(Transaction).where(Transaction.tx_date >= start, Transaction.tx_date < end).order_by(Transaction.tx_date.desc(), Transaction.id.desc())))


def transaction_summary(db, month):
    records = month_transactions(db, month)
    income, expense = [], []
    categories, days = defaultdict(list), defaultdict(lambda: {'income': [], 'expense': []})
    for row in records:
        amount = to_cny(db, row.amount, row.currency)
        (income if row.type == 'income' else expense).append(amount)
        if row.type == 'expense':
            categories[row.category].append(amount)
        days[row.tx_date.isoformat()][row.type].append(amount)
    income, expense = total(income), total(expense)
    return {'income_cny': income, 'expense_cny': expense, 'net_cny': rounded(decimal(income) - decimal(expense)),
            'by_category': [{'category': k, 'amount_cny': total(v)} for k, v in categories.items()],
            'by_day': [{'date': key, 'income_cny': total(value['income']), 'expense_cny': total(value['expense'])} for key, value in sorted(days.items())]}


def budgets_data(db, month):
    summary = transaction_summary(db, month)
    spent = {r['category']: r['amount_cny'] for r in summary['by_category']}
    budgets = {r.category: r.amount_cny for r in db.scalars(select(Budget).where(Budget.month == month))}
    return [{'category': category, 'month': month, 'budget_cny': budgets.get(category),
             'spent_cny': spent.get(category, 0),
             'over_budget': category in budgets and spent.get(category, 0) > budgets[category]}
            for category in EXPENSE_CATEGORIES]


def networth_history(db, limit=90):
    rows = list(db.scalars(select(NetWorthSnapshot).order_by(NetWorthSnapshot.snap_date.desc()).limit(limit)))
    return [{'date': r.snap_date, 'total_cny': r.total_cny} for r in reversed(rows)]
