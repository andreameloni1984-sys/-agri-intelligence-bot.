from types import SimpleNamespace

from agribot.chat import ChatSession, select_commodities
from agribot.data import DataError
from agribot.universe import UNIVERSE

from .helpers import make_history, trend


def fake_fetch(symbol):
    if symbol == "LE=F":
        raise DataError("offline")
    step = 0.002 if symbol in {"GC=F", "NG=F"} else -0.002
    return make_history(trend(step=step, wiggle=0.01), symbol)


def test_selection_followup_and_board():
    sel, board = select_commodities("oro?", [])
    assert [c.key for c in sel] == ["oro"] and not board
    sel, board = select_commodities("e lo stop?", sel)
    assert [c.key for c in sel] == ["oro"]
    sel, board = select_commodities("classifica", [])
    assert len(sel) == len(UNIVERSE) and board


def test_rule_based_reply():
    chat = ChatSession(fetch=fake_fetch, use_llm=False)
    out = chat.ask("oro long o short?")
    assert "LONG" in out and "Oro" in out
    board = chat.ask("classifica")
    assert "Classifica" in board and "Bovini vivi: offline" in board


class FakeClient:
    def __init__(self):
        self.calls = []
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self.create))

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(stop_reason="end_turn",
                               content=[SimpleNamespace(type="text", text="ORO → LONG")])


def test_llm_reply_gets_engine_data_and_keeps_history():
    client = FakeClient()
    chat = ChatSession(fetch=fake_fetch, client=client)
    assert chat.ask("oro?") == "ORO → LONG"
    first = client.calls[0]
    assert first["model"] == "claude-opus-5-5"
    assert "<dati_motore>" in first["messages"][-1]["content"]
    assert '"direction": "LONG"' in first["messages"][-1]["content"]
    chat.ask("e lo stop?")
    assert len(client.calls[1]["messages"]) == 3


def test_llm_failure_falls_back():
    class Broken(FakeClient):
        def create(self, **kwargs):
            raise RuntimeError("boom")
    chat = ChatSession(fetch=fake_fetch, client=Broken())
    assert "Oro" in chat.ask("oro")
