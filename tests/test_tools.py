from types import SimpleNamespace

from utils.data_loader import get_example_wardrobe
from tools import create_fit_card, search_listings, suggest_outfit


class _FakeCompletions:
    def __init__(self, content: str):
        self.content = content
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=self.content))]
        )


class _FakeClient:
    def __init__(self, content: str):
        self.chat = SimpleNamespace(completions=_FakeCompletions(content))


def test_search_returns_results():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert isinstance(results, list)
    assert len(results) > 0
    assert all(item["price"] <= 50 for item in results)
    assert all(isinstance(item, dict) for item in results)


def test_search_empty_results():
    results = search_listings("designer ballgown", size="XXS", max_price=5)
    assert results == []


def test_search_price_and_size_filter():
    results = search_listings("vintage polo shirt", size="M", max_price=20)
    assert results
    assert results[0]["id"] == "lst_024"
    assert all(item["price"] <= 20 for item in results)
    assert all("m" in item["size"].lower() for item in results)


def test_suggest_outfit_empty_wardrobe_handles_gracefully(monkeypatch):
    fake_client = _FakeClient("Try the tee with relaxed denim and chunky sneakers for a 90s look.")
    monkeypatch.setattr("tools._get_groq_client", lambda: fake_client)

    new_item = {
        "title": "Graphic Tee — 2003 Tour Bootleg Style",
        "category": "tops",
        "size": "L",
        "colors": ["black"],
        "style_tags": ["graphic tee", "vintage", "grunge"],
        "price": 24.0,
        "platform": "depop",
    }

    result = suggest_outfit(new_item=new_item, wardrobe={"items": []})

    assert isinstance(result, str)
    assert "denim" in result.lower()
    call = fake_client.chat.completions.calls[0]
    assert call["model"] == "llama-3.3-70b-versatile"
    assert "no wardrobe items yet" in call["messages"][1]["content"].lower()


def test_suggest_outfit_uses_wardrobe_items(monkeypatch):
    fake_client = _FakeClient("Pair the tee with the wide-leg jeans and the chunky white sneakers.")
    monkeypatch.setattr("tools._get_groq_client", lambda: fake_client)

    new_item = {
        "title": "Vintage Polo Shirt — Forest Green",
        "category": "tops",
        "size": "M",
        "colors": ["green"],
        "style_tags": ["vintage", "preppy", "classic"],
        "price": 18.0,
        "platform": "depop",
    }

    result = suggest_outfit(new_item=new_item, wardrobe=get_example_wardrobe())

    assert isinstance(result, str)
    assert "wide-leg jeans" in result.lower()
    call = fake_client.chat.completions.calls[0]
    prompt = call["messages"][1]["content"]
    assert "Vintage Polo Shirt — Forest Green" in prompt
    assert "Baggy straight-leg jeans" in prompt
    assert "Chunky white sneakers" in prompt


def test_create_fit_card_empty_outfit_returns_error():
    result = create_fit_card(outfit="", new_item={"title": "Graphic Tee"})
    assert isinstance(result, str)
    assert "error" in result.lower()


def test_create_fit_card_calls_llm(monkeypatch):
    fake_client = _FakeClient("thrifted this faded band tee off depop for $22 and it hit perfect with my wide-legs")
    monkeypatch.setattr("tools._get_groq_client", lambda: fake_client)

    new_item = {
        "title": "Faded Band Tee",
        "category": "tops",
        "size": "M",
        "colors": ["black"],
        "style_tags": ["vintage", "grunge"],
        "price": 22.0,
        "platform": "depop",
        "condition": "good",
    }

    result = create_fit_card(
        outfit="Pair it with baggy jeans and chunky sneakers.",
        new_item=new_item,
    )

    assert isinstance(result, str)
    assert "depop" in result.lower()
    call = fake_client.chat.completions.calls[0]
    assert call["model"] == "llama-3.3-70b-versatile"
    assert "Faded Band Tee" in call["messages"][1]["content"]
    assert "Pair it with baggy jeans" in call["messages"][1]["content"]
