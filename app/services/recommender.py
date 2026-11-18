from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP

from app.services.ingredients import INGREDIENTS, normalize
from app.services.meal_transform import apply_preferences
from app.services.ingredient_search import search_ingredients

STORES = {
    "greens": dict(
        id="greens",
        name="Đà Lạt / Mỹ Thuận",
        route="westminster",
        specialty="Vietnamese greens, herbs, calamansi and raw fish paste",
        query="Da Lat supermarket Westminster California",
        stop_order=1,
    ),
    "seafood": dict(
        id="seafood",
        name="Thuận Phát / Lucky Seafood",
        route="westminster",
        specialty="Roe squid, fresh whole fish and unseasoned shrimp",
        query="Thuan Phat supermarket Westminster California",
        stop_order=0,
        cooler_reminder="🧊 Pack in Cooler with Ice",
    ),
    "bulk": dict(
        id="bulk",
        name="Costco / Sam’s / Aldi",
        route="anaheim",
        specialty="Salmon, poultry, milk, eggs and toddler fruit",
        query="Costco Anaheim California",
        stop_order=0,
    ),
    "pantry": dict(
        id="pantry",
        name="Pantry / Weee!",
        route="pantry",
        specialty="Check home stock first: dry noodles, wood ear, broth and sauces",
        query=None,
        stop_order=0,
    ),
    "manual": dict(
        id="manual",
        name="Your local supermarket",
        route="anaheim",
        specialty="No specialty benchmark; compare locally",
        query=None,
        stop_order=2,
    ),
}
ROUTES = [
    dict(
        id="westminster",
        name="Westminster Little Saigon Run",
        note="Stop 1: Thuận Phát / Lucky Seafood (cooler). Stop 2: Đà Lạt / Mỹ Thuận for produce.",
    ),
    dict(
        id="anaheim",
        name="Costco / Local Anaheim Run",
        note="Compare pack sizes before buying bulk.",
    ),
    dict(
        id="pantry",
        name="Pantry / Weee! Check",
        note="Check the cupboard before ordering dry staples.",
    ),
]

DRY_PASTA_IDS = {"nui", "pasta"}
CANONICAL_PASTA_NAME = "Dry pasta / nui"


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


def aggregate_key(item, known):
    unit = item["unit"]
    if known and known["id"] in DRY_PASTA_IDS:
        return ("dry_pasta_nui", unit)
    if known:
        return (known["id"], unit)
    return (normalize(item["name"]), unit)


def display_name(item, known, key):
    if key[0] == "dry_pasta_nui":
        return CANONICAL_PASTA_NAME
    return item["name"]


def cents(n):
    return str(n.quantize(Decimal(".01"), rounding=ROUND_HALF_UP))


def recommend(meals, checked=(), preferences=None):
    meals = apply_preferences(meals, preferences)
    homemade_broth = bool((preferences or {}).get("homemade_broth"))
    quantities = defaultdict(lambda: Decimal(0))
    details = {}
    for meal in meals:
        for item in meal["ingredients"]:
            known = match_item(item)
            key = aggregate_key(item, known)
            quantities[key] += Decimal(str(item["quantity"]))
            details[key] = (item, known)
    groups = {r["id"]: dict(**r, stores=[]) for r in ROUTES}
    stores = {}
    cost = baseline = Decimal(0)
    broth_arbitrage = Decimal(0)
    unknown = 0
    for key, qty in sorted(quantities.items()):
        item, known = details[key]
        specialty = known["specialty"] if known else "manual"
        store = STORES[specialty]
        if specialty not in stores:
            stores[specialty] = dict(**store, items=[])
            groups[store["route"]]["stores"].append(stores[specialty])
        priced = known is not None and known["unit"] == item["unit"]
        line_id = "|".join(key)
        covered = line_id in checked
        local = Decimal(cents(qty * Decimal(known["local_price"]))) if priced else None
        base = Decimal(cents(qty * Decimal(known["weee_price"]))) if priced else None
        skip_broth = (
            homemade_broth and known is not None and known["id"] == "broth" and priced
        )
        if skip_broth and not covered:
            broth_arbitrage += local
            local = Decimal("0.00")
        if not covered:
            if priced:
                cost += local
                baseline += base
            else:
                unknown += 1
        stores[specialty]["items"].append(
            dict(
                id=line_id,
                url=item.get("url") or (known.get("url") if known else None),
                name=display_name(item, known, key),
                quantity=cents(qty),
                unit=item["unit"],
                checked=covered,
                estimated_cost=cents(local) if priced else None,
                savings=cents(base - local) if priced else None,
                is_broth=known is not None and known["id"] == "broth",
                broth_arbitrage_eligible=known is not None and known["id"] == "broth",
            )
        )
    for route in groups.values():
        route["stores"].sort(key=lambda s: s.get("stop_order", 99))
    savings = baseline - cost
    basis = (
        "Estimated USD for unchecked quantities. Excludes full-package overage, fees, "
        "fuel and takeout. Checked = already covered or purchased; no pantry inventory changes."
    )
    if homemade_broth and broth_arbitrage > 0:
        basis += f" Homemade broth saves {cents(broth_arbitrage)} vs buying low-sodium broth."
    return dict(
        routes=list(groups.values()),
        estimated_cost=cents(cost),
        estimated_weee=cents(baseline),
        estimated_savings=cents(savings),
        homemade_broth_savings=cents(broth_arbitrage) if broth_arbitrage else None,
        unpriced_items=unknown,
        basis=basis,
    )


def item_intel(query):
    return [
        dict(
            ingredient=item,
            store=STORES[item["specialty"]],
            basis=(
                "Estimated unit prices; current stock and price are unverified."
                if item["local_price"] is not None
                else "No price benchmark for this cut or ingredient. Compare current store prices."
            ),
        )
        for item in search_ingredients(query)
    ]
