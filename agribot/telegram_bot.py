"""Bot Telegram (long polling, nessuna libreria extra): python -m agribot.telegram_bot"""
from __future__ import annotations

import logging
import os
import time

import requests

from .chat import ChatSession

log = logging.getLogger("agribot.telegram")
API = "https://api.telegram.org/bot{token}/{method}"
MAX_LEN = 4000

WELCOME = """🌾 Agri Intelligence Bot
Ti do una direzione LONG / SHORT / NEUTRO sulle materie prime, calcolata su trend, momentum, breakout e RSI.

Esempi:
• oro long o short?
• com'è messo il gas naturale?
• classifica delle materie prime
• e le agricole?

Comandi: /classifica · /analisi <materia prima> · /reset · /help"""


def split_message(text: str, limit: int = MAX_LEN) -> list[str]:
    chunks, current = [], ""
    for para in text.split("\n"):
        while len(para) > limit:
            if current:
                chunks.append(current)
                current = ""
            chunks.append(para[:limit])
            para = para[limit:]
        candidate = f"{current}\n{para}" if current else para
        if len(candidate) > limit:
            chunks.append(current)
            current = para
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks or [""]


class TelegramBot:
    def __init__(self, token: str, allowed: set[int] | None = None):
        self.token = token
        self.allowed = allowed
        self.sessions: dict[int, ChatSession] = {}
        self.http = requests.Session()

    def call(self, method: str, **params):
        resp = self.http.post(API.format(token=self.token, method=method), json=params, timeout=70)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("ok"):
            raise RuntimeError(data.get("description", "errore Telegram"))
        return data["result"]

    def send(self, chat_id: int, text: str) -> None:
        for chunk in split_message(text):
            self.call("sendMessage", chat_id=chat_id, text=chunk, disable_web_page_preview=True)

    def handle(self, chat_id: int, text: str) -> str:
        session = self.sessions.setdefault(chat_id, ChatSession())
        cmd, _, arg = text.partition(" ")
        cmd = cmd.split("@")[0].lower()
        if cmd in {"/start", "/help", "/aiuto"}:
            return WELCOME
        if cmd == "/reset":
            session.reset()
            return "Conversazione azzerata ✅"
        if cmd == "/classifica":
            return session.ask("classifica di tutte le materie prime")
        if cmd == "/analisi":
            return session.ask(arg or "classifica") if arg else "Uso: /analisi oro (oppure grano, wti, rame...)"
        return session.ask(text)

    def run(self) -> None:
        offset = None
        log.info("Bot avviato, in ascolto...")
        while True:
            try:
                updates = self.call("getUpdates", timeout=50, offset=offset, allowed_updates=["message"])
            except Exception as exc:  # noqa: BLE001
                log.warning("getUpdates fallito: %s", exc)
                time.sleep(5)
                continue
            for upd in updates:
                offset = upd["update_id"] + 1
                msg = upd.get("message") or {}
                text = (msg.get("text") or "").strip()
                chat_id = (msg.get("chat") or {}).get("id")
                if not text or chat_id is None:
                    continue
                if self.allowed and chat_id not in self.allowed:
                    self.send(chat_id, "⛔ Chat non autorizzata.")
                    continue
                try:
                    self.call("sendChatAction", chat_id=chat_id, action="typing")
                    self.send(chat_id, self.handle(chat_id, text))
                except Exception as exc:  # noqa: BLE001
                    log.exception("Errore nella gestione del messaggio")
                    try:
                        self.send(chat_id, f"Errore temporaneo: {exc}")
                    except Exception:  # noqa: BLE001
                        pass


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("Imposta TELEGRAM_BOT_TOKEN (token da @BotFather).")
        return 1
    allowed_raw = os.getenv("TELEGRAM_ALLOWED_CHATS", "").strip()
    allowed = {int(x) for x in allowed_raw.split(",") if x.strip()} or None
    TelegramBot(token, allowed).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
