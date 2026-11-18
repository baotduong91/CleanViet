"""Import recipe ingredients from supported blog URLs (JSON-LD Recipe)."""

from __future__ import annotations

import html
import json
import re
from fractions import Fraction
from html.parser import HTMLParser
import unicodedata
from urllib.parse import urlparse

from app.services.remote_fetch import fetch_public

from app.services.ingredients import INGREDIENTS, normalize
from app.services.parser import GroceryItem

ALLOWED_HOSTS = (
    "helensrecipes.com",
    "www.helensrecipes.com",
    "hungryhuy.com",
    "www.hungryhuy.com",
    "helenrecipes.com",
    "www.helenrecipes.com",
    "vickypham.com",
    "www.vickypham.com",
)


class _RecipeScripts(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.blocks = []
        self.collect = False

    def handle_starttag(self, tag, attrs):
        self.collect = tag == "script" and dict(attrs).get("type", "").lower() == "application/ld+json"
        if self.collect:
            self.blocks.append("")

    def handle_data(self, data):
        if self.collect:
            self.blocks[-1] += data

    def handle_endtag(self, tag):
        if tag == "script":
            self.collect = False


def _extract_recipe_ld(page: str) -> dict | None:
    parser = _RecipeScripts()
    parser.feed(page)
    def find(node):
        if isinstance(node, list):
            return next((result for child in node if (result := find(child))), None)
        if not isinstance(node, dict):
            return None
        types = node.get("@type", [])
        types = [types] if isinstance(types, str) else types
        if isinstance(types, list) and any(t in {"Recipe", "https://schema.org/Recipe", "http://schema.org/Recipe"} for t in types if isinstance(t, str)):
            return node
        return find(node.get("@graph"))
    for block in parser.blocks:
        try:
            result = find(json.loads(block.strip()))
        except json.JSONDecodeError:
            continue
        if result:
            return result
    return None


def _match_ingredient(text: str) -> str | None:
    n = " " + normalize(text) + " "
    # Broths and condiments must never become their source meat or fish.
    if any(" " + word + " " in n for word in ("broth", "stock", "nuoc dung")):
        return "broth"
    if any(" " + word + " " in n for word in ("sauce", "nuoc mam", "paste sauce")):
        return None
    matches = []
    for key, item in INGREDIENTS.items():
        for alias in [item["name"], *item["aliases"]]:
            alias = normalize(alias)
            if alias and " " + alias + " " in n:
                matches.append((len(alias), key))
    return max(matches)[1] if matches else None


def _source_item(line: str) -> GroceryItem:
    """Convert explicit mass/volume units, preserving other source amounts for review."""
    kid = _match_ingredient(line)
    text = unicodedata.normalize("NFKC", line).replace("⁄", "/")
    # NFKC writes mixed unicode fractions as 11/2, so separate them first.
    text = re.sub(r"(\d)([¼½¾⅓⅔⅛⅜⅝⅞])", r"\1 \2", line)
    text = unicodedata.normalize("NFKC", text).replace("⁄", "/")
    match = re.match(r"^\s*(\d+\s+\d+/\d+|\d+/\d+|\d+(?:\.\d+)?)\s*(pounds?|lbs?\.?|ounces?|oz\.?|kilograms?|kg|grams?|g|liters?|litres?|l|milliliters?|ml)\b", text, re.I)
    if match:
        try:
            qty = sum(float(Fraction(part)) for part in match[1].split())
        except (ValueError, ZeroDivisionError):
            match = None
    if match and qty > 0:
        unit = match[2].lower().rstrip(".")
        if unit in {"l", "liter", "liters", "litre", "litres", "ml", "milliliter", "milliliters"}:
            qty *= 0.001 if unit in {"ml", "milliliter", "milliliters"} else 1
            target = "L"
        else:
            factor = 1
            if unit in {"oz", "ounce", "ounces"}:
                factor = 1 / 16
            elif unit in {"g", "gram", "grams"}:
                factor = 1 / 453.59237
            elif unit in {"kg", "kilogram", "kilograms"}:
                factor = 1000 / 453.59237
            qty *= factor
            target = "lb"
        if qty <= 1000:
            return GroceryItem(name=INGREDIENTS[kid]["name"] if kid else line[:120],
                               quantity=qty, unit=target, ingredient_id=kid)
    # Keep unsupported measures visible and unpriced instead of inventing a conversion.
    return GroceryItem(name=line[:120], quantity=1, unit="each")


async def import_recipe_url(
    url: str,
    family_servings: float | None = None,
) -> tuple[str, list[GroceryItem], str, str | None]:
    parsed = urlparse(url.strip())
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError("Paste a valid http(s) recipe URL.")
    resp = await fetch_public(url.strip(), allowed_hosts=ALLOWED_HOSTS)
    page_html = resp.text
    recipe = _extract_recipe_ld(page_html)
    if not recipe:
        raise ValueError("No Recipe JSON-LD found on that page.")
    title = html.unescape(str(recipe.get("name") or "Imported recipe"))[:200]
    raw_ings = recipe.get("recipeIngredient") or recipe.get("ingredients") or []
    if isinstance(raw_ings, str):
        raw_ings = [raw_ings]
    if not isinstance(raw_ings, list) or not raw_ings:
        raise ValueError("Recipe has no ingredient lines.")
    lines = [html.unescape(line).strip() for line in raw_ings if isinstance(line, str) and line.strip()]
    if not lines or len(lines) > 40:
        raise ValueError("Import requires between 1 and 40 ingredient lines.")
    items = [_source_item(line) for line in lines]
    family_note = ""
    if family_servings is not None:
        raw_yield = recipe.get("recipeYield", "")
        if isinstance(raw_yield, list):
            raw_yield = raw_yield[0] if raw_yield else ""
        yield_match = re.search(r"\d+(?:\.\d+)?", str(raw_yield))
        servings = float(yield_match[0]) if yield_match else 0
        adjusted = []
        for line, item in zip(lines, items):
            kid = _match_ingredient(line)
            if item.ingredient_id and servings > 0:
                item = item.model_copy(update={"quantity": min(1000, item.quantity * family_servings / servings)})
            elif kid:
                meta = INGREDIENTS[kid]
                item = GroceryItem(name=meta["name"], quantity=meta["quantity"], unit=meta["unit"], ingredient_id=kid)
            adjusted.append(item)
        items = adjusted
        family_note = " Weights scaled to 2 adults + toddler where yield is available; unsupported measures use family estimates. Review quantities."

    note = (
        f"Imported from {parsed.netloc}. Source recipe quantities are not scaled to your family. "
        "Weight and volume measures are converted to lb/L. Other lines retain their source "
        "amount in the name as one unpriced entry; review before shopping."
    )
    from app.services.dish_photos import best_dish_photo_url

    if family_note:
        note = f"Imported from {parsed.netloc}." + family_note
    photo_source = best_dish_photo_url(recipe, page_html, url)
    return title, items, note, photo_source
