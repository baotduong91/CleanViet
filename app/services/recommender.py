from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from app.services.ingredients import INGREDIENTS, normalize

STORES = {
    "greens": dict(
        id="greens",
        name="Đà Lạt / Mỹ Thuận",
        route="westminster",
        specialty="Vietnamese greens, herbs, calamansi and raw fish paste",
        query="Da Lat supermarket Westminster California",
    ),
    "seafood": dict(
        id="seafood",
        name="Thuận Phát / Lucky Seafood",
        route="westminster",
        specialty="Roe squid, fresh whole fish and unseasoned shrimp",
        query="Thuan Phat supermarket Westminster California",
    ),
    "bulk": dict(
        id="bulk",
        name="Costco / Sam’s / Aldi",
        route="anaheim",
        specialty="Salmon, poultry, milk, eggs and toddler fruit",
        query="Costco Anaheim California",
    ),
    "pantry": dict(
        id="pantry",
        name="Pantry / Weee!",
        route="pantry",
        specialty="Check home stock first: dry noodles, wood ear, broth and sauces",
        query=None,
    ),
    "manual": dict(
        id="manual",
        name="Your local supermarket",
        route="anaheim",
        specialty="No specialty benchmark; compare locally",
        query=None,
    ),
}
ROUTES = [
    dict(
        id="westminster",
        name="Westminster Little Saigon Run",
        note="Greens first, seafood last; bring a cooler.",
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


def cents(n):
    return str(n.quantize(Decimal(".01"), rounding=ROUND_HALF_UP))


def recommend(meals, checked=()):
    quantities = defaultdict(lambda: Decimal(0))
    details = {}
    for meal in meals:
        for item in meal["ingredients"]:
            known = match_item(item)
            key = (known["id"] if known else normalize(item["name"]), item["unit"])
            quantities[key] += Decimal(str(item["quantity"]))
            details[key] = (item, known)
    groups = {r["id"]: dict(**r, stores=[]) for r in ROUTES}
    stores = {}
    cost = baseline = Decimal(0)
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
        if not covered:
            if priced:
                cost += local
                baseline += base
            else:
                unknown += 1
        stores[specialty]["items"].append(
            dict(
                id=line_id,
                name=item["name"],
                quantity=str(qty),
                unit=item["unit"],
                checked=covered,
                estimated_cost=cents(local) if priced else None,
                savings=cents(base - local) if priced else None,
            )
        )
    return dict(
        routes=list(groups.values()),
        estimated_cost=cents(cost),
        estimated_weee=cents(baseline),
        estimated_savings=cents(baseline - cost),
        unpriced_items=unknown,
        basis="Estimated USD for unchecked quantities. Excludes full-package overage, fees, fuel and takeout. Checked = already covered or purchased; no pantry inventory changes.",
    )


def item_intel(query):
    n = normalize(query)
    exact = [
        i
        for i in INGREDIENTS.values()
        if n in i["aliases"] or n == normalize(i["name"])
    ]
    candidates = exact or list(INGREDIENTS.values())
    return [
        dict(
            ingredient=i,
            store=STORES[i["specialty"]],
            basis="Household heuristic; estimated unit prices and current stock are unverified.",
        )
        for i in candidates
        if n
        and (n in normalize(i["name"]) or any(n in a or a in n for a in i["aliases"]))
    ][:8]
