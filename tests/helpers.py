from datetime import datetime, timedelta, timezone

from agribot.data import PriceHistory


def make_history(closes, symbol="TEST"):
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    dates = [start + timedelta(days=i) for i in range(len(closes))]
    return PriceHistory(
        symbol=symbol, dates=dates,
        open=list(closes),
        high=[c * 1.01 for c in closes],
        low=[c * 0.99 for c in closes],
        close=list(closes),
        last_update=dates[-1],
    )


def trend(n=400, start=100.0, step=0.002, wiggle=0.0):
    out, p = [], start
    for i in range(n):
        p *= 1 + step + (wiggle if i % 2 else -wiggle)
        out.append(p)
    return out
