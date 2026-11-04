"""Import recipe ingredients from supported blog URLs (JSON-LD Recipe)."""

from __future__ import annotations

import html
import json
import re
from urllib.parse import urlparse

import httpx

from app.services.ingredients import INGREDIENTS, normalize
from app.services.parser import GroceryItem

ALLOWED_HOSTS = (
    "hungryhuy.com",
    "www.hungryhuy.com",
    "helenrecipes.com",
    "www.helenrecipes.com",
    "vickypham.com",
    "www.vickypham.com",
)


def _host_allowed(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    return any(
        host == domain or host.endswith("." + domain)
        for domain in ("hungryhuy.com", "helenrecipes.com", "vickypham.com")
    )


def _extract_recipe_ld(html: str) -> dict | None:
    for block in re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html,
        re.I | re.S,
    ):
        try:
            data = json.loads(block.strip())
        except json.JSONDecodeError:
            continue
        nodes = data if isinstance(data, list) else [data]
        for node in nodes:
            if isinstance(node, dict) and node.get("@type") == "Recipe":
                return node
            if isinstance(node, dict) and "@graph" in node:
                for g in node["@graph"]:
                    if isinstance(g, dict) and g.get("@type") == "Recipe":
                        return g
    return None


def _match_ingredient(text: str) -> str | None:
    n = normalize(text)
    for key, item in INGREDIENTS.items():
        if normalize(item["name"]) in n:
            return key
        if any(a in n for a in item["aliases"]):
            return key
    return None


async def import_recipe_url(
    url: str,
) -> tuple[str, list[GroceryItem], str, str | None]:
    parsed = urlparse(url.strip())
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError("Paste a valid http(s) recipe URL.")
    if not _host_allowed(url):
        raise ValueError(
            "Supported sites: Hungry Huy, Helen Recipes, and Vicky Pham blogs."
        )
    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        resp = await client.get(url, headers={"User-Agent": "CleanViet/2.0 recipe-import"})
        resp.raise_for_status()
        page_html = resp.text
    recipe = _extract_recipe_ld(page_html)
    if not recipe:
        raise ValueError("No Recipe JSON-LD found on that page.")
    title = html.unescape(str(recipe.get("name") or "Imported recipe"))[:200]
    raw_ings = recipe.get("recipeIngredient") or recipe.get("ingredients") or []
    items: list[GroceryItem] = []
    seen: set[str] = set()
    for line in raw_ings:
        text = str(line)
        kid = _match_ingredient(text)
        if not kid or kid in seen:
            continue
        seen.add(kid)
        meta = INGREDIENTS[kid]
        items.append(
            GroceryItem(
                name=meta["name"],
                quantity=float(meta["quantity"]),
                unit=meta["unit"],
                ingredient_id=kid,
            )
        )
    if not items:
        raise ValueError("Could not map recipe ingredients to pantry items.")
    note = f"Imported from {parsed.netloc}; review quantities for your family."
    from app.services.dish_photos import best_dish_photo_url

    photo_source = best_dish_photo_url(recipe, page_html, url)
    return title, items, note, photo_source
