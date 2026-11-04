"""Deterministic toddler notes keyed by dish title keywords."""

from app.services.ingredients import normalize

FALLBACK = (
    "Reserve a mild portion before spicy/salty sauces; cut proteins and "
    "vegetables into soft bite-sized pieces."
)

RULES: list[tuple[tuple[str, ...], str]] = [
    (
        ("sup nui", "súp nui", "macaroni soup"),
        "Reserve toddler portion of pork & shrimp paste BEFORE black pepper. "
        "Scissor-cut king oyster mushrooms and nui into soft 1cm bites.",
    ),
    (
        ("bun quay", "bún quậy"),
        "Serve tender fish/shrimp paste balls over warm broth-soaked noodles. "
        "Keep spicy muối ớt tắc strictly on the side. Mince squid finely or omit if chewy.",
    ),
    (
        ("salmon", "tilapia", "ca hoi", "ca ro phi"),
        "Flake fish thoroughly and check every piece for pin bones. Serve with "
        "steamed soft broccoli and soft rice.",
    ),
    (
        ("pasta", "bolognese", "spaghetti"),
        "Set aside plain noodles and a scoop of browned beef + soft carrots before "
        "adding acidic/salty sauce. Toss with olive oil.",
    ),
    (
        ("steamed chicken", "ga hap", "chicken ginger", "chicken scallion"),
        "Shred tender chicken along the grain into fine strips. Ladle mild chicken "
        "broth over soft warm rice.",
    ),
]


def toddler_tip_for(dish_name: str) -> str:
    n = normalize(dish_name)
    if "sup nui" in n or ("nui" in n and ("tom" in n or "thit" in n or "shrimp" in n)):
        return RULES[0][1]
    for keys, tip in RULES:
        if any(k in n for k in keys):
            return tip
    if "nui" in n or "macaroni" in n:
        return RULES[0][1]
    return FALLBACK
