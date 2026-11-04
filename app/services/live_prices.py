"""Orange County live circular prices via Flipp (cached 12h)."""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

import httpx

from app.services.ingredients import INGREDIENTS, normalize

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
    qn = normalize(query)
    deals = await fetch_live_oc_deals(query, zip_code)
    matched_ingredient = None
    for key, meta in INGREDIENTS.items():
        if qn in normalize(meta["name"]) or any(qn in a or a in qn for a in meta["aliases"]):
            matched_ingredient = key
            break
    if not deals and matched_ingredient:
        fallback = _baseline_deal(matched_ingredient)
        return {
            "query": query,
            "cached": False,
            "baseline_fallback": True,
            "deals": [fallback] if fallback else [],
            "ingredient_id": matched_ingredient,
        }
    return {
        "query": query,
        "cached": bool(deals),
        "baseline_fallback": not deals,
        "deals": deals[:12],
        "ingredient_id": matched_ingredient,
    }


async def sync_all_staples() -> dict[str, dict]:
    """Refresh flyer matches for common shopping staples."""
    out: dict[str, dict] = {}
    for ing_id, meta in INGREDIENTS.items():
        deals = await fetch_live_oc_deals(meta["name"], "92683")
        if not deals:
            fb = _baseline_deal(ing_id)
            if fb:
                out[ing_id] = {
                    **fb,
                    "label": f"Baseline ${fb['price']:.2f}/{meta['unit']} (offline cache)",
                }
            continue
        best = min(deals, key=lambda d: d["price"])
        valid = best.get("valid_to") or "this week"
        out[ing_id] = {
            **best,
            "label": f"🔥 Live Flyer Sale: ${best['price']:.2f} @ {best['merchant']} (Valid thru {valid})",
        }
    return out
