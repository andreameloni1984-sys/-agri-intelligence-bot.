# 🌾 Agri Intelligence Bot

Chat di analisi che dà una **direzione LONG / SHORT / NEUTRO** sulle materie prime.
Funziona su **Telegram** o da **terminale**.

## Come funziona

1. **Capisce la domanda**: riconosce le materie prime citate (oro, grano, petrolio brent, gas, caffè…),
   i settori (“le agricole”, “i metalli”) o richieste di classifica. Le domande di seguito
   (“e lo stop?”) riusano l'ultima selezione.
2. **Scarica i prezzi** giornalieri dei future (Yahoo Finance, nessuna chiave, cache 15 minuti).
3. **Calcola uno score da -100 a +100** combinando:

   | Componente | Peso | Cosa misura |
   |---|---|---|
   | Trend lungo | 20 | prezzo vs SMA200, SMA50 vs SMA200 |
   | Trend medio | 15 | prezzo vs SMA50, SMA20 vs SMA50 |
   | Momentum | 25 | segno dei rendimenti a 1, 3, 6, 12 mesi |
   | MACD | 15 | linea e istogramma |
   | Breakout | 15 | canali di Donchian 20 e 55 giorni |
   | RSI | 10 | contrarian agli estremi (>70 / <30) |

   **LONG** se score ≥ +25, **SHORT** se ≤ −25, altrimenti **NEUTRO**.
   Stop a 2 ATR, target a 2 e 4 ATR. Avvisi su RSI estremo, volatilità alta e componenti discordanti.
4. **Risponde**: con `ANTHROPIC_API_KEY` impostata, Claude (`claude-opus-5-5`) scrive la risposta
   in italiano partendo dai numeri del motore e mantiene il contesto della conversazione.
   Senza chiave (o se l'API non risponde) il bot invia il report a regole.
   Il fallback lato server dell'API è attivo: se il modello rifiuta una richiesta, l'API la ripete
   su un modello di riserva.

Universo: oro, argento, platino, rame, WTI, Brent, gas naturale, grano, mais, soia, caffè,
zucchero, cacao, cotone, bovini vivi (modificabile in `agribot/universe.py`).

## Avvio

```bash
pip install -r requirements.txt
cp .env.example .env   # inserisci le chiavi, poi esportale nell'ambiente

# Chat da terminale
python -m agribot.cli
python -m agribot.cli "oro long o short?"

# Bot Telegram (token da @BotFather)
export TELEGRAM_BOT_TOKEN=...
export ANTHROPIC_API_KEY=...          # opzionale
export TELEGRAM_ALLOWED_CHATS=12345   # opzionale, limita chi può usarlo
python -m agribot.telegram_bot
```

Comandi Telegram: `/classifica`, `/analisi <materia prima>`, `/reset`, `/help`, oppure testo libero.

Variabili opzionali: `AGRIBOT_MODEL` (modello Claude), `AGRIBOT_DISABLE_LLM=1` (solo report a regole).

## Test

```bash
pytest -q
```

> ⚠️ Analisi quantitativa automatica a scopo informativo. Non è una consulenza finanziaria:
> i segnali trend-following sbagliano spesso nei mercati laterali. Usa sempre stop e size adeguata.
