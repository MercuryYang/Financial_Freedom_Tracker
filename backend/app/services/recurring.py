import calendar
from datetime import date

from sqlalchemy import select

from ..models import RecurringRule, Transaction


def next_month(day):
    return date(day.year + (day.month == 12), 1 if day.month == 12 else day.month + 1, 1)


def ensure_recurring_due(db, today):
    for rule in db.scalars(select(RecurringRule).where(RecurringRule.active.is_(True))):
        month = next_month(rule.last_generated) if rule.last_generated else rule.created_date.replace(day=1)
        while month <= today:
            due = month.replace(day=min(rule.day_of_month, calendar.monthrange(month.year, month.month)[1]))
            if due > today:
                break
            existing = db.scalar(select(Transaction.id).where(Transaction.recurring_rule_id == rule.id, Transaction.tx_date == due))
            if existing is None:
                db.add(Transaction(type=rule.type, amount=rule.amount, currency=rule.currency,
                                   category=rule.category, note=rule.note, tx_date=due,
                                   source='recurring', recurring_rule_id=rule.id))
            rule.last_generated = due
            month = next_month(month)
    db.flush()
