from datetime import datetime, timezone

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Transaction(Base):
    __tablename__ = 'transactions'
    __table_args__ = (UniqueConstraint('recurring_rule_id', 'tx_date'), UniqueConstraint('dream_item_id'))
    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[str] = mapped_column(String(12))
    amount: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(3))
    tx_date: Mapped[object] = mapped_column(Date, index=True)
    category: Mapped[str] = mapped_column(String(32))
    note: Mapped[str] = mapped_column(Text, default='')
    source: Mapped[str] = mapped_column(String(16), default='manual')
    recurring_rule_id: Mapped[int | None] = mapped_column(ForeignKey('recurring_rules.id', ondelete='SET NULL'))
    dream_item_id: Mapped[int | None] = mapped_column(ForeignKey('dream_items.id', ondelete='SET NULL'))
    created_at: Mapped[object] = mapped_column(DateTime, default=utcnow)


class RecurringRule(Base):
    __tablename__ = 'recurring_rules'
    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[str] = mapped_column(String(12))
    amount: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(3))
    category: Mapped[str] = mapped_column(String(32))
    note: Mapped[str] = mapped_column(Text, default='')
    day_of_month: Mapped[int] = mapped_column(Integer)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_generated: Mapped[object | None] = mapped_column(Date, nullable=True)
    created_date: Mapped[object] = mapped_column(Date)


class Budget(Base):
    __tablename__ = 'budgets'
    __table_args__ = (UniqueConstraint('category', 'month'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    category: Mapped[str] = mapped_column(String(32))
    month: Mapped[str] = mapped_column(String(7))
    amount_cny: Mapped[float] = mapped_column(Float)


class SavingsGoal(Base):
    __tablename__ = 'savings_goals'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    target_amount: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(3))
    deadline: Mapped[object | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default='active')


class SavingsContribution(Base):
    __tablename__ = 'savings_contributions'
    id: Mapped[int] = mapped_column(primary_key=True)
    goal_id: Mapped[int] = mapped_column(ForeignKey('savings_goals.id', ondelete='CASCADE'), index=True)
    amount: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(3))
    contributed_at: Mapped[object] = mapped_column(Date)
    note: Mapped[str] = mapped_column(Text, default='')


class AssetAccount(Base):
    __tablename__ = 'asset_accounts'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(32))
    currency: Mapped[str] = mapped_column(String(3))
    balance: Mapped[float] = mapped_column(Float)
    updated_at: Mapped[object] = mapped_column(DateTime, default=utcnow)


class NetWorthSnapshot(Base):
    __tablename__ = 'net_worth_snapshots'
    id: Mapped[int] = mapped_column(primary_key=True)
    snap_date: Mapped[object] = mapped_column(Date, unique=True, index=True)
    total_cny: Mapped[float] = mapped_column(Float)
    breakdown_json: Mapped[str] = mapped_column(Text)


class DreamItem(Base):
    __tablename__ = 'dream_items'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    price: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(3))
    priority: Mapped[str] = mapped_column(String(12), default='medium')
    url: Mapped[str] = mapped_column(Text, default='')
    note: Mapped[str] = mapped_column(Text, default='')
    status: Mapped[str] = mapped_column(String(12), default='pending')
    purchased_at: Mapped[object | None] = mapped_column(Date, nullable=True)


class InvestmentHolding(Base):
    __tablename__ = 'investment_holdings'
    id: Mapped[int] = mapped_column(primary_key=True)
    symbol: Mapped[str] = mapped_column(String(40))
    name: Mapped[str] = mapped_column(String(200))
    asset_type: Mapped[str] = mapped_column(String(16))
    currency: Mapped[str] = mapped_column(String(3))
    quantity: Mapped[float] = mapped_column(Float, default=0)
    avg_cost: Mapped[float] = mapped_column(Float, default=0)
    current_price: Mapped[float] = mapped_column(Float, default=0)
    updated_at: Mapped[object] = mapped_column(DateTime, default=utcnow)


class InvestmentTrade(Base):
    __tablename__ = 'investment_trades'
    id: Mapped[int] = mapped_column(primary_key=True)
    holding_id: Mapped[int | None] = mapped_column(ForeignKey('investment_holdings.id', ondelete='SET NULL'), index=True)
    symbol: Mapped[str] = mapped_column(String(40))
    name: Mapped[str] = mapped_column(String(200))
    currency: Mapped[str] = mapped_column(String(3))
    action: Mapped[str] = mapped_column(String(8))
    quantity: Mapped[float] = mapped_column(Float)
    price: Mapped[float] = mapped_column(Float)
    fee: Mapped[float] = mapped_column(Float, default=0)
    trade_date: Mapped[object] = mapped_column(Date, index=True)
    realized_pnl: Mapped[float] = mapped_column(Float, default=0)
    note: Mapped[str] = mapped_column(Text, default='')


class ExchangeRate(Base):
    __tablename__ = 'exchange_rates'
    id: Mapped[int] = mapped_column(primary_key=True)
    currency: Mapped[str] = mapped_column(String(3), unique=True)
    rate: Mapped[float] = mapped_column(Float)
    fetched_at: Mapped[object] = mapped_column(DateTime)
    reference_date: Mapped[object | None] = mapped_column(Date, nullable=True)
