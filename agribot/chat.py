"""Sessione di chat: capisce di quali materie prime si parla, calcola i segnali e risponde.

Con ANTHROPIC_API_KEY impostata, la risposta è scritta da Claude a partire dai dati
calcolati dal motore quantitativo; senza chiave, il bot risponde con il report a regole.
"""
from __future__ import annotations

import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Callable

from . import report
from .data import DataError, PriceHistory, fetch_history
from .signals import Signal, analyze
from .universe import UNIVERSE, Commodity, find_commodities, find_sectors

log = logging.getLogger(__name__)

MODEL = os.getenv("AGRIBOT_MODEL", "claude-opus-5-5")
MAX_HISTORY_MESSAGES = 16

SYSTEM_PROMPT = """Sei l'analista di "Agri Intelligence Bot", una chat in italiano che dà una direzione \
operativa (LONG, SHORT o NEUTRO) sulle materie prime.

Ad ogni domanda ricevi, in un blocco <dati_motore>, l'output JSON di un motore quantitativo calcolato \
su prezzi giornalieri dei future (trend SMA20/50/200, time-series momentum 1/3/6/12 mesi, MACD, \
breakout Donchian 20/55, RSI14, ATR14, volatilità). Lo score va da -100 (forte short) a +100 (forte long); \
LONG sopra +25, SHORT sotto -25.

Come rispondere:
- Per ogni materia prima richiesta apri con la direzione in grassetto-testo, es. "ORO → LONG (score +62, forte)".
- Spiega in 2-4 frasi il perché, citando i numeri del motore (trend, momentum, RSI, breakout).
- Indica livelli indicativi di stop e target dal JSON, e il principale rischio (avvertenze del motore).
- Se il quadro è misto o lo score è debole, dillo chiaramente: NEUTRO è una risposta valida.
- Puoi aggiungere contesto fondamentale generale (stagionalità, dollaro, scorte, meteo, OPEC...) ma \
presentalo come contesto, non come fatto di oggi: non hai notizie in tempo reale e non devi inventare \
prezzi, dati o eventi che non sono nel JSON.
- Se chiedono una classifica, ordina per |score| e segnala le 2-3 opportunità migliori long e short.
- Stile: conciso, adatto a Telegram (testo semplice, niente tabelle markdown, al massimo ~250 parole \
salvo richiesta esplicita).
- Chiudi con una riga breve che ricorda che è un'analisi automatica e non una consulenza finanziaria."""

_BOARD_WORDS = ("classifica", "tutte", "tutti", "panoramica", "migliori", "migliore", "overview",
                "quali", "quale", "opportunit", "mercato", "scanner", "ranking")

Fetcher = Callable[[str], PriceHistory]


def compute_signals(commodities: list[Commodity], fetch: Fetcher = fetch_history) -> tuple[list[Signal], list[str]]:
    def one(c: Commodity):
        try:
            return analyze(c, fetch(c.symbol)), None
        except DataError as exc:
            return None, f"{c.name}: {exc}"

    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(one, commodities))
    signals = [s for s, _ in results if s]
    errors = [e for _, e in results if e]
    return signals, errors


def select_commodities(text: str, previous: list[Commodity]) -> tuple[list[Commodity], bool]:
    """Restituisce (materie prime da analizzare, è_una_classifica)."""
    named = find_commodities(text)
    if named:
        return named, False
    sector = find_sectors(text)
    if sector:
        return sector, len(sector) > 2
    low = text.lower()
    if any(w in low for w in _BOARD_WORDS):
        return list(UNIVERSE), True
    if previous:  # domanda di follow-up ("e lo stop?", "perché?")
        return previous, len(previous) > 2
    return list(UNIVERSE), True


def _claude_client():
    if os.getenv("AGRIBOT_DISABLE_LLM"):
        return None
    try:
        import anthropic
    except ImportError:
        return None
    try:
        return anthropic.Anthropic()
    except Exception:  # noqa: BLE001 - configurazione errata
        return None


class ChatSession:
    def __init__(self, fetch: Fetcher = fetch_history, client=None, use_llm: bool = True):
        self.fetch = fetch
        self.client = client if client is not None else (_claude_client() if use_llm else None)
        self.history: list[dict] = []
        self.last_selection: list[Commodity] = []

    def reset(self) -> None:
        self.history.clear()
        self.last_selection = []

    @property
    def llm_enabled(self) -> bool:
        return self.client is not None

    def rule_based_reply(self, signals: list[Signal], errors: list[str], board: bool) -> str:
        parts = []
        if board:
            parts.append(report.format_board(signals))
            top = [s for s in sorted(signals, key=lambda s: -abs(s.score)) if s.direction != "NEUTRO"][:3]
            if top:
                parts.append("Dettaglio dei segnali più forti:")
                parts.extend(report.format_signal(s) for s in top)
        else:
            parts.extend(report.format_signal(s) for s in signals)
        if errors:
            parts.append("Dati non disponibili: " + "; ".join(errors))
        parts.append(report.DISCLAIMER)
        return "\n\n".join(parts)

    def ask(self, text: str) -> str:
        selection, board = select_commodities(text, self.last_selection)
        signals, errors = compute_signals(selection, self.fetch)
        if not signals:
            return "Non riesco a scaricare i prezzi in questo momento. " + "; ".join(errors)
        self.last_selection = selection

        if not self.llm_enabled:
            return self.rule_based_reply(signals, errors, board)

        payload = {
            "tipo_richiesta": "classifica" if board else "analisi",
            "segnali": [s.to_dict() for s in signals],
            "errori_dati": errors,
        }
        user_content = (
            f"<dati_motore>\n{json.dumps(payload, ensure_ascii=False)}\n</dati_motore>\n\n"
            f"Domanda dell'utente: {text}"
        )
        messages = self.history + [{"role": "user", "content": user_content}]
        try:
            reply = self._call_claude(messages)
        except Exception as exc:  # noqa: BLE001 - la chat non deve mai cadere
            if type(exc).__name__ in {"AuthenticationError", "PermissionDeniedError"} or "credential" in str(exc).lower() \
                    or "api_key" in str(exc).lower():
                log.warning("Credenziali Claude assenti o non valide: passo al report a regole")
                self.client = None
            log.warning("Claude non disponibile (%s): uso il report a regole", exc)
            return self.rule_based_reply(signals, errors, board)

        self.history = (messages + [{"role": "assistant", "content": reply}])[-MAX_HISTORY_MESSAGES:]
        while self.history and self.history[0]["role"] != "user":
            self.history.pop(0)
        return reply

    def _call_claude(self, messages: list[dict]) -> str:
        response = self.client.beta.messages.create(
            model=MODEL,
            max_tokens=16000,
            system=SYSTEM_PROMPT,
            output_config={"effort": "medium"},
            # Se il modello principale rifiuta, l'API riprova in automatico su un modello di riserva.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            messages=messages,
        )
        if response.stop_reason == "refusal":
            raise RuntimeError("richiesta rifiutata dal modello")
        text = "".join(b.text for b in response.content if b.type == "text").strip()
        if not text:
            raise RuntimeError("risposta vuota")
        return text
