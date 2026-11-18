"""Autocomplete gating, provider bounds, semantic parity and selection integration."""

import asyncio
import json
from pathlib import Path
import subprocess
import time

import httpx
import pytest

from app.main import app
from app.services import recipe_autocomplete as search
from app.services.cookbook_catalog import DISHES
from app.services.icon_parser import resolve_dish_icon
from app.services.parser import GroceryItem


@pytest.fixture(autouse=True)
def isolated_cache(monkeypatch, tmp_path):
    search._memory.clear()
    monkeypatch.setattr(search, "DB_PATH", tmp_path / "search.sqlite")
    yield
    search._memory.clear()


@pytest.mark.parametrize("query", ["canh", "canh ", " ga ", "canh c", ""])
async def test_single_word_or_short_second_word_never_requests(monkeypatch, query):
    def unexpected(*args, **kwargs):
        pytest.fail("Short query must not instantiate an HTTP client")
    monkeypatch.setattr(search.httpx, "AsyncClient", unexpected)
    result = await search.autocomplete(query)
    assert result["live_enabled"] is False


@pytest.mark.parametrize("title,icon", [
    ("canh chua", "🥣"), ("bún quậy", "🍜"), ("gà hấp", "🍗"), ("mực trứng", "🦑"),
    ("Canh cá hồi tôm mực", "🦑"), ("Canh cá hồi tôm", "🦐"),
    ("Canh cá hồi", "🐟"), ("Bún gà", "🍜"), ("Nui gà", "🥣"),
    ("Bò xào nấm", "🥩"), ("Đậu hũ", "🥬"), ("Spaghetti", "🍝"),
    ("Tomato pasta", "🍝"), ("Mushroom bowl", "🍲"), ("Unknown", "🍲"),
])
def test_exact_icon_priority_and_boundaries(title, icon):
    assert resolve_dish_icon(title)["icon"] == icon


def test_title_cleaner():
    assert search.clean_title("Easy Authentic Canh Chua Cá (Vietnamese Sour Fish Soup Recipe!)") == "Canh Chua Cá (Vietnamese Sour Fish Soup)"
    assert search.clean_title("<b>Gà</b> &amp; Nấm Recipe | Hungry Huy") == "Gà & Nấm"


async def test_two_word_concurrent_search_clean_titles_and_cache(monkeypatch):
    original = httpx.AsyncClient
    calls = []
    async def handler(request):
        calls.append(str(request.url))
        await asyncio.sleep(0.03)
        return httpx.Response(200, json=[{
            "title": {"rendered": "Easy Authentic Canh Chua Recipe!"},
            "link": f"https://{request.url.host}/canh-chua/",
        }])
    monkeypatch.setattr(search.httpx, "AsyncClient", lambda **kw: original(**kw, transport=httpx.MockTransport(handler)))
    start = time.monotonic()
    result = await search.autocomplete("canh chua")
    assert time.monotonic() - start < 0.3
    assert len(calls) == 3
    live = [r for r in result["suggestions"] if r["source_url"]]
    assert len(live) == 3
    assert all(r["title_clean"] == "Canh Chua" and r["icon"] == "🥣" for r in live)
    assert {r["source_domain"] for r in live} == {s[0] for s in search.SOURCES}
    cached = await search.autocomplete(" CÁNH   CHUA ")
    assert cached["cached"] and len(calls) == 3
    search._memory.clear()
    assert (await search.autocomplete("canh chua"))["cached"]
    assert len(calls) == 3


@pytest.mark.parametrize("query,expected", [
    ("canh chua", "🥣"), ("bun quay", "🍜"), ("ga hap", "🍗"), ("muc trung", "🦑"),
])
async def test_api_returns_live_icons(monkeypatch, query, expected):
    async def source(client, name, url, q):
        return [search.suggestion(q, source_domain=name, source_url=url)]
    monkeypatch.setattr(search, "_search_source", source)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
        r = await client.get("/api/cookbook/autocomplete", params={"q": query})
    assert r.status_code == 200
    rows = [r for r in r.json()["suggestions"] if r["source_url"]]
    assert rows and all(r["icon"] == expected for r in rows)


async def test_hard_timeout_retains_local_results(monkeypatch):
    async def slow(*args):
        await asyncio.sleep(5)
        return []
    monkeypatch.setattr(search, "_search_source", slow)
    start = time.monotonic()
    result = await search.autocomplete("ga hap")
    assert time.monotonic() - start < 1.5
    assert any(r["catalog_id"] for r in result["suggestions"])


async def test_provider_http_error_and_bad_data(monkeypatch):
    original = httpx.AsyncClient
    def handler(request):
        if "hungryhuy" in request.url.host:
            return httpx.Response(403)
        return httpx.Response(200, text="<html>not JSON</html>")
    monkeypatch.setattr(search.httpx, "AsyncClient", lambda **kw: original(**kw, transport=httpx.MockTransport(handler)))
    result = await search.autocomplete("ga hap")
    assert result["suggestions"]
    assert not any(r["source_url"] for r in result["suggestions"])


async def test_expired_cache_refetches(monkeypatch):
    search._remember("ga hap", time.time() - search.TTL - 1, [])
    calls = []
    async def source(*args):
        calls.append(1)
        return []
    monkeypatch.setattr(search, "_search_source", source)
    await search.autocomplete("ga hap")
    assert len(calls) == 3


async def test_catalog_and_live_selection(monkeypatch):
    from app.routes import canvas
    async def imported(url, family_servings=None):
        assert family_servings == 2.5
        return "Ga hap", [GroceryItem(name="Chicken", quantity=1.5, unit="lb", ingredient_id="chicken")], "Scaled for family.", None
    monkeypatch.setattr(canvas, "import_recipe_url", imported)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
        r = await client.post("/api/cookbook/select-suggestion", json={
            "title_clean": "ga hap", "source_url": "https://hungryhuy.com/ga-hap/",
        })
        assert r.status_code == 200
        assert r.json()["dish_name"] == "🍗 ga hap"
        assert r.json()["ingredients"][0]["quantity"] == 1.5
        assert r.json()["toddler_tip"]
        dish = next(d for d in DISHES if d.id == "canh_bau_tom")
        r = await client.post("/api/cookbook/select-suggestion", json={
            "title_clean": dish.display_name, "catalog_id": dish.id,
        })
        assert r.status_code == 200 and r.json()["ingredients"]
        assert r.json()["dish_name"].startswith("🦐")


async def test_selection_fallback(monkeypatch):
    from app.routes import canvas
    async def fail(*args, **kwargs):
        raise ValueError("Partial JSON-LD")
    monkeypatch.setattr(canvas, "import_recipe_url", fail)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
        r = await client.post("/api/cookbook/select-suggestion", json={
            "title_clean": "Bún quậy", "source_url": "https://hungryhuy.com/partial/",
        })
        assert r.status_code == 200 and r.json()["ingredients"]
        assert "estimates" in r.json()["parser_note"]


def test_python_js_icon_parity_and_catalog_snapshot():
    root = Path(__file__).resolve().parents[1]
    samples = ["Canh Chua", "Bún quậy", "Gà hấp", "Mực trứng", "cá hồi tôm mực",
               "tomato pasta", "Đậu hũ", "salmon", "pork", "spaghetti", "unknown"]
    script = "import {resolveDishIcon} from './frontend/src/utils/iconParser.js'; console.log(JSON.stringify(" + json.dumps(samples) + ".map(resolveDishIcon)))"
    result = subprocess.run(["node", "--input-type=module", "-e", script], cwd=root, check=True, capture_output=True, text=True)
    assert json.loads(result.stdout) == [resolve_dish_icon(s) for s in samples]
    snapshot = json.loads((root / "frontend/src/data/cookbookCatalog.json").read_text())
    assert {r["catalog_id"]: r["title_clean"] for r in snapshot} == {d.id: d.display_name for d in DISHES}
