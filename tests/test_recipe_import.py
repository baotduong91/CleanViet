"""Regression coverage for URL previews and shopping calculations."""
import json
import socket
from decimal import Decimal
from unittest.mock import patch

import httpx
import pytest

from app.main import app
from app.services.recipe_import import _match_ingredient, _source_item
from app.services.meal_transform import apply_preferences
from app.services.parser import parse_dish
from app.services.recommender import recommend


@pytest.fixture
def public_dns(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))
    ])


async def preview(monkeypatch, handler, url="https://hungryhuy.com/recipe"):
    original = httpx.AsyncClient
    async with original(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as api:
        with patch("app.services.remote_fetch.httpx.AsyncClient",
                   lambda **kw: original(**kw, transport=httpx.MockTransport(handler))):
            return await api.post("/api/cookbook/import-url", json={"url": url})


def page(recipe):
    return httpx.Response(200, text='<script TYPE = "application/ld+json">' + json.dumps(recipe) + '</script>')


async def test_api_import_source_amounts_unknowns_duplicates_and_toddler_tip(monkeypatch, public_dns):
    recipe = {"@graph": [{"@type": ["Thing", "Recipe"], "name": "Salmon dinner",
                         "recipeIngredient": ["2 lb salmon", "8 oz salmon", "2 tomatoes",
                                              "fish sauce", "1 L chicken broth"]}]}
    r = await preview(monkeypatch, lambda req: page(recipe))
    assert r.status_code == 200, r.text
    data = r.json()
    assert "pin bones" in data["toddler_tip"]
    items = data["ingredients"]
    assert [(i["quantity"], i["unit"]) for i in items[:2]] == [(2, "lb"), (0.5, "lb")]
    assert items[2]["name"] == "2 tomatoes" and items[2]["ingredient_id"] is None
    assert items[3]["ingredient_id"] is None
    assert items[4]["ingredient_id"] == "broth"
    shopping = recommend([data])
    lines = [i for r in shopping["routes"] for s in r["stores"] for i in s["items"]]
    assert next(i for i in lines if i["id"] == "salmon|lb")["quantity"] == "2.50"


@pytest.mark.parametrize("line,expected", [
    ("1½ lb shrimp", 1.5), ("1 1/2 lb shrimp", 1.5),
    ("½ lb shrimp", 0.5), ("1/4 lb shrimp", 0.25),
    ("500 g shrimp", 500 / 453.59237), ("1 kg shrimp", 1000 / 453.59237),
    ("8 oz shrimp", 0.5), ("250 ml broth", 0.25),
])
def test_quantity_conversion(line, expected):
    assert _source_item(line).quantity == pytest.approx(expected)


def test_ingredient_boundaries_and_specificity():
    assert _match_ingredient("tomatoes") == "tomato"
    assert _match_ingredient("fish sauce") is None
    assert _match_ingredient("chicken broth") == "broth"
    assert _match_ingredient("pork ribs") == "pork_ribs"
    assert _match_ingredient("king oyster mushrooms") == "king_oyster"
    assert _source_item("1/0 lb shrimp").unit == "each"
    assert _source_item("2 cups rice").ingredient_id is None


async def test_string_ingredients(monkeypatch, public_dns):
    r = await preview(monkeypatch, lambda req: page({
        "@type": "https://schema.org/Recipe", "name": "Salmon", "recipeIngredient": "2 lb salmon",
    }))
    assert r.status_code == 200
    assert r.json()["ingredients"][0]["quantity"] == 2


@pytest.mark.parametrize("payload", [
    {}, {"@type": "Recipe", "recipeIngredient": []},
    {"@type": "Recipe", "recipeIngredient": {"salmon": 2}},
])
async def test_invalid_recipe_data(monkeypatch, public_dns, payload):
    r = await preview(monkeypatch, lambda req: page(payload))
    assert r.status_code == 422


async def test_redirect_rejected_before_request(monkeypatch, public_dns):
    visited = []
    def handler(req):
        visited.append(str(req.url))
        return httpx.Response(302, headers={"location": "http://127.0.0.1/private"})
    r = await preview(monkeypatch, handler)
    assert r.status_code == 422
    assert visited == ["https://hungryhuy.com/recipe"]


async def test_valid_redirect_and_upstream_failure(monkeypatch, public_dns):
    def handler(req):
        if req.url.path == "/recipe":
            return httpx.Response(302, headers={"location": "/next"})
        return page({"@type": "Recipe", "recipeIngredient": ["1 lb salmon"]})
    assert (await preview(monkeypatch, handler)).status_code == 200
    assert (await preview(monkeypatch, lambda req: httpx.Response(500))).status_code == 502


async def test_private_dns_blocked(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 80))
    ])
    def unexpected(req):
        pytest.fail("Private destination must not be requested")
    assert (await preview(monkeypatch, unexpected)).status_code == 422


async def test_image_redirect_also_blocked(monkeypatch, public_dns):
    visited = []
    def handler(req):
        visited.append(str(req.url))
        if req.url.host == "hungryhuy.com":
            return page({"@type": "Recipe", "name": "Salmon", "recipeIngredient": ["1 lb salmon"],
                         "image": "https://images.example.com/photo.jpg"})
        return httpx.Response(302, headers={"location": "http://127.0.0.1/private"})
    # Image fetch fails gracefully, preserving recipe preview.
    def resolve(host, *a, **k):
        ip = "127.0.0.1" if host == "127.0.0.1" else "93.184.216.34"
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 443))]
    monkeypatch.setattr(socket, "getaddrinfo", resolve)
    r = await preview(monkeypatch, handler)
    assert r.status_code == 200
    assert r.json()["image_url"] is None
    assert len(visited) == 2


def test_broth_savings_and_preference_scaling():
    meal = parse_dish("Súp nui tôm thịt").model_dump()
    result = recommend([meal], preferences={"homemade_broth": True})
    assert Decimal(result["estimated_savings"]) == Decimal(result["estimated_weee"]) - Decimal(result["estimated_cost"])
    meals = [{"ingredients": [
        {"name": kid, "ingredient_id": kid, "quantity": 1, "unit": "lb"}
        for kid in ["salmon", "bun", "carrot"]
    ]}]
    adjusted = apply_preferences(meals, {"pack_lunch": [True], "lean_mode": True})
    assert [i["quantity"] for i in adjusted[0]["ingredients"]] == [1.5, 1.125, 1.3]
    assert [i["quantity"] for i in meals[0]["ingredients"]] == [1, 1, 1]


@pytest.mark.parametrize("url", [
    "https://hungryhuy.com.evil.test/recipe",
    "https://user:password@hungryhuy.com/recipe",
    "https://hungryhuy.com:8080/recipe",
    "file:///etc/passwd",
])
async def test_invalid_urls_never_fetched(monkeypatch, public_dns, url):
    def unexpected(req):
        pytest.fail("Invalid URL must never be fetched")
    assert (await preview(monkeypatch, unexpected, url)).status_code == 422


async def test_download_limit(monkeypatch, public_dns):
    r = await preview(monkeypatch, lambda req: httpx.Response(200, content=b"x" * (2 * 1024 * 1024 + 1)))
    assert r.status_code == 422


async def test_redirect_loop(monkeypatch, public_dns):
    visits = []
    def handler(req):
        visits.append(req.url)
        return httpx.Response(302, headers={"location": "/recipe"})
    assert (await preview(monkeypatch, handler)).status_code == 422
    assert len(visits) == 6


async def test_compressed_recipe_page(monkeypatch, public_dns):
    import gzip
    body = b'<script type="application/ld+json">{"@type":"Recipe","recipeIngredient":["2 lb salmon"]}</script>'
    r = await preview(monkeypatch, lambda req: httpx.Response(
        200, content=gzip.compress(body), headers={"content-encoding": "gzip"},
    ))
    assert r.status_code == 200
    assert r.json()["ingredients"][0]["quantity"] == 2


async def test_import_normalizes_family_yield_without_changing_regular_import(monkeypatch, public_dns):
    from app.services.recipe_import import import_recipe_url
    recipe = {"@type": "Recipe", "name": "Salmon", "recipeYield": "4 servings",
              "recipeIngredient": ["2 lb salmon", "2 cups rice"]}
    original = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: original(
        **kw, transport=httpx.MockTransport(lambda req: page(recipe))))
    _, items, note, _ = await import_recipe_url("https://hungryhuy.com/recipe", family_servings=2.5)
    assert items[0].quantity == 1.25
    assert items[1].ingredient_id == "rice"
    assert items[1].unit == "lb"
    assert "family estimates" in note
    assert "not scaled" not in note
