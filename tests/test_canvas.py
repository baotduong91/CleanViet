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
    assert not parse_dish("An entirely unfamiliar family specialty").ingredients
    assert "beef" in {
        i.ingredient_id for i in parse_dish("Pasta bolognese").ingredients
    }
    assert "eggs" not in {
        i.ingredient_id for i in parse_dish("Bún quậy mực trứng").ingredients
    }
    assert "pin bones" in parse_dish("Salmon").toddler_tip


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
