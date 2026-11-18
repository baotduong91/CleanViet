"""Ordered, token-boundary culinary icons, mirrored by frontend iconParser.js."""

from app.services.ingredients import normalize

RULES = (
    (("muc", "bach tuoc", "squid", "octopus"), "🦑", "Seafood"),
    (("tom", "cua", "ghe", "ngheu", "hen", "shrimp", "crab", "shellfish"), "🦐", "Seafood"),
    (("ca", "cha ca", "salmon", "tilapia", "catfish", "fish"), "🐟", "Clean Fish"),
    (("bun", "pho", "hu tieu", "mien", "banh canh"), "🍜", "Noodle Bowl"),
    (("sup", "nui", "chao", "canh"), "🥣", "Clear Soup / Canh"),
    (("ga", "vit", "chicken", "duck"), "🍗", "Poultry"),
    (("bo", "thit", "suon", "beef", "pork"), "🥩", "Savory Meat"),
    (("dau hu", "nam", "rau", "bau", "bi", "cai", "tofu"), "🥬", "Greens & Umami"),
    (("pasta", "bolognese", "spaghetti", "macaroni"), "🍝", "Pasta"),
)


def resolve_dish_icon(title: str) -> dict:
    text = " " + " ".join(normalize(title).split()) + " "
    for tokens, icon, label in RULES:
        if any(" " + token + " " in text for token in tokens):
            return {"icon": icon, "category_label": label}
    return {"icon": "🍲", "category_label": "Home Dish"}
