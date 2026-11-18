import json

from sqlalchemy import select

from ..models import AssetAccount, InvestmentHolding, NetWorthSnapshot
from .reporting import assets_data


def take_snapshot(db, today):
    db.flush()
    has_assets = db.scalar(select(AssetAccount.id).limit(1)) is not None
    has_holdings = db.scalar(select(InvestmentHolding.id).limit(1)) is not None
    # The initial empty app has no invented zero history. After real history,
    # deleting the final position must record zero rather than retain old wealth.
    if not has_assets and not has_holdings and db.scalar(select(NetWorthSnapshot.id).limit(1)) is None:
        return
    assets = assets_data(db)
    snapshot = db.scalar(select(NetWorthSnapshot).where(NetWorthSnapshot.snap_date == today))
    if snapshot is None:
        snapshot = NetWorthSnapshot(snap_date=today, total_cny=0, breakdown_json='{}')
        db.add(snapshot)
    snapshot.total_cny = assets['total_cny']
    snapshot.breakdown_json = json.dumps({r['category']: r['amount_cny'] for r in assets['by_category']})
    db.flush()
