from datetime import date
from typing import Annotated, Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .constants import INCOME_CATEGORIES, EXPENSE_CATEGORIES

Currency = Literal['CNY', 'USD']
Positive = Annotated[float, Field(gt=0, le=1e15, allow_inf_nan=False)]
NonNegative = Annotated[float, Field(ge=0, le=1e15, allow_inf_nan=False)]
Name = Annotated[str, Field(min_length=1, max_length=200)]
Note = Annotated[str, Field(max_length=2000)]
Month = Annotated[str, Field(pattern=r'^\d{4}-(0[1-9]|1[0-2])$')]


class Input(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True, allow_inf_nan=False)


class TransactionInput(Input):
    type: Literal['income', 'expense']
    amount: Positive
    currency: Currency = 'CNY'
    tx_date: date
    category: str
    note: Note = ''

    @model_validator(mode='after')
    def valid_category(self):
        choices = INCOME_CATEGORIES if self.type == 'income' else EXPENSE_CATEGORIES
        if self.category not in choices:
            raise ValueError('分类与收支类型不匹配')
        return self


class RecurringInput(Input):
    type: Literal['income', 'expense']
    amount: Positive
    currency: Currency = 'CNY'
    category: str
    day_of_month: Annotated[int, Field(ge=1, le=31)]
    note: Note = ''
    active: bool = True

    @model_validator(mode='after')
    def valid_category(self):
        choices = INCOME_CATEGORIES if self.type == 'income' else EXPENSE_CATEGORIES
        if self.category not in choices:
            raise ValueError('分类与收支类型不匹配')
        return self


class BudgetInput(Input):
    category: Literal['food', 'housing', 'transport', 'shopping', 'entertainment', 'medical', 'education', 'other']
    month: Month
    amount_cny: NonNegative | None


class GoalInput(Input):
    name: Name
    target_amount: Positive
    currency: Currency = 'CNY'
    deadline: date | None = None
    status: Literal['active', 'done', 'abandoned'] = 'active'


class ContributionInput(Input):
    amount: Positive
    currency: Currency = 'CNY'
    contributed_at: date
    note: Note = ''


class AssetInput(Input):
    name: Name
    category: Literal['cash', 'checking', 'term_deposit', 'real_estate', 'other']
    currency: Currency = 'CNY'
    balance: NonNegative


class DreamInput(Input):
    name: Name
    price: Positive
    currency: Currency = 'CNY'
    priority: Literal['high', 'medium', 'low'] = 'medium'
    url: Annotated[str, Field(max_length=2000)] = ''
    note: Note = ''
    status: Literal['pending', 'purchased'] = 'pending'

    @field_validator('url')
    @classmethod
    def safe_link(cls, value):
        if value and (urlparse(value).scheme not in ('http', 'https') or not urlparse(value).netloc):
            raise ValueError('链接须为完整 http 或 https 地址')
        return value


class PurchaseInput(Input):
    amount: Positive | None = None
    currency: Currency | None = None


class HoldingInput(Input):
    symbol: Annotated[str, Field(min_length=1, max_length=40)]
    name: Name
    asset_type: Literal['stock', 'etf', 'fund', 'crypto', 'bond', 'other']
    currency: Currency = 'CNY'
    quantity: NonNegative = 0
    avg_cost: NonNegative = 0
    current_price: NonNegative = 0


class HoldingUpdate(Input):
    name: Name | None = None
    current_price: NonNegative | None = None


class TradeInput(Input):
    holding_id: Annotated[int, Field(gt=0)]
    action: Literal['buy', 'sell']
    quantity: Positive
    price: NonNegative
    fee: NonNegative = 0
    trade_date: date
    note: Note = ''
