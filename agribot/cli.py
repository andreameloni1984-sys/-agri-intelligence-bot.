"""Chat da terminale: python -m agribot.cli"""
from __future__ import annotations

import sys

from .chat import ChatSession

HELP = """Scrivi una domanda, es.:
  oro long o short?
  com'è messo il petrolio brent?
  classifica delle materie prime
  e le agricole?
Comandi: /reset (nuova conversazione), /esci"""


def main() -> int:
    session = ChatSession()
    mode = "Claude" if session.llm_enabled else "report a regole (imposta ANTHROPIC_API_KEY per le risposte di Claude)"
    print(f"🌾 Agri Intelligence Bot — modalità: {mode}\n{HELP}\n")
    if len(sys.argv) > 1:
        print(session.ask(" ".join(sys.argv[1:])))
        return 0
    while True:
        try:
            text = input("tu › ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not text:
            continue
        if text in {"/esci", "/exit", "/quit"}:
            return 0
        if text == "/reset":
            session.reset()
            print("Conversazione azzerata.\n")
            continue
        print("\nbot › " + session.ask(text) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
