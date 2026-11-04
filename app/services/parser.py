"""Vietnamese cookbook parser with catalog match, token deconstruction, and URL import."""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field

from app.services.cookbook_catalog import (
    catalog_to_grocery_items,
    find_catalog_dish,
)
from app.services.ingredients import INGREDIENTS, normalize
from app.services.toddler_tips import toddler_tip_for


class GroceryItem(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=120)
    quantity: float = Field(gt=0, le=1000, allow_inf_nan=False)
    unit: str = Field(pattern="^(lb|L|each)$")
    ingredient_id: str | None = None


class ParsedMeal(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    dish_name: str = Field(min_length=1, max_length=200)
    ingredients: list[GroceryItem] = Field(default_factory=list, max_length=40)
    toddler_tip: str = Field(
        default="Reserve a mild portion; cut into small soft bites and check ingredients for allergens.",
        max_length=1000,
    )
    parser_note: str = Field(
        default="Local suggestions; review before confirming.", max_length=1000
    )
    image_url: str | None = Field(default=None, max_length=500)


def _items_from_ids(ids: set[str]) -> list[GroceryItem]:
    return [
        GroceryItem(
            name=INGREDIENTS[k]["name"],
            quantity=INGREDIENTS[k]["quantity"],
            unit=INGREDIENTS[k]["unit"],
            ingredient_id=k,
        )
        for k in sorted(ids)
        if k in INGREDIENTS
    ]


def _deconstruct_dish(name: str) -> list[GroceryItem]:
    n = normalize(name)
    ids: set[str] = set()

    protein_map = [
        (("ca hoi", "salmon"), "salmon"),
        (("ca ro phi", "tilapia"), "tilapia"),
        (("ca dieu hong", "red snapper"), "red_snapper"),
        (("ca bong lau", "ca lang", "ca tra", "catfish"), "catfish"),
        (("ca ", "fish", "whole fish"), "whole_fish"),
        (("tom", "shrimp"), "shrimp"),
        (("muc", "squid"), "squid"),
        (("bo ", "beef", "bo luc lac"), "beef"),
        (("bo tenderloin", "thit bo"), "beef_tenderloin"),
        (("ga ", "chicken"), "chicken"),
        (("thit bam", "thit heo", "pork", "suon"), "pork"),
        (("suon non",), "pork_ribs"),
        (("thac lac", "cha ca", "fish paste"), "fish_paste"),
    ]
    for keys, ing in protein_map:
        if any(k in n for k in keys):
            ids.add(ing)

    veg_map = [
        (("bau", "bottle gourd"), "bottle_gourd"),
        (("bi do", "pumpkin"), "pumpkin"),
        (("cai be", "napa"), "napa"),
        (("mong toi", "rau mong"), "greens"),
        (("bong cai", "broccoli"), "broccoli"),
        (("nam duoi ga", "king oyster"), "king_oyster"),
        (("nam huong", "shiitake"), "shiitake"),
        (("cu sen", "lotus"), "lotus_root"),
        (("rong bien", "seaweed"), "seaweed"),
        (("khoai tay", "potato"), "potato"),
        (("dau hu", "tofu"), "tofu"),
        (("carrot", "ca rot"), "carrot"),
        (("tan o", "bac ha"), "taro_stem"),
    ]
    for keys, ing in veg_map:
        if any(k in n for k in keys):
            ids.add(ing)

    if any(k in n for k in ("canh", "sup", "chao", "broth", "soup")):
        ids.update({"broth", "scallion", "garlic"})
    if any(k in n for k in ("bun", "pho", "hu tieu")):
        ids.add("bun")
    if any(k in n for k in ("nui", "macaroni", "pasta", "spaghetti", "bolognese")):
        ids.update({"nui", "pasta"})
    if "mien" in n or "glass noodle" in n:
        ids.add("glass_noodle")
    if any(k in n for k in ("hap", "steamed")):
        ids.update({"ginger", "scallion", "rice"})
    if any(k in n for k in ("nuong", "air fry", "airfry", "grill")):
        ids.update({"garlic", "lemongrass", "rice"})
    if any(k in n for k in ("xao", "stir fry", "rim", "kho")):
        ids.update({"garlic", "rice"})
    if any(k in n for k in ("hanh la", "scallion")):
        ids.add("scallion")
    if "gung" in n or "ginger" in n:
        ids.add("ginger")
    if "toi" in n or "garlic" in n:
        ids.add("garlic")
    if "sa " in n or "lemongrass" in n:
        ids.add("lemongrass")
    if "la chanh" in n or "kaffir" in n:
        ids.add("lime_leaf")
    if "com" in n or "rice" in n:
        ids.add("rice")

    for key, item in INGREDIENTS.items():
        if any(
            re.search(r"(?<![a-z0-9])" + re.escape(a) + r"(?![a-z0-9])", n)
            for a in item["aliases"]
        ):
            ids.add(key)

    legacy_patterns = {
        "sup nui": ["nui", "shrimp", "pork", "wood_ear", "king_oyster", "carrot", "scallion", "broth"],
        "bun quay": ["bun", "fish_paste", "shrimp", "squid", "calamansi", "scallion", "broth"],
        "bolognese": ["pasta", "beef", "tomato", "onion", "carrot", "garlic"],
        "steamed chicken": ["chicken", "ginger", "scallion", "rice"],
        "ga hap": ["chicken", "ginger", "scallion", "rice"],
        "tomato pasta": ["pasta", "tomato", "garlic"],
    }
    for pattern, extra in legacy_patterns.items():
        if pattern in n:
            ids.update(extra)
    if "muc" in n or "bun quay" in n:
        ids.discard("eggs")

    if not ids:
        ids.update({"rice", "broth", "greens", "garlic", "scallion"})

    return _items_from_ids(ids)


def parse_dish(dish_name: str) -> ParsedMeal:
    name = dish_name.strip()
    if not name:
        raise ValueError("Enter a dish name.")

    catalog = find_catalog_dish(name)
    if catalog:
        ingredients = [
            GroceryItem(
                name=label,
                quantity=qty,
                unit=unit,
                ingredient_id=ing_id,
            )
            for ing_id, label, qty, unit in catalog_to_grocery_items(catalog)
        ]
        return ParsedMeal(
            dish_name=catalog.display_name,
            ingredients=ingredients,
            toddler_tip=catalog.toddler_tip,
            parser_note=f"Cookbook match ({catalog.prep_minutes} min). Adjust for appetite.",
        )

    ingredients = _deconstruct_dish(name)
    tip = toddler_tip_for(name)
    return ParsedMeal(
        dish_name=name,
        ingredients=ingredients,
        toddler_tip=tip,
        parser_note="Component parser; review quantities before confirming.",
    )


def parsed_from_import(
    title: str,
    items: list[GroceryItem],
    note: str,
    image_url: str | None = None,
) -> ParsedMeal:
    return ParsedMeal(
        dish_name=title,
        ingredients=items,
        toddler_tip=toddler_tip_for(title),
        parser_note=note,
        image_url=image_url,
    )
