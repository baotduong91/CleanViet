"""Local-first Vietnamese cookbook search with bounded concurrent JSON providers."""

import asyncio
from collections import OrderedDict
from contextlib import contextmanager
import html
import json
from pathlib import Path
import re
import sqlite3
import time
from urllib.parse import urlsplit

import httpx

from app.services.cookbook_catalog import DISHES
from app.services.ingredients import normalize
from app.services.icon_parser import resolve_dish_icon

SOURCES = (
    ("Helen's Recipes", "https://helensrecipes.com/wp-json/wp/v2/posts"),
    ("Hungry Huy", "https://www.hungryhuy.com/wp-json/wp/v2/posts"),
    ("Vicky Pham", "https://vickypham.com/wp-json/wp/v2/posts"),
)
TTL = 24 * 3600
DB_PATH = Path(__file__).resolve().parents[2] / "data" / "recipe_search.sqlite"
CACHE_LIMIT = 256
_memory = OrderedDict()


def search_allowed(query: str) -> bool:
    words = query.strip().split()
    return len(words) >= 2 and len(words[1]) >= 2


def clean_title(title: str) -> str:
    title = re.sub(r"<[^>]*>", "", html.unescape(title))
    title = re.sub(r"^(?:(?:easy|authentic|best|traditional|homemade|quick)\s+)+", "", title, flags=re.I)
    title = re.sub(r"\s+(?:recipe|recipes)\b", "", title, flags=re.I)
    title = re.sub(r"\s*[|–—]\s*(?:Helen.?s Recipes|Hungry Huy|Vicky Pham).*$", "", title, flags=re.I)
    return re.sub(r"\s+", " ", title.replace("!", "")).strip(" -")[:200]


def suggestion(title, *, source_domain="CleanViet Catalog", source_url=None, catalog_id=None):
    title = clean_title(title)
    return dict(title_clean=title, **resolve_dish_icon(title),
                source_domain=source_domain, source_url=source_url, catalog_id=catalog_id)


def _trigrams(text):
    return {text[i:i + 3] for i in range(max(0, len(text) - 2))}


def local_matches(query: str) -> list[dict]:
    q = " ".join(normalize(query).split())
    if not q:
        return []
    query_grams = _trigrams(q)
    ranked = []
    for dish in DISHES:
        title = normalize(dish.display_name)
        blob = dish.search_blob()
        score = 0
        if title.startswith(q):
            score = 100
        elif q in blob or all(w in blob.split() for w in q.split()):
            score = 80
        elif len(q.split()) >= 2 and query_grams:
            overlap = len(query_grams & _trigrams(blob)) / len(query_grams)
            if overlap >= 0.65:
                score = overlap * 50
        if score:
            ranked.append((score, dish))
    ranked.sort(key=lambda row: (-row[0], row[1].id))
    return [suggestion(d.display_name, catalog_id=d.id) for _, d in ranked[:8]]


@contextmanager
def _db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("CREATE TABLE IF NOT EXISTS autocomplete (query TEXT PRIMARY KEY, fetched REAL, payload TEXT)")
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def _remember(key, stamp, items):
    _memory[key] = (stamp, items)
    _memory.move_to_end(key)
    while len(_memory) > CACHE_LIMIT:
        _memory.popitem(last=False)


def _cached(key):
    row = _memory.get(key)
    if row and time.time() - row[0] < TTL:
        _memory.move_to_end(key)
        return row[1]
    try:
        with _db() as conn:
            row = conn.execute("SELECT fetched,payload FROM autocomplete WHERE query=?", (key,)).fetchone()
        if row and time.time() - row[0] < TTL:
            items = json.loads(row[1])
            _remember(key, row[0], items)
            return items
    except (OSError, sqlite3.Error, ValueError):
        pass
    return None


def _cache(key, items):
    stamp = time.time()
    _remember(key, stamp, items)
    try:
        with _db() as conn:
            conn.execute("INSERT OR REPLACE INTO autocomplete VALUES(?,?,?)", (key, stamp, json.dumps(items)))
            conn.execute("DELETE FROM autocomplete WHERE query NOT IN (SELECT query FROM autocomplete ORDER BY fetched DESC LIMIT 256)")
    except (OSError, sqlite3.Error):
        pass


async def _search_source(client, name, url, query):
    try:
        async with client.stream("GET", url, params={
            "search": query, "per_page": 5, "_fields": "title,link,yoast_head_json",
        }) as response:
            response.raise_for_status()
            chunks = []
            size = 0
            async for chunk in response.aiter_bytes():
                size += len(chunk)
                if size > 1024 * 1024:
                    return []
                chunks.append(chunk)
        posts = json.loads(b"".join(chunks))
        if not isinstance(posts, list):
            return []
        results = []
        for post in posts[:5]:
            if not isinstance(post, dict):
                continue
            title = post.get("title")
            title = title.get("rendered") if isinstance(title, dict) else title
            link = post.get("link")
            if not isinstance(title, str) or not isinstance(link, str):
                continue
            parsed = urlsplit(link)
            if parsed.scheme != "https" or parsed.hostname != urlsplit(url).hostname or parsed.username or parsed.password:
                continue
            title_words = normalize(clean_title(title)).split()
            if not all(any(word.startswith(token) for word in title_words) for token in normalize(query).split()):
                continue
            results.append(suggestion(title, source_domain=name, source_url=link))
        return results
    except (httpx.HTTPError, ValueError, TypeError):
        return []


async def autocomplete(query: str) -> dict:
    local = local_matches(query)
    if not search_allowed(query):
        return {"suggestions": local, "live_enabled": False, "cached": False}
    key = " ".join(normalize(query).split())
    cached = _cached(key)
    if cached is not None:
        return {"suggestions": cached, "live_enabled": True, "cached": True}
    async with httpx.AsyncClient(timeout=1.2, follow_redirects=False) as client:
        async def bounded(name, url):
            try:
                return await asyncio.wait_for(_search_source(client, name, url, query), 1.2)
            except TimeoutError:
                return []
        groups = await asyncio.gather(*(bounded(name, url) for name, url in SOURCES))
    combined = []
    seen = set()
    for row in [*local, *(item for group in groups for item in group)]:
        identity = row["source_url"] or row["catalog_id"]
        if identity not in seen:
            combined.append(row)
            seen.add(identity)
    combined = combined[:20]
    _cache(key, combined)
    return {"suggestions": combined[:20], "live_enabled": True, "cached": False}
