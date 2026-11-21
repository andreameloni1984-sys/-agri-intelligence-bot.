from agribot.telegram_bot import split_message


def test_split_message():
    text = "\n".join(["x" * 100] * 100)
    chunks = split_message(text, limit=1000)
    assert all(len(c) <= 1000 for c in chunks)
    assert "\n".join(chunks).replace("\n", "") == text.replace("\n", "")
