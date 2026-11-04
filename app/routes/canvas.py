import json
from datetime import date
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import session_dependency
from app.services.ingredients import FAVORITES, normalize
from app.services.cookbook_catalog import list_dishes
from app.services.cookbook_store import delete_saved, list_saved, save_dish
from app.services.live_prices import live_check, sync_all_staples
from app.services.parser import ParsedMeal, parse_dish, parsed_from_import
from app.services.dish_photos import cache_dish_photo
from app.services.recipe_import import import_recipe_url
from app.services.recommender import STORES, item_intel, recommend
from app.services.community_insights import fetch_insights

router = APIRouter(prefix="/api")
DB = Depends(session_dependency)


class ParseRequest(BaseModel):
    dish_name: str = Field(min_length=1, max_length=200)


class ImportUrlRequest(BaseModel):
    url: str = Field(min_length=8, max_length=500)


class CanvasMeal(ParsedMeal):
    day: Literal["Monday", "Tuesday", "Wednesday", "Thursday"]


class CanvasPreferences(BaseModel):
    model_config = ConfigDict(extra="forbid")
    lean_mode: bool = False
    pack_lunch: list[bool] = Field(default_factory=lambda: [False, False, False, False])
    homemade_broth: bool = False
    store_mode: bool = False

    @field_validator("pack_lunch")
    @classmethod
    def four_days(cls, v):
        if len(v) != 4:
            raise ValueError("pack_lunch must have four entries (Mon–Thu).")
        return v


class CanvasRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    week_start: date
    revision: int = Field(default=0, ge=0)
    meals: list[CanvasMeal] = Field(min_length=4, max_length=4)
    checked: list[str] = Field(default_factory=list, max_length=200)
    preferences: CanvasPreferences = Field(default_factory=CanvasPreferences)

    @field_validator("week_start")
    @classmethod
    def monday(cls, v):
        if v.weekday() != 0:
            raise ValueError("Choose a Monday.")
        return v

    @field_validator("meals")
    @classmethod
    def days(cls, v):
        if len({m.day for m in v}) != 4:
            raise ValueError("Choose one meal for each Monday–Thursday day.")
        return v


@router.post("/meals/parse-ingredients")
async def parse(body: ParseRequest):
    try:
        return parse_dish(body.dish_name)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.get("/cookbook")
async def cookbook(
    category: str = Query("", max_length=40),
    q: str = Query("", max_length=200),
    session: AsyncSession = DB,
):
    cat = category or None
    dishes = list_dishes(cat, q)
    if cat in (None, "favorites"):
        saved = await list_saved(session, q)
        seen = {normalize(d["display_name"]) for d in dishes}
        for row in saved:
            if normalize(row["display_name"]) not in seen:
                dishes.insert(0, row)
                seen.add(normalize(row["display_name"]))
    return dict(
        dishes=dishes,
        categories=[
            {"id": "favorites", "label": "⭐ Favorites"},
            {"id": "canh_soups", "label": "🥣 Canh / Soups"},
            {"id": "noodle_bowls", "label": "🍜 Bún / Nui"},
            {"id": "steamed_airfry", "label": "🐟 Steamed & Air-Fry"},
            {"id": "stir_fry_savory", "label": "🍚 Stir-Fry & Clean Savory"},
        ],
    )


@router.post("/cookbook/import-url")
async def cookbook_import_preview(body: ImportUrlRequest):
    """Parse URL for preview; does not save until /cookbook/saved."""
    try:
        title, items, note, photo_source = await import_recipe_url(body.url)
        image_url = None
        if photo_source:
            image_url = await cache_dish_photo(photo_source, title)
        return parsed_from_import(title, items, note, image_url)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(502, "Recipe import failed. Try manual entry.") from exc


@router.post("/cookbook/saved")
async def cookbook_save(body: ParsedMeal, session: AsyncSession = DB):
    return await save_dish(session, body)


@router.delete("/cookbook/saved/{dish_key}")
async def cookbook_delete_saved(dish_key: str, session: AsyncSession = DB):
    if not await delete_saved(session, dish_key):
        raise HTTPException(404, "Saved dish not found.")
    return {"ok": True}


@router.get("/prices/live-check")
async def prices_live(q: str = Query(min_length=1, max_length=120), zip_code: str = "92683"):
    return await live_check(q, zip_code)


@router.post("/prices/sync-flyers")
async def prices_sync():
    deals = await sync_all_staples()
    return dict(deals=deals, count=len(deals))


@router.get("/meals/history")
async def history(q: str = Query("", max_length=200), session: AsyncSession = DB):
    rows = (
        (
            await session.execute(
                text(
                    "SELECT dish_name FROM meal_history ORDER BY updated_at DESC LIMIT 200"
                )
            )
        )
        .scalars()
        .all()
    )
    return dict(
        favorites=FAVORITES,
        past_meals=[n for n in rows if normalize(q) in normalize(n)][:20],
    )


@router.put("/canvas")
async def save(body: CanvasRequest, session: AsyncSession = DB):
    await session.execute(text("SELECT pg_advisory_xact_lock(20261103)"))
    revision = (
        await session.execute(
            text("SELECT revision FROM meal_canvases WHERE week_start=:week"),
            {"week": body.week_start},
        )
    ).scalar_one_or_none() or 0
    if revision != body.revision:
        raise HTTPException(
            409, "This week changed in another tab. Reload before saving your changes."
        )
    payload = body.model_dump(mode="json")
    payload["revision"] = revision + 1
    await session.execute(
        text(
            "INSERT INTO meal_canvases(week_start,revision,payload) VALUES(:week,:revision,CAST(:payload AS jsonb)) ON CONFLICT(week_start) DO UPDATE SET revision=EXCLUDED.revision,payload=EXCLUDED.payload,updated_at=now()"
        ),
        {
            "week": body.week_start,
            "revision": revision + 1,
            "payload": json.dumps(payload),
        },
    )
    for meal in body.meals:
        await session.execute(
            text(
                "INSERT INTO meal_history(dish_key,dish_name,payload) VALUES(:key,:name,CAST(:payload AS jsonb)) ON CONFLICT(dish_key) DO UPDATE SET dish_name=EXCLUDED.dish_name,payload=EXCLUDED.payload,updated_at=now()"
            ),
            {
                "key": normalize(meal.dish_name),
                "name": meal.dish_name,
                "payload": meal.model_dump_json(),
            },
        )
    prefs = payload.get("preferences") or {}
    return dict(
        **payload,
        shopping=recommend(payload["meals"], payload["checked"], prefs),
    )


@router.get("/canvas")
async def load(week_start: date, session: AsyncSession = DB):
    payload = (
        await session.execute(
            text("SELECT payload FROM meal_canvases WHERE week_start=:week"),
            {"week": week_start},
        )
    ).scalar_one_or_none()
    if payload is None:
        return dict(
            week_start=str(week_start), revision=0, meals=[], checked=[], shopping=None
        )
    prefs = payload.get("preferences") or {}
    return dict(
        **payload,
        shopping=recommend(payload["meals"], payload.get("checked", []), prefs),
    )


@router.get("/stores/intel")
async def intel(q: str = Query(min_length=1, max_length=120)):
    live = await live_check(q)
    return dict(matches=item_intel(q), live=live)


@router.get("/stores/{store_id}/community")
async def community(store_id: str):
    if store_id not in STORES:
        raise HTTPException(404, "Unknown store specialty.")
    return await fetch_insights(store_id)
