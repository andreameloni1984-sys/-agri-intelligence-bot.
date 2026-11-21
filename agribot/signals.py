"""Motore direzionale: combina trend, momentum, breakout e RSI in uno score -100..+100."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

from . import indicators as ind
from .data import PriceHistory
from .universe import Commodity

LONG_THRESHOLD = 25.0
SHORT_THRESHOLD = -25.0

WEIGHTS = {
    "trend_lungo": 20,   # prezzo/SMA200 e incrocio SMA50-SMA200
    "trend_medio": 15,   # prezzo/SMA50 e SMA20-SMA50
    "momentum": 25,      # time-series momentum 1/3/6/12 mesi
    "macd": 15,
    "breakout": 15,      # canali di Donchian 20/55
    "rsi": 10,           # ipercomprato/ipervenduto (contrarian agli estremi)
}


@dataclass
class Signal:
    key: str
    name: str
    symbol: str
    sector: str
    price: float
    currency: str
    as_of: str
    direction: str            # LONG / SHORT / NEUTRO
    score: float              # -100..+100
    strength: str             # forte / moderato / debole
    components: dict[str, float]
    metrics: dict[str, float | None]
    stop: float | None = None
    target1: float | None = None
    target2: float | None = None
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _sign(x: float | None) -> float:
    if x is None or x == 0:
        return 0.0
    return 1.0 if x > 0 else -1.0


def _clip(x: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def _r(x: float | None, nd: int = 4) -> float | None:
    return None if x is None else round(x, nd)


def analyze(commodity: Commodity, h: PriceHistory) -> Signal:
    c = h.close
    price = c[-1]
    sma20, sma50, sma200 = ind.sma(c, 20), ind.sma(c, 50), ind.sma(c, 200)
    rets = {lb: ind.pct_return(c, lb) for lb in (21, 63, 126, 252)}
    macd_v = ind.macd(c)
    rsi_v = ind.rsi(c)
    atr_v = ind.atr(h.high, h.low, c)
    vol = ind.realized_vol(c)
    d20 = ind.donchian(h.high, h.low, 20)
    d55 = ind.donchian(h.high, h.low, 55)

    comp: dict[str, float] = {}

    parts = [_sign(price - sma200) if sma200 else 0.0,
             _sign(sma50 - sma200) if (sma50 and sma200) else 0.0]
    comp["trend_lungo"] = sum(parts) / 2

    parts = [_sign(price - sma50) if sma50 else 0.0,
             _sign(sma20 - sma50) if (sma20 and sma50) else 0.0]
    comp["trend_medio"] = sum(parts) / 2

    valid = [r for r in rets.values() if r is not None]
    comp["momentum"] = sum(_sign(r) for r in valid) / len(valid) if valid else 0.0

    if macd_v:
        line, _sig, hist = macd_v
        comp["macd"] = (_sign(hist) + _sign(line)) / 2
    else:
        comp["macd"] = 0.0

    b = 0.0
    if d55 and price > d55[0]:
        b = 1.0
    elif d55 and price < d55[1]:
        b = -1.0
    elif d20:
        hi, lo = d20
        if price > hi:
            b = 0.6
        elif price < lo:
            b = -0.6
        elif hi > lo:
            b = _clip(((price - lo) / (hi - lo) - 0.5) * 0.8, -0.4, 0.4)
    comp["breakout"] = b

    if rsi_v is None:
        comp["rsi"] = 0.0
    elif rsi_v >= 70:
        comp["rsi"] = -_clip((rsi_v - 65) / 15, 0.3, 1.0)
    elif rsi_v <= 30:
        comp["rsi"] = _clip((35 - rsi_v) / 15, 0.3, 1.0)
    else:
        comp["rsi"] = (rsi_v - 50) / 40  # lieve conferma di momentum nella zona neutra

    score = round(sum(WEIGHTS[k] * v for k, v in comp.items()), 1)
    if score >= LONG_THRESHOLD:
        direction = "LONG"
    elif score <= SHORT_THRESHOLD:
        direction = "SHORT"
    else:
        direction = "NEUTRO"
    a = abs(score)
    strength = "forte" if a >= 60 else "moderato" if a >= 40 else "debole"

    stop = t1 = t2 = None
    if atr_v and direction != "NEUTRO":
        s = 1 if direction == "LONG" else -1
        stop = price - s * 2 * atr_v
        t1 = price + s * 2 * atr_v
        t2 = price + s * 4 * atr_v

    warnings: list[str] = []
    if rsi_v is not None and direction == "LONG" and rsi_v >= 70:
        warnings.append(f"RSI {rsi_v:.0f}: ipercomprato, rischio di ritracciamento a breve")
    if rsi_v is not None and direction == "SHORT" and rsi_v <= 30:
        warnings.append(f"RSI {rsi_v:.0f}: ipervenduto, rischio di rimbalzo a breve")
    if vol is not None and vol > 0.45:
        warnings.append(f"Volatilità elevata ({vol:.0%} annua): ridurre la size")
    if direction != "NEUTRO":
        opposite = [k for k, v in comp.items() if k != "rsi" and _sign(v) == -_sign(score) and abs(v) >= 0.5]
        if opposite:
            warnings.append("Componenti in disaccordo: " + ", ".join(opposite))

    metrics = {
        "sma20": _r(sma20), "sma50": _r(sma50), "sma200": _r(sma200),
        "ret_1m": _r(rets[21]), "ret_3m": _r(rets[63]), "ret_6m": _r(rets[126]), "ret_12m": _r(rets[252]),
        "rsi14": _r(rsi_v, 1), "macd_hist": _r(macd_v[2] if macd_v else None),
        "atr14": _r(atr_v), "vol_20d_annua": _r(vol),
        "max_20g": _r(d20[0] if d20 else None), "min_20g": _r(d20[1] if d20 else None),
        "max_55g": _r(d55[0] if d55 else None), "min_55g": _r(d55[1] if d55 else None),
    }
    return Signal(
        key=commodity.key, name=commodity.name, symbol=commodity.symbol, sector=commodity.sector,
        price=round(price, 4), currency=h.currency,
        as_of=(h.last_update or h.dates[-1]).strftime("%Y-%m-%d %H:%M UTC"),
        direction=direction, score=score, strength=strength,
        components={k: round(v, 2) for k, v in comp.items()}, metrics=metrics,
        stop=_r(stop), target1=_r(t1), target2=_r(t2), warnings=warnings,
    )
