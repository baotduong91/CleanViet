from datetime import datetime, timezone
from decimal import Decimal
import os
import pytest
import httpx
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import text
from app.main import app
from app.db import session_dependency
from app.routes.canvas import CanvasRequest
from app.services.parser import parse_dish
from app.services.recommender import recommend, item_intel
from app.services.community_insights import analyze_reviews, fetch_insights
from pydantic import ValidationError


def test_examples_and_unknown_dishes():
    for name in [
        "Súp nui tôm thịt",
        "Air fry salmon with broccoli & rice",
        "Bún quậy Phú Quốc",
        "Pasta bolognese",
        "Steamed chicken ginger scallion",
    ]:
        assert parse_dish(name).ingredients
    assert parse_dish("An entirely unfamiliar family specialty").ingredients
    assert "beef" in {
        i.ingredient_id for i in parse_dish("Pasta bolognese").ingredients
    }
    assert "eggs" not in {
        i.ingredient_id for i in parse_dish("Bún quậy mực trứng").ingredients
    }
    assert "pin bones" in parse_dish("Salmon").toddler_tip.lower()
    assert "1cm bites" in parse_dish("Súp nui tôm thịt").toddler_tip


def test_dry_pasta_merge_and_broth_arbitrage():
    meals = [
        parse_dish("Pasta bolognese").model_dump(),
        parse_dish("Súp nui tôm thịt").model_dump(),
    ]
    result = recommend(meals)
    items = [i for r in result["routes"] for s in r["stores"] for i in s["items"]]
    pasta = next(i for i in items if i["name"] == "Dry pasta / nui")
    assert pasta["quantity"] == "1.00"
    with_broth = recommend(meals, preferences={"homemade_broth": True})
    assert Decimal(with_broth["homemade_broth_savings"]) > 0
    assert Decimal(with_broth["estimated_cost"]) < Decimal(result["estimated_cost"])


def test_aggregation_covered_unknown_and_units():
    meals = [parse_dish("salmon broccoli").model_dump()] * 2
    result = recommend(meals)
    items = [i for r in result["routes"] for s in r["stores"] for i in s["items"]]
    assert next(i for i in items if i["id"] == "salmon|lb")["quantity"] == "2.50"
    assert Decimal(result["estimated_savings"]) == Decimal(
        result["estimated_weee"]
    ) - Decimal(result["estimated_cost"])
    covered = recommend(meals, [i["id"] for i in items])
    assert covered["estimated_cost"] == "0.00"
    result = recommend(
        [{"ingredients": [{"name": "Custom spice", "unit": "each", "quantity": 1}]}]
    )
    assert result["unpriced_items"] == 1
    result = recommend(
        [
            {
                "ingredients": [
                    {
                        "ingredient_id": "salmon",
                        "name": "salmon",
                        "unit": "L",
                        "quantity": 1,
                    }
                ]
            }
        ]
    )
    assert result["unpriced_items"] == 1


def test_intel_accent_matching():
    assert item_intel("Mực trứng")[0]["store"]["id"] == "seafood"
    assert len(item_intel("Mực trứng")) == 1
    assert item_intel("Nấm đùi gà")[0]["store"]["id"] == "greens"


def test_reviews_recent_relevant_and_attributed():
    now = datetime(2026, 11, 2, tzinfo=timezone.utc)
    reviews = [
        {
            "publishTime": "2026-10-30T00:00:00Z",
            "text": {"text": "Fresh fish and produce looked good"},
            "authorAttribution": {"displayName": "Reviewer"},
        },
        {"publishTime": "2025-10-30T00:00:00Z", "text": {"text": "fresh fish"}},
        {"publishTime": "bad", "text": {"text": "squid"}},
    ]
    result = analyze_reviews(reviews, now)
    assert len(result) == 1
    assert result[0]["author"] == "Reviewer"


async def test_no_key_is_honest(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "google_places_api_key", "")
    assert (await fetch_insights("seafood"))["status"] == "not_configured"


def test_schedule_rejects_friday_duplicate_and_invalid_quantities():
    meals = [
        parse_dish("salmon").model_dump() | {"day": d}
        for d in ["Monday", "Tuesday", "Wednesday", "Thursday"]
    ]
    CanvasRequest(week_start="2026-11-02", meals=meals)
    meals[-1]["day"] = "Friday"
    with pytest.raises(ValidationError):
        CanvasRequest(week_start="2026-11-02", meals=meals)
    with pytest.raises(ValueError):
        parse_dish(" ")


@pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"), reason="Dedicated test DB required"
)
async def test_persist_conflict_history_checks_and_security():
    url = os.environ["TEST_DATABASE_URL"]
    assert url.endswith("/cleanviet_test")
    engine = create_async_engine(url)
    sessions = async_sessionmaker(engine)
    async with engine.begin() as c:
        await c.execute(text("TRUNCATE meal_canvases,meal_history"))

    async def dependency():
        async with sessions() as s:
            async with s.begin():
                yield s

    app.dependency_overrides[session_dependency] = dependency
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://testserver"
        ) as c:
            body = {
                "week_start": "2026-11-02",
                "revision": 0,
                "meals": [
                    parse_dish("Pasta bolognese").model_dump() | {"day": d}
                    for d in ["Monday", "Tuesday", "Wednesday", "Thursday"]
                ],
            }
            r = await c.put("/api/canvas", json=body)
            assert r.status_code == 200, r.text
            assert r.json()["revision"] == 1
            assert (await c.put("/api/canvas", json=body)).status_code == 409
            body["revision"] = 1
            body["checked"] = ["pasta|lb"]
            assert (await c.put("/api/canvas", json=body)).status_code == 200
            loaded = (await c.get("/api/canvas?week_start=2026-11-02")).json()
            assert loaded["checked"] == ["pasta|lb"]
            assert (
                "Pasta bolognese"
                in (await c.get("/api/meals/history")).json()["past_meals"]
            )
            assert (
                await c.post(
                    "/api/meals/parse-ingredients",
                    json={"dish_name": "salmon"},
                    headers={"Origin": "https://evil.example"},
                )
            ).status_code == 403
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


def test_cookbook_accent_free_queries():
    for query in ("canh bau tom", "ga hap la chanh", "bun moc"):
        meal = parse_dish(query)
        assert meal.ingredients, f"expected ingredients for {query}"
        assert meal.toddler_tip
    assert "1cm" in parse_dish("canh bau tom").toddler_tip or parse_dish(
        "canh bau tom"
    ).toddler_tip


async def test_live_prices_offline_baseline(monkeypatch):
    from app.services import live_prices

    async def fail_fetch(*_a, **_k):
        raise OSError("offline")

    monkeypatch.setattr(live_prices, "_fetch_flipp", fail_fetch)
    live_prices._memory.clear()
    result = await live_prices.live_check("shrimp", "92683")
    assert result["baseline_fallback"]
    assert result["deals"]


def test_recipe_image_picker_prefers_largest_json_ld():
    from app.services.dish_photos import best_dish_photo_url

    recipe = {
        "image": [
            {"@type": "ImageObject", "url": "https://cdn.example/small.jpg", "width": 400},
            {"@type": "ImageObject", "url": "https://cdn.example/hero.jpg", "width": 1600},
        ]
    }
    url = best_dish_photo_url(recipe, "<html></html>", "https://hungryhuy.com/recipe")
    assert url == "https://cdn.example/hero.jpg"


def test_recipe_image_picker_skips_data_uri_placeholders():
    from app.services.dish_photos import best_dish_photo_url

    recipe = {"image": "data:image/svg+xml;base64,PHN2Zy8+"}
    html = '<meta property="og:image" content="https://cdn.example/og.jpg" />'
    url = best_dish_photo_url(recipe, html, "https://hungryhuy.com/recipe")
    assert url == "https://cdn.example/og.jpg"


def test_cookbook_catalog_size():
    from app.services.cookbook_catalog import DISHES

    assert len(DISHES) >= 40


def test_vercel_settings_normalize_postgres_and_use_exact_hosts():
    from app.config import Settings

    settings = Settings(
        _env_file=None,
        database_url="postgresql://example:example@db.example.net/cleanviet?sslmode=require",
        vercel_url="cleanviet-preview.example.vercel.app",
        vercel_project_production_url="cleanviet.example.vercel.app",
    )
    assert settings.database_url.startswith("postgresql+asyncpg://")
    assert "cleanviet-preview.example.vercel.app" in settings.trusted_hosts
    assert "cleanviet.example.vercel.app" in settings.trusted_hosts
    assert "attacker.example" not in settings.trusted_hosts
    assert "*" not in settings.trusted_hosts


async def test_flyer_snapshot_persists_and_exposes_item_urls(monkeypatch, tmp_path):
    from app.services import live_prices
    monkeypatch.setattr(live_prices, "DB_PATH", tmp_path / "prices.sqlite")
    assert live_prices.flyer_snapshot()["synced_at"] is None
    deals = {
        "salmon": {"price": 7.99, "url": "https://example.com/flyer"},
        "squid": {"price": 8.99, "baseline_fallback": True},
    }
    saved = live_prices.save_flyer_snapshot(deals)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
        result = await client.get("/api/prices/flyer-status")
    assert result.status_code == 200
    assert result.json() == saved
    assert saved["flyer_count"] == saved["baseline_count"] == 1
    assert saved["deals"]["salmon"]["url"] == "https://example.com/flyer"


async def test_review_fallback_has_maps_link(monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "google_places_api_key", "")
    result = await fetch_insights("seafood")
    assert result["status"] == "not_configured"
    assert result["url"].startswith("https://www.google.com/maps/search/")
    assert "Thuan" in result["url"]


async def test_sync_snapshot_api_includes_baseline_and_flyer(monkeypatch, tmp_path):
    from app.services import live_prices
    monkeypatch.setattr(live_prices, "DB_PATH", tmp_path / "prices.sqlite")
    async def deals(query, *_args):
        if "salmon" in query.lower():
            return [{"price": 7.99, "merchant": "Aldi", "url": "https://example.com/salmon"}]
        return []
    monkeypatch.setattr(live_prices, "fetch_live_oc_deals", deals)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
        r = await client.post("/api/prices/sync-flyers")
        assert r.status_code == 200
        data = r.json()
        assert data["synced_at"]
        assert data["flyer_count"] == 1
        assert data["baseline_count"] > 0
        assert data["deals"]["salmon"]["url"] == "https://example.com/salmon"
        assert (await client.get("/api/prices/flyer-status")).json()["synced_at"] == data["synced_at"]
