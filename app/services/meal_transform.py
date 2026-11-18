from decimal import Decimal

from app.services.ingredients import INGREDIENTS, normalize


def match_item(item):
    if item.get("ingredient_id") in INGREDIENTS:
        return INGREDIENTS[item["ingredient_id"]]
    n = normalize(item["name"])
    return next(
        (
            i
            for i in INGREDIENTS.values()
            if n == normalize(i["name"]) or n in i["aliases"]
        ),
        None,
    )

PROTEIN_IDS = {
    "chicken",
    "tilapia",
    "salmon",
    "shrimp",
    "pork",
    "fish_paste",
    "squid",
    "beef",
    "whole_fish",
}
CARB_IDS = {"rice", "nui", "pasta", "bun"}
LEAN_CARB_IDS = {"rice", "nui", "pasta", "bun"}
LEAN_VOLUME_IDS = {"king_oyster", "broccoli", "greens", "carrot", "napa", "lotus_root", "pumpkin", "bottle_gourd", "shiitake", "taro_stem"}


def _ingredient_id(item) -> str | None:
    if item.get("ingredient_id") in INGREDIENTS:
        return item["ingredient_id"]
    known = match_item(item)
    return known["id"] if known else None


def apply_preferences(meals, preferences=None):
    preferences = preferences or {}
    pack_lunch = preferences.get("pack_lunch") or [False, False, False, False]
    lean = bool(preferences.get("lean_mode"))
    adjusted = []
    for index, meal in enumerate(meals):
        pack = index < len(pack_lunch) and pack_lunch[index]
        ingredients = []
        for item in meal.get("ingredients", []):
            qty = Decimal(str(item["quantity"]))
            kid = _ingredient_id(item)
            if pack and kid in PROTEIN_IDS | CARB_IDS:
                qty *= Decimal("1.5")
            if lean and kid in LEAN_CARB_IDS:
                qty *= Decimal("0.75")
            if lean and kid in LEAN_VOLUME_IDS:
                qty *= Decimal("1.3")
            ingredients.append({**item, "quantity": float(qty)})
        adjusted.append({**meal, "ingredients": ingredients})
    return adjusted
