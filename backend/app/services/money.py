from decimal import Decimal, ROUND_HALF_UP, localcontext
import math

from fastapi import HTTPException
from sqlalchemy import select

from ..models import ExchangeRate


def decimal(value):
    return Decimal(str(value))


def rounded(value, places=2):
    with localcontext() as context:
        context.prec = max(64, len(decimal(value).as_tuple().digits) + abs(decimal(value).adjusted()) + places + 2)
        result = float(decimal(value).quantize(Decimal(10) ** -places, rounding=ROUND_HALF_UP))
    if not math.isfinite(result):
        raise HTTPException(422, '金额超出可计算范围')
    return result


def to_cny(db, amount, currency):
    amount = decimal(amount)
    if currency == 'CNY' or amount == 0:
        return rounded(amount)
    row = db.scalar(select(ExchangeRate).where(ExchangeRate.currency == currency))
    if row is None:
        raise HTTPException(409, f'尚无 {currency} 汇率，请联网刷新汇率后重试')
    return rounded(amount * decimal(row.rate))


def total(values):
    return rounded(sum((decimal(v) for v in values), Decimal(0)))
