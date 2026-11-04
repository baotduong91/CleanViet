"""Download and cache hero dish photos from recipe pages."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx

from app.services.ingredients import normalize

DISH_IMAGE_DIR = Path(__file__).resolve().parents[2] / "data" / "dish_images"
MAX_BYTES = 5 * 1024 * 1024
SKIP_IN_URL = ("logo", "icon", "avatar", "gravatar", "pixel", "emoji", "badge", "spacer")


def _http_image_url(url: str) -> bool:
    low = url.strip().lower()
    if not low.startswith(("http://", "https://")):
        return False
    if low.endswith(".svg") or "image/svg" in low:
        return False
    return True


def _abs_url(base: str, link: str) -> str:
    return urljoin(base, link.strip())


def _image_candidates_from_recipe(recipe: dict, page_url: str) -> list[tuple[int, str]]:
    out: list[tuple[int, str]] = []
    raw = recipe.get("image")
    if isinstance(raw, str):
        abs_url = _abs_url(page_url, raw)
        if _http_image_url(abs_url):
            out.append((800, abs_url))
    elif isinstance(raw, list):
        for item in raw:
            if isinstance(item, str):
                abs_url = _abs_url(page_url, item)
                if _http_image_url(abs_url):
                    out.append((600, abs_url))
            elif isinstance(item, dict):
                url = item.get("url") or item.get("contentUrl")
                if not url:
                    continue
                width = 0
                try:
                    width = int(item.get("width") or item.get("contentWidth") or 0)
                except (TypeError, ValueError):
                    width = 0
                abs_url = _abs_url(page_url, str(url))
                if _http_image_url(abs_url):
                    out.append((width, abs_url))
    elif isinstance(raw, dict):
        url = raw.get("url") or raw.get("contentUrl")
        if url:
            try:
                width = int(raw.get("width") or 0)
            except (TypeError, ValueError):
                width = 0
            abs_url = _abs_url(page_url, str(url))
            if _http_image_url(abs_url):
                out.append((width, abs_url))
    return out


def _og_image(html: str, page_url: str) -> str | None:
    for pattern in (
        r'<meta[^>]+property=["\']og:image(?::secure_url)?["\'][^>]+content=["\']([^"\']+)',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image',
    ):
        match = re.search(pattern, html, re.I)
        if match:
            og = _abs_url(page_url, match.group(1))
            if _http_image_url(og):
                return og
    return None


def _content_images(html: str, page_url: str) -> list[tuple[int, str]]:
    found: list[tuple[int, str]] = []
    for tag in re.findall(r"<img\b[^>]*>", html, re.I):
        src_m = re.search(r'\bsrc=["\']([^"\']+)["\']', tag, re.I)
        if not src_m:
            continue
        src = _abs_url(page_url, src_m.group(1))
        if not _http_image_url(src):
            continue
        low = src.lower()
        if any(skip in low for skip in SKIP_IN_URL):
            continue
        if low.endswith((".svg", ".gif")):
            continue
        score = 0
        w_m = re.search(r'\bwidth=["\']?(\d+)', tag, re.I)
        h_m = re.search(r'\bheight=["\']?(\d+)', tag, re.I)
        if w_m:
            score += int(w_m.group(1))
        if h_m:
            score += int(h_m.group(1))
        if "wp-content" in low or "recipe" in low or "upload" in low:
            score += 400
        found.append((score, src))
    return found


def best_dish_photo_url(recipe: dict | None, html: str, page_url: str) -> str | None:
    """Pick the most complete hero image: JSON-LD Recipe > og:image > largest in-content img."""
    candidates: list[tuple[int, str]] = []
    if recipe:
        candidates.extend(_image_candidates_from_recipe(recipe, page_url))
    og = _og_image(html, page_url)
    if og:
        candidates.append((900, og))
    candidates.extend(_content_images(html, page_url))
    if not candidates:
        return None
    candidates.sort(key=lambda pair: pair[0], reverse=True)
    return candidates[0][1]


def local_image_path(dish_key: str) -> Path:
    DISH_IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    return DISH_IMAGE_DIR / f"{dish_key}.jpg"


def public_image_url(dish_key: str) -> str:
    return f"/media/dishes/{dish_key}.jpg"


async def cache_dish_photo(source_url: str, dish_name: str) -> str | None:
    """Download image bytes to data/dish_images/{key}.jpg; return served URL."""
    if not source_url or not source_url.startswith("http"):
        return None
    key = normalize(dish_name)[:120].replace(" ", "_") or "dish"
    dest = local_image_path(key)
    headers = {"User-Agent": "CleanViet/2.0 dish-photo"}
    try:
        async with httpx.AsyncClient(timeout=25, follow_redirects=True) as client:
            resp = await client.get(source_url, headers=headers)
            resp.raise_for_status()
            ctype = (resp.headers.get("content-type") or "").split(";")[0].lower()
            if not ctype.startswith("image/"):
                return None
            data = resp.content
            if len(data) > MAX_BYTES or len(data) < 500:
                return None
            ext = ".jpg"
            if "png" in ctype:
                ext = ".png"
            elif "webp" in ctype:
                ext = ".webp"
            dest = DISH_IMAGE_DIR / f"{key}{ext}"
            dest.write_bytes(data)
            return f"/media/dishes/{key}{ext}"
    except (httpx.HTTPError, OSError, ValueError):
        return None


def remove_cached_photo(dish_key: str) -> None:
    if not DISH_IMAGE_DIR.exists():
        return
    for path in DISH_IMAGE_DIR.glob(f"{dish_key}.*"):
        path.unlink(missing_ok=True)
