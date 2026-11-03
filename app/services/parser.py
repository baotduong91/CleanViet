"""Local ingredient suggestions; unknown dishes remain available for manual editing."""

import re
from pydantic import BaseModel, ConfigDict, Field
from app.services.ingredients import INGREDIENTS, normalize


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


def parse_dish(dish_name):
    name = dish_name.strip()
    if not name:
        raise ValueError("Enter a dish name.")
    n = normalize(name)
    ids = set()
    for key, item in INGREDIENTS.items():
        if any(
            re.search(r"(?<![a-z0-9])" + re.escape(a) + r"(?![a-z0-9])", n)
            for a in item["aliases"]
        ):
            ids.add(key)
    for pattern, extra in {
        "sup nui": [
            "nui",
            "shrimp",
            "pork",
            "wood_ear",
            "king_oyster",
            "carrot",
            "scallion",
            "broth",
        ],
        "bun quay": [
            "bun",
            "fish_paste",
            "shrimp",
            "squid",
            "calamansi",
            "scallion",
            "broth",
        ],
        "bolognese": ["pasta", "beef", "tomato", "onion", "carrot", "garlic"],
        "steamed chicken": ["chicken", "ginger", "scallion", "rice"],
        "ga hap": ["chicken", "ginger", "scallion", "rice"],
        "tomato pasta": ["pasta", "tomato", "garlic"],
    }.items():
        if pattern in n:
            ids.update(extra)
    if "muc" in n or "bun quay" in n:
        ids.discard("eggs")
    tip = "Reserve a mild portion before salty or spicy sauces. Cut vegetables and noodles into small soft bites."
    if ids & {"salmon", "tilapia", "whole_fish"}:
        tip += " Flake fish carefully and check for pin bones."
    if "squid" in ids:
        tip += " Finely chop tender squid; omit if chewy."
    if "chicken" in ids:
        tip += " Remove bones, skin and cartilage; shred finely."
    return ParsedMeal(
        dish_name=name,
        ingredients=[
            GroceryItem(
                name=INGREDIENTS[k]["name"],
                quantity=INGREDIENTS[k]["quantity"],
                unit=INGREDIENTS[k]["unit"],
                ingredient_id=k,
            )
            for k in sorted(ids)
        ],
        toddler_tip=tip,
        parser_note="Suggestions cover family dinner only; adjust quantities for lunches and appetite."
        if ids
        else "No reliable match. Add ingredients manually; any dish is welcome.",
    )
