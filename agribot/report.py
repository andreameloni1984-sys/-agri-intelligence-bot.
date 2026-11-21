"""Formattazione testuale dei segnali (usata da sola o come base per Claude)."""
from __future__ import annotations

from .signals import Signal

ICON = {"LONG": "🟢 LONG", "SHORT": "🔴 SHORT", "NEUTRO": "⚪ NEUTRO"}
LABELS = {
    "trend_lungo": "Trend lungo (SMA200)",
    "trend_medio": "Trend medio (SMA50)",
    "momentum": "Momentum 1-12 mesi",
    "macd": "MACD",
    "breakout": "Breakout Donchian",
    "rsi": "RSI",
}


def _fmt(x: float | None) -> str:
    if x is None:
        return "n.d."
    return f"{x:,.2f}" if abs(x) >= 10 else f"{x:.4f}"


def _pct(x: float | None) -> str:
    return "n.d." if x is None else f"{x:+.1%}"


def format_signal(s: Signal) -> str:
    m = s.metrics
    lines = [
        f"{s.name} ({s.symbol}) — {ICON[s.direction]} · score {s.score:+.0f}/100 ({s.strength})",
        f"Prezzo {_fmt(s.price)} {s.currency} · dato del {s.as_of}",
        f"Rendimenti: 1m {_pct(m['ret_1m'])} · 3m {_pct(m['ret_3m'])} · 6m {_pct(m['ret_6m'])} · 12m {_pct(m['ret_12m'])}",
        f"RSI14 {m['rsi14'] if m['rsi14'] is not None else 'n.d.'} · ATR14 {_fmt(m['atr14'])} · "
        f"SMA50 {_fmt(m['sma50'])} · SMA200 {_fmt(m['sma200'])}",
        "Componenti: " + " · ".join(f"{LABELS[k]} {v:+.1f}" for k, v in s.components.items()),
    ]
    if s.direction != "NEUTRO":
        lines.append(
            f"Livelli indicativi: stop {_fmt(s.stop)} · target1 {_fmt(s.target1)} · target2 {_fmt(s.target2)} (2/4 ATR)"
        )
    else:
        lines.append("Nessun vantaggio direzionale chiaro: meglio restare flat o attendere conferme.")
    for w in s.warnings:
        lines.append(f"⚠️ {w}")
    return "\n".join(lines)


def format_board(signals: list[Signal]) -> str:
    ordered = sorted(signals, key=lambda s: -abs(s.score))
    lines = ["📊 Classifica direzionale materie prime (ordinata per forza del segnale)", ""]
    for s in ordered:
        lines.append(f"{ICON[s.direction]:<10} {s.name:<16} score {s.score:+5.0f} · RSI {s.metrics['rsi14']} · 3m {_pct(s.metrics['ret_3m'])}")
    return "\n".join(lines)


DISCLAIMER = "ℹ️ Analisi quantitativa automatica a scopo informativo: non è una raccomandazione d'investimento."
