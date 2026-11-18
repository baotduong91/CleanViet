"""Orange County live circular prices via Flipp (cached 12h)."""

from __future__ import annotations

import json
import asyncio
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

from app.services.ingredients import INGREDIENTS, normalize
from app.services.ingredient_search import search_ingredients, flyer_search_term

FLIPP_URL = "https://backflipp.wishabi.com/flipp/items/search"
CACHE_TTL = 12 * 3600
MERCHANTS = (
    "99 ranch",
    "h mart",
    "aldi",
    "sprouts",
    "stater bros",
    "smart & final",
    "costco",
)
ZIPS = ("92683", "92805")
DB_PATH = Path(__file__).resolve().parents[2] / "data" / "live_prices.sqlite"

_memory: dict[str, tuple[float, list[dict]]] = {}


def _db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS flipp_cache (cache_key TEXT PRIMARY KEY, fetched_at REAL, payload TEXT)"
    )
    conn.commit()
    return conn


def _cache_get(key: str) -> list[dict] | None:
    now = time.time()
    if key in _memory:
        ts, rows = _memory[key]
        if now - ts < CACHE_TTL:
            return rows
    conn = _db()
    row = conn.execute(
        "SELECT fetched_at, payload FROM flipp_cache WHERE cache_key=?", (key,)
    ).fetchone()
    conn.close()
    if not row:
        return None
    fetched_at, payload = row
    if now - fetched_at >= CACHE_TTL:
        return None
    rows = json.loads(payload)
    _memory[key] = (fetched_at, rows)
    return rows


def _cache_set(key: str, rows: list[dict]) -> None:
    now = time.time()
    _memory[key] = (now, rows)
    conn = _db()
    conn.execute(
        "INSERT OR REPLACE INTO flipp_cache(cache_key,fetched_at,payload) VALUES(?,?,?)",
        (key, now, json.dumps(rows)),
    )
    conn.commit()
    conn.close()


async def _fetch_flipp(query: str, zip_code: str) -> list[dict]:
    params = {"locale": "en-us", "q": query, "postal_code": zip_code}
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(FLIPP_URL, params=params)
        resp.raise_for_status()
        data = resp.json()
    items = data.get("items") or data.get("ecom_items") or []
    deals: list[dict] = []
    for item in items:
        name = str(item.get("name") or item.get("description") or "")
        merchant = str(item.get("merchant") or item.get("store_name") or "")
        merchant_l = merchant.lower()
        if merchant_l and not any(m in merchant_l for m in MERCHANTS):
            continue
        price = item.get("current_price") or item.get("price")
        if price is None:
            continue
        valid = str(item.get("valid_to") or item.get("valid_until") or "")[:10]
        deals.append(
            {
                "name": name,
                "merchant": merchant or "Local circular",
                "price": float(price),
                "valid_to": valid,
                "zip_code": zip_code,
                "url": item.get("url") or item.get("item_url") or item.get("flyer_url"),
            }
        )
    return deals


async def fetch_live_oc_deals(query: str, zip_code: str = "92683") -> list[dict]:
    key = f"{normalize(query)}|{zip_code}"
    cached = _cache_get(key)
    if cached is not None:
        return cached
    try:
        rows: list[dict] = []
        for z in {zip_code, *ZIPS}:
            rows.extend(await _fetch_flipp(query, z))
        _cache_set(key, rows)
        return rows
    except (httpx.HTTPError, OSError, json.JSONDecodeError):
        stale = _memory.get(key)
        if stale:
            return stale[1]
        conn = _db()
        row = conn.execute(
            "SELECT payload FROM flipp_cache WHERE cache_key=?", (key,)
        ).fetchone()
        conn.close()
        if row:
            return json.loads(row[0])
        return []


def _baseline_deal(ingredient_id: str) -> dict | None:
    meta = INGREDIENTS.get(ingredient_id)
    if not meta:
        return None
    return {
        "name": meta["name"],
        "merchant": "Street baseline (offline)",
        "price": float(meta["local_price"]),
        "valid_to": "",
        "zip_code": "92683",
        "baseline_fallback": True,
    }


async def live_check(query: str, zip_code: str = "92683") -> dict:
    matches = search_ingredients(query, limit=1)
    ingredient = matches[0] if matches else None
    matched_ingredient = ingredient["id"] if ingredient else None
    search_query = flyer_search_term(ingredient) if ingredient else query.strip()
    try:
        deals = await asyncio.wait_for(fetch_live_oc_deals(search_query, zip_code), timeout=3)
    except TimeoutError:
        deals = []
    if not deals and matched_ingredient:
        fallback = _baseline_deal(matched_ingredient)
        return {
            "query": query,
            "search_query": search_query,
            "cached": False,
            "baseline_fallback": True,
            "deals": [fallback] if fallback else [],
            "ingredient_id": matched_ingredient,
        }
    return {
        "query": query,
        "search_query": search_query,
        "cached": bool(deals),
        "baseline_fallback": not deals,
        "deals": deals[:12],
        "ingredient_id": matched_ingredient,
    }


async def sync_all_staples() -> dict[str, dict]:
    """Bound parallel flyer lookups so one sync completes within 25 seconds."""
    out: dict[str, dict] = {}
    limit = asyncio.Semaphore(4)

    async def lookup(ing_id, meta):
        async with limit:
            deals = await fetch_live_oc_deals(meta["name"], "92683")
        if deals:
            best = min(deals, key=lambda d: d["price"])
            valid = best.get("valid_to") or "not provided"
            out[ing_id] = {
                **best,
                "label": f"Flyer: ${best['price']:.2f} @ {best['merchant']} (Valid thru {valid})",
            }

    try:
        await asyncio.wait_for(
            asyncio.gather(*(lookup(k, v) for k, v in INGREDIENTS.items())),
            timeout=25,
        )
    except TimeoutError:
        pass
    for ing_id, meta in INGREDIENTS.items():
        if ing_id not in out:
            fb = _baseline_deal(ing_id)
            if fb:
                out[ing_id] = {
                    **fb,
                    "label": f"Baseline ${fb['price']:.2f}/{meta['unit']} (no flyer match)",
                }
    return out


def flyer_snapshot() -> dict:
    """Return the last completed flyer check, including offline results."""
    conn = _db()
    row = conn.execute(
        "SELECT payload FROM flipp_cache WHERE cache_key=?", ("__flyer_snapshot__",)
    ).fetchone()
    conn.close()
    return json.loads(row[0]) if row else {"synced_at": None, "deals": {}}


def save_flyer_snapshot(deals: dict) -> dict:
    snapshot = {
        "synced_at": datetime.now(timezone.utc).isoformat(),
        "deals": deals,
        "flyer_count": sum(not d.get("baseline_fallback", False) for d in deals.values()),
        "baseline_count": sum(bool(d.get("baseline_fallback")) for d in deals.values()),
    }
    conn = _db()
    conn.execute(
        "INSERT OR REPLACE INTO flipp_cache(cache_key,fetched_at,payload) VALUES(?,?,?)",
        ("__flyer_snapshot__", time.time(), json.dumps(snapshot)),
    )
    conn.commit()
    conn.close()
    return snapshot
