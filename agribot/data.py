"""Download dei prezzi giornalieri (Yahoo Finance chart API, nessuna chiave richiesta)."""
from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone

import requests

_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; agri-intelligence-bot/1.0)"}
CACHE_SECONDS = 15 * 60


@dataclass
class PriceHistory:
    symbol: str
    dates: list[datetime]
    open: list[float]
    high: list[float]
    low: list[float]
    close: list[float]
    currency: str = "USD"
    last_update: datetime | None = None

    def __len__(self) -> int:
        return len(self.close)


class DataError(RuntimeError):
    pass


_cache: dict[str, tuple[float, PriceHistory]] = {}


def parse_chart(symbol: str, payload: dict) -> PriceHistory:
    try:
        result = payload["chart"]["result"][0]
        quote = result["indicators"]["quote"][0]
        stamps = result["timestamp"]
    except (KeyError, IndexError, TypeError) as exc:
        raise DataError(f"Risposta inattesa per {symbol}") from exc
    rows = []
    for i, ts in enumerate(stamps):
        o, h, l, c = (quote[k][i] for k in ("open", "high", "low", "close"))
        if None in (o, h, l, c):
            continue
        rows.append((datetime.fromtimestamp(ts, tz=timezone.utc), float(o), float(h), float(l), float(c)))
    if len(rows) < 60:
        raise DataError(f"Storico insufficiente per {symbol} ({len(rows)} barre)")
    meta = result.get("meta", {})
    market_time = meta.get("regularMarketTime")
    return PriceHistory(
        symbol=symbol,
        dates=[r[0] for r in rows],
        open=[r[1] for r in rows],
        high=[r[2] for r in rows],
        low=[r[3] for r in rows],
        close=[r[4] for r in rows],
        currency=meta.get("currency") or "USD",
        last_update=datetime.fromtimestamp(market_time, tz=timezone.utc) if market_time else rows[-1][0],
    )


def fetch_history(symbol: str, range_: str = "2y", session: requests.Session | None = None) -> PriceHistory:
    now = time.time()
    cached = _cache.get(symbol)
    if cached and now - cached[0] < CACHE_SECONDS:
        return cached[1]
    http = session or requests
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            resp = http.get(
                _URL.format(symbol=symbol),
                params={"range": range_, "interval": "1d"},
                headers=_HEADERS,
                timeout=15,
            )
            resp.raise_for_status()
            history = parse_chart(symbol, resp.json())
            _cache[symbol] = (now, history)
            return history
        except (requests.RequestException, ValueError, DataError) as exc:
            last_exc = exc
            time.sleep(1.5 * (attempt + 1))
    raise DataError(f"Impossibile scaricare {symbol}: {last_exc}")
