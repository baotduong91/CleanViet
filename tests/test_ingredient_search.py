"""Vietnamese cut-specific lookup, conservative matching and flyer identity."""
import httpx
import pytest

from app.main import app
from app.services.ingredient_search import search_ingredients
from app.services.recommender import item_intel
from app.services import live_prices


@pytest.mark.parametrize("query,kid", [
    ("thịt bò phi lê", "beef_tenderloin"),
    (" THIT   BO   PHI-LE ", "beef_tenderloin"),
    ("bo phile", "beef_tenderloin"),
    ("beef filet", "beef_tenderloin"),
    ("phi lê bò", "beef_tenderloin"),
    ("filet mignon", "beef_tenderloin"),
    ("thịt bò xay", "beef"),
    ("thịt heo bằm", "pork"),
    ("bắp bò", "beef_shank"),
    ("ức gà", "chicken_breast"),
    ("thịt heo phi lê", "pork_tenderloin"),
    ("nấm đùi gà", "king_oyster"),
    ("nấm bào ngư", "oyster_mushroom"),
    ("mực trứng", "squid"),
    ("phi lê cá hồi", "salmon"),
    ("cá basa", "catfish"),
    ("mộc nhĩ", "wood_ear"),
    ("rau muống", "water_spinach"),
    ("cải thìa", "bok_choy"),
    ("tôm sú", "tiger_shrimp"),
    ("tomatoes", "tomato"),
])
def test_specific_matches(query, kid):
    result = item_intel(query)
    assert result and result[0]["ingredient"]["id"] == kid


@pytest.mark.parametrize("query", ["", "   ", "xyzznotfood", "thit bo wagyu", "tomatillo"])
def test_unknown_queries_do_not_become_unrelated_ingredients(query):
    assert search_ingredients(query) == []


def test_specific_cut_and_broad_queries():
    tenderloin = item_intel("thit bo phi le")
    assert [r["ingredient"]["id"] for r in tenderloin] == ["beef_tenderloin"]
    assert {"beef", "beef_tenderloin"}.issubset({r["ingredient"]["id"] for r in item_intel("thit bo")})
    assert item_intel("rau muong")[0]["store"]["id"] == "greens"
    assert item_intel("tom su")[0]["store"]["id"] == "seafood"


async def test_vietnamese_query_uses_correct_english_flyer_and_baseline(monkeypatch):
    queries = []
    async def no_deals(query, zip_code):
        queries.append(query)
        return []
    monkeypatch.setattr(live_prices, "fetch_live_oc_deals", no_deals)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
        r = await client.get("/api/stores/intel", params={"q": "thịt bò phi lê"})
    assert r.status_code == 200
    data = r.json()
    assert data["matches"][0]["ingredient"]["id"] == "beef_tenderloin"
    assert data["live"]["ingredient_id"] == "beef_tenderloin"
    assert data["live"]["deals"][0]["price"] == 12.99
    assert queries == ["beef tenderloin"]


async def test_new_cut_has_no_invented_price(monkeypatch):
    async def no_deals(*args):
        return []
    monkeypatch.setattr(live_prices, "fetch_live_oc_deals", no_deals)
    result = item_intel("ức gà")[0]
    assert result["ingredient"]["local_price"] is None
    assert result["ingredient"]["weee_price"] is None
    assert "No price benchmark" in result["basis"]
    live = await live_prices.live_check("ức gà")
    assert live["ingredient_id"] == "chicken_breast"
    assert live["deals"] == []
