"""Authentic Vietnamese weeknight cookbook — 3-person family weights (2 adults + toddler)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from app.services.ingredients import INGREDIENTS, normalize

Category = Literal[
    "canh_soups",
    "noodle_bowls",
    "steamed_airfry",
    "stir_fry_savory",
    "toddler_western",
]

IngLine = tuple[str, float | None]


@dataclass(frozen=True)
class CookbookDish:
    id: str
    name_vi: str
    name_en: str
    category: Category
    prep_minutes: int
    commute_friendly: bool
    toddler_tip: str
    ingredients: tuple[IngLine, ...]
    favorite: bool = False
    search_tokens: tuple[str, ...] = field(default_factory=tuple)

    @property
    def display_name(self) -> str:
        return self.name_vi if self.name_vi else self.name_en

    def search_blob(self) -> str:
        return normalize(
            " ".join(
                [self.name_vi, self.name_en, self.id, *self.search_tokens],
            ),
        )


def _d(
    id: str,
    vi: str,
    en: str,
    cat: Category,
    prep: int,
    commute: bool,
    tip: str,
    ings: list[IngLine],
    *,
    favorite: bool = False,
    tokens: tuple[str, ...] = (),
) -> CookbookDish:
    return CookbookDish(
        id=id,
        name_vi=vi,
        name_en=en,
        category=cat,
        prep_minutes=prep,
        commute_friendly=commute,
        toddler_tip=tip,
        ingredients=tuple(ings),
        favorite=favorite,
        search_tokens=tokens,
    )


DISHES: tuple[CookbookDish, ...] = (
    # --- Canh / soups ---
    _d(
        "canh_bau_tom",
        "Canh bầu tôm tươi",
        "Fresh shrimp & bottle gourd soup",
        "canh_soups",
        25,
        True,
        "Peel shrimp; scissor bottle gourd into soft 1cm pieces. Keep pepper off toddler bowl.",
        [("bottle_gourd", 1.25), ("shrimp", 0.75), ("pork", 0.25), ("scallion", 0.125), ("broth", 1.5)],
        tokens=("canh bau tom",),
    ),
    _d(
        "canh_cai_be",
        "Canh cải bẹ xanh thịt bằm",
        "Napa cabbage & ground pork soup",
        "canh_soups",
        22,
        True,
        "Mince pork fine; shred napa into ribbons. Serve mild portion before fish sauce.",
        [("napa", 1), ("pork", 0.75), ("garlic", 0.08), ("broth", 1.5)],
        tokens=("canh cai be", "cai be xanh"),
    ),
    _d(
        "canh_mong_toi_tom",
        "Canh mồng tơi nấu tôm",
        "Malabar spinach & shrimp soup",
        "canh_soups",
        20,
        True,
        "Pick tender spinach tips; halve shrimp for toddler. Check shells removed.",
        [("greens", 0.5), ("shrimp", 0.75), ("garlic", 0.08), ("broth", 1.5)],
        tokens=("mong toi", "canh mong toi"),
    ),
    _d(
        "canh_chua_ca",
        "Canh chua cá bông lau",
        "Tamarind-sour catfish soup",
        "canh_soups",
        35,
        False,
        "Flake catfish; serve toddler portion before sour tamarind and chili.",
        [("catfish", 1.5), ("tomato", 0.5), ("pineapple", None), ("bean_sprout", None), ("broth", 1.5)],
        tokens=("canh chua", "ca bong lau"),
    ),
    _d(
        "canh_tan_o_thac_lac",
        "Canh tần ô cá thác lác",
        "Taro stem & featherback fish soup",
        "canh_soups",
        30,
        False,
        "Poach fish paste balls until springy; slice taro stem thin and soft.",
        [("taro_stem", 0.75), ("fish_paste", 0.5), ("shrimp", 0.5), ("scallion", 0.125), ("broth", 1.5)],
        tokens=("tan o", "thac lac"),
    ),
    _d(
        "canh_suon_sen",
        "Canh sườn non củ sen",
        "Young ribs & lotus root soup",
        "canh_soups",
        45,
        False,
        "Simmer ribs until tender; lotus root in thin coins for toddler.",
        [("pork_ribs", 1.5), ("lotus_root", 0.75), ("broth", 2), ("scallion", 0.125)],
        tokens=("suon non", "cu sen"),
    ),
    _d(
        "canh_rong_bien_dau_hu",
        "Canh rong biển đậu hũ thịt bằm",
        "Seaweed tofu pork soup",
        "canh_soups",
        25,
        True,
        "Crumble tofu small; soak seaweed briefly so it is soft for toddler.",
        [("seaweed", 0.05), ("tofu", 0.75), ("pork", 0.5), ("broth", 1.5), ("scallion", 0.125)],
        tokens=("rong bien", "dau hu"),
    ),
    _d(
        "canh_bi_do",
        "Canh bí đỏ thịt bằm",
        "Pumpkin ground pork soup",
        "canh_soups",
        25,
        True,
        "Mash pumpkin cubes until soft; mild portion before fish sauce.",
        [("pumpkin", 1), ("pork", 0.75), ("broth", 1.5), ("scallion", 0.125)],
        tokens=("bi do", "canh bi"),
    ),
    _d(
        "canh_khoai_mon",
        "Canh khoai môn thịt bằm",
        "Taro & pork soup",
        "canh_soups",
        30,
        False,
        "Cook taro until very soft; watch toddler portion size.",
        [("pumpkin", 0.75), ("pork", 0.75), ("broth", 1.5), ("scallion", 0.125)],
        tokens=("khoai mon",),
    ),
    _d(
        "canh_chua_tom",
        "Canh chua tôm",
        "Sour shrimp soup",
        "canh_soups",
        25,
        True,
        "Shell-on flavor for adults; toddler gets peeled shrimp only.",
        [("shrimp", 1), ("tomato", 0.5), ("pineapple", None), ("bean_sprout", None), ("broth", 1.5)],
        tokens=("canh chua tom",),
    ),
    # --- Noodles ---
    _d(
        "sup_nui_tom_nam",
        "Súp nui tôm thịt nấm đùi gà",
        "Macaroni soup shrimp pork king oyster",
        "noodle_bowls",
        25,
        True,
        "Scissor nui and mushrooms into 1cm bites; mild portion before pepper.",
        [
            ("nui", 0.5),
            ("shrimp", 0.75),
            ("pork", 0.75),
            ("king_oyster", 0.5),
            ("carrot", 0.5),
            ("wood_ear", 0.025),
            ("scallion", 0.125),
            ("broth", 1.5),
        ],
        favorite=True,
        tokens=("sup nui", "súp nui"),
    ),
    _d(
        "bun_quay_pq",
        "Bún quậy Phú Quốc",
        "Phú Quốc dipping noodle bowl",
        "noodle_bowls",
        30,
        False,
        "Keep muối ớt tắc off toddler bowl; mince squid if chewy.",
        [
            ("bun", 0.5),
            ("fish_paste", 0.5),
            ("shrimp", 0.75),
            ("squid", 0.75),
            ("calamansi", 0.25),
            ("scallion", 0.125),
            ("broth", 1.5),
        ],
        favorite=True,
        tokens=("bun quay",),
    ),
    _d(
        "bun_moc",
        "Bún mọc nấm hương",
        "Vietnamese meatball & shiitake noodle soup",
        "noodle_bowls",
        30,
        False,
        "Split meatballs small; soften shiitake strips for toddler.",
        [("bun", 0.5), ("pork", 1), ("shiitake", 0.35), ("scallion", 0.125), ("broth", 1.5)],
        tokens=("bun moc",),
    ),
    _d(
        "mien_ga",
        "Miến gà xé phay",
        "Glass noodle chicken soup",
        "noodle_bowls",
        35,
        False,
        "Shred chicken fine; cut glass noodles short for toddler.",
        [("glass_noodle", 0.35), ("chicken", 1.5), ("ginger", 0.1), ("scallion", 0.125), ("broth", 1.5)],
        tokens=("mien ga", "miến gà"),
    ),
    _d(
        "chao_ga",
        "Cháo gà ác hạt sen",
        "Free-range chicken lotus seed congee",
        "noodle_bowls",
        40,
        False,
        "Cook rice very soft; shred chicken to threads for toddler.",
        [("rice", 0.75), ("chicken", 1.5), ("lotus_root", 0.25), ("ginger", 0.1), ("broth", 2)],
        tokens=("chao ga", "cháo"),
    ),
    _d(
        "bun_bo_hue_nhe",
        "Bún bò Huế nhẹ",
        "Light central-style beef noodle soup",
        "noodle_bowls",
        40,
        False,
        "Skip chili oil for toddler; thin-slice beef after simmering.",
        [("bun", 0.5), ("beef", 0.75), ("lemongrass", 0.25), ("broth", 2)],
        tokens=("bun bo",),
    ),
    _d(
        "hu_tieu",
        "Hủ tiếu Nam Vang",
        "Nam Vang pork seafood noodle soup",
        "noodle_bowls",
        35,
        False,
        "Mild bowl before lime and chili; mince shrimp.",
        [("nui", 0.5), ("pork", 0.5), ("shrimp", 0.5), ("broth", 1.5), ("scallion", 0.125)],
        tokens=("hu tieu",),
    ),
    _d(
        "mi_quang",
        "Mì Quảng gà",
        "Quảng-style turmeric chicken noodles",
        "noodle_bowls",
        35,
        False,
        "Use wide noodles; toddler portion with extra broth.",
        [("nui", 0.5), ("chicken", 1.25), ("turmeric", None), ("peanut", None), ("broth", 1)],
        tokens=("mi quang",),
    ),
    _d(
        "bun_thit_nuong",
        "Bún thịt nướng",
        "Grilled pork vermicelli bowl",
        "noodle_bowls",
        30,
        True,
        "Cut pork into small bites; fish sauce dip on side for adults only.",
        [("bun", 0.5), ("pork", 1), ("lettuce", None), ("cucumber", None), ("scallion", 0.125)],
        tokens=("bun thit nuong",),
    ),
    _d(
        "pho_ga_nhe",
        "Phở gà nhẹ",
        "Light chicken pho",
        "noodle_bowls",
        45,
        False,
        "Skim fat; star anise light for toddler bowl.",
        [("bun", 0.5), ("chicken", 1.5), ("ginger", 0.1), ("onion", 0.25), ("broth", 2)],
        tokens=("pho ga",),
    ),
    # --- Steamed & air-fry ---
    _d(
        "ga_hap_hanh_gung",
        "Gà hấp hành gừng",
        "Steamed ginger scallion chicken",
        "steamed_airfry",
        35,
        False,
        "Shred chicken along grain; ladle mild broth over soft rice.",
        [("chicken", 1.5), ("ginger", 0.15), ("scallion", 0.2), ("rice", 0.5)],
        favorite=True,
        tokens=("ga hap", "gà hấp"),
    ),
    _d(
        "ga_hap_la_chanh",
        "Gà hấp lá chanh nấm đùi gà",
        "Kaffir lime leaf king oyster steamed chicken",
        "steamed_airfry",
        40,
        False,
        "Remove lime leaf sliver from toddler portion; soft mushroom strips.",
        [("chicken", 1.5), ("lime_leaf", 0.15), ("king_oyster", 0.5), ("ginger", 0.1), ("rice", 0.5)],
        tokens=("ga hap la chanh",),
    ),
    _d(
        "ca_ro_phi_sa",
        "Cá rô phi nướng sả nghệ (Air Fryer)",
        "Air-fry lemongrass turmeric tilapia",
        "steamed_airfry",
        22,
        True,
        "Flake thoroughly; check for pin bones. Soft broccoli on side.",
        [("tilapia", 1.25), ("lemongrass", 0.25), ("turmeric", None), ("broccoli", 1), ("rice", 0.5)],
        tokens=("ca ro phi", "tilapia"),
    ),
    _d(
        "ca_hoi_airfry",
        "Cá hồi nướng miso tỏi ớt (Air Fryer)",
        "Air-fry miso garlic salmon",
        "steamed_airfry",
        20,
        True,
        "Flake fish; check pin bones. Reserve plain salmon before glaze.",
        [("salmon", 1.25), ("garlic", 0.08), ("broccoli", 1), ("rice", 0.5)],
        favorite=True,
        tokens=("ca hoi", "salmon air"),
    ),
    _d(
        "muc_hap",
        "Mực ống trứng hấp gừng hành",
        "Steamed roe squid ginger scallion",
        "steamed_airfry",
        25,
        True,
        "Mince squid rings fine for toddler or offer shrimp alternate.",
        [("squid", 0.75), ("ginger", 0.1), ("scallion", 0.125), ("rice", 0.5)],
        tokens=("muc hap", "muc ong trung"),
    ),
    _d(
        "ca_hap_tuong",
        "Cá điêu hồng chưng tương",
        "Steamed red snapper black bean",
        "steamed_airfry",
        30,
        False,
        "Debone snapper; toddler gets plain steamed portion before salty bean sauce.",
        [("red_snapper", 1.5), ("ginger", 0.1), ("scallion", 0.125), ("rice", 0.5)],
        tokens=("ca dieu hong", "chung tuong"),
    ),
    _d(
        "tom_hap",
        "Tôm hấp bia",
        "Beer-steamed shrimp",
        "steamed_airfry",
        18,
        True,
        "Peel toddler shrimp; halve lengthwise.",
        [("shrimp", 1.25), ("lemongrass", 0.15), ("rice", 0.5)],
        tokens=("tom hap",),
    ),
    _d(
        "ca_hap_xi_dau",
        "Cá hấp xì dầu",
        "Steamed fish soy ginger",
        "steamed_airfry",
        25,
        True,
        "Light soy on toddler portion only after steaming plain.",
        [("whole_fish", 1.5), ("ginger", 0.1), ("scallion", 0.125), ("rice", 0.5)],
        tokens=("ca hap",),
    ),
    # --- Stir-fry & savory ---
    _d(
        "bo_luc_lac",
        "Bò lúc lắc khoai tây air-fry",
        "Shaking beef & air-fry potatoes",
        "stir_fry_savory",
        25,
        True,
        "Cut beef and potatoes into toddler bite cubes; less pepper on kids plate.",
        [("beef_tenderloin", 1), ("potato", 1), ("garlic", 0.08), ("tomato", 0.25)],
        tokens=("bo luc lac",),
    ),
    _d(
        "bo_xao_broccoli",
        "Thịt bò xào bông cải xanh",
        "Beef broccoli stir-fry",
        "stir_fry_savory",
        20,
        True,
        "Soft-steam broccoli first for toddler; thin beef slices.",
        [("beef", 0.75), ("broccoli", 1), ("garlic", 0.08), ("rice", 0.5)],
        tokens=("bo xao", "bong cai"),
    ),
    _d(
        "muc_xao_toi",
        "Mực xào cần tỏi",
        "Garlic celery squid stir-fry",
        "stir_fry_savory",
        18,
        True,
        "Score squid; mince for toddler if chewy.",
        [("squid", 0.75), ("garlic", 0.1), ("scallion", 0.125), ("rice", 0.5)],
        tokens=("muc xao",),
    ),
    _d(
        "dau_hu_nhoi_thit",
        "Đậu hũ nhồi thịt sốt cà chua",
        "Stuffed tofu tomato sauce",
        "stir_fry_savory",
        30,
        False,
        "Crumble stuffed tofu for toddler; mild sauce before fish sauce.",
        [("tofu", 1), ("pork", 0.5), ("tomato", 0.75), ("scallion", 0.125), ("rice", 0.5)],
        tokens=("dau hu nhoi",),
    ),
    _d(
        "tom_rim_thit",
        "Tôm rim thịt nạc",
        "Caramel shrimp lean pork",
        "stir_fry_savory",
        25,
        True,
        "Peel shrimp; use less caramel color on toddler portion.",
        [("shrimp", 0.75), ("pork", 0.75), ("garlic", 0.08), ("rice", 0.5)],
        tokens=("tom rim",),
    ),
    _d(
        "thit_kho_trung",
        "Thịt kho trứng",
        "Caramel pork & eggs",
        "stir_fry_savory",
        40,
        False,
        "Quarter eggs; rinse sauce off toddler pork.",
        [("pork", 1.25), ("eggs", 6), ("coconut", None), ("rice", 0.75)],
        tokens=("thit kho",),
    ),
    _d(
        "ca_kho_to",
        "Cá kho tộ",
        "Clay-pot braised catfish",
        "stir_fry_savory",
        35,
        False,
        "Flake fish; dilute sauce for toddler.",
        [("catfish", 1.25), ("pork", 0.25), ("garlic", 0.08), ("rice", 0.75)],
        tokens=("ca kho",),
    ),
    _d(
        "rau_muong_xao",
        "Rau muống xào tỏi",
        "Garlic water spinach",
        "stir_fry_savory",
        12,
        True,
        "Chop spinach fine for toddler; mild garlic.",
        [("greens", 0.75), ("garlic", 0.08), ("rice", 0.5)],
        tokens=("rau muong",),
    ),
    _d(
        "canh_ga_sam",
        "Gà xào sả ớt",
        "Lemongrass chili chicken stir-fry",
        "stir_fry_savory",
        22,
        True,
        "No chili on toddler plate; small chicken cubes.",
        [("chicken", 1), ("lemongrass", 0.25), ("rice", 0.5)],
        tokens=("ga xao",),
    ),
    # --- Toddler / Western family ---
    _d(
        "pasta_bolognese",
        "Pasta bolognese",
        "Family pasta bolognese",
        "toddler_western",
        30,
        True,
        "Plain noodles + mild beef scoop before acidic sauce.",
        [("pasta", 0.5), ("beef", 1), ("tomato", 0.5), ("carrot", 0.5), ("onion", 0.5), ("garlic", 0.1)],
        favorite=True,
        tokens=("bolognese", "pasta"),
    ),
    _d(
        "toddler_tomato_pasta",
        "Toddler tomato pasta",
        "Mild tomato pasta",
        "toddler_western",
        20,
        True,
        "Olive oil toss; soft carrot dice.",
        [("pasta", 0.5), ("tomato", 0.5), ("garlic", 0.05)],
        favorite=True,
    ),
    _d(
        "salmon_broccoli_rice",
        "Air fry salmon with broccoli & rice",
        "Salmon broccoli rice bowl",
        "toddler_western",
        22,
        True,
        "Flake salmon; check pin bones. Soft broccoli.",
        [("salmon", 1.25), ("broccoli", 1), ("rice", 0.5)],
        favorite=True,
        tokens=("air fry salmon",),
    ),
    _d(
        "steamed_chicken_ginger",
        "Steamed chicken ginger scallion",
        "Steamed chicken ginger scallion",
        "toddler_western",
        35,
        False,
        "Shred chicken fine; mild broth over rice.",
        [("chicken", 1.5), ("ginger", 0.15), ("scallion", 0.2), ("rice", 0.5)],
        favorite=True,
        tokens=("steamed chicken",),
    ),
    _d(
        "turkey_meatballs",
        "Turkey veggie meatballs",
        "Turkey veggie meatballs",
        "toddler_western",
        25,
        True,
        "Split meatballs small; check internal temp.",
        [("beef", 0.75), ("carrot", 0.5), ("onion", 0.25), ("pasta", 0.5)],
        tokens=("meatball",),
    ),
    _d(
        "sheet_pan_chicken",
        "Sheet-pan lemon herb chicken",
        "Sheet-pan lemon herb chicken",
        "toddler_western",
        30,
        True,
        "Cube chicken; roast carrots soft.",
        [("chicken", 1.25), ("potato", 0.75), ("carrot", 0.5), ("rice", 0.5)],
        tokens=("sheet pan",),
    ),
)

# Placeholder ingredient ids map to sensible defaults when missing from INGREDIENTS
_PLACEHOLDER_DEFAULTS: dict[str, IngLine] = {
    "pineapple": ("fruit", 0.25),
    "bean_sprout": ("greens", 0.35),
    "turmeric": ("ginger", 0.02),
    "peanut": ("fruit", 0.1),
    "lettuce": ("greens", 0.35),
    "cucumber": ("greens", 0.35),
    "coconut": ("milk", 0.25),
}

DISH_BY_ID = {d.id: d for d in DISHES}


def _score(query_norm: str, dish: CookbookDish) -> int:
    blob = dish.search_blob()
    if query_norm == dish.id.replace("_", " "):
        return 1000
    if query_norm in blob or blob in query_norm:
        return 500 + len(query_norm)
    q_tokens = set(query_norm.split())
    b_tokens = set(blob.split())
    overlap = len(q_tokens & b_tokens)
    if overlap:
        return 100 + overlap * 10
    for tok in dish.search_tokens:
        tn = normalize(tok)
        if tn in query_norm or query_norm in tn:
            return 300
    return 0


def find_catalog_dish(query: str) -> CookbookDish | None:
    q = normalize(query)
    if not q:
        return None
    ranked = sorted(
        ((_score(q, d), d) for d in DISHES),
        key=lambda pair: (pair[0], pair[1].id),
        reverse=True,
    )
    best_score, best = ranked[0]
    return best if best_score >= 100 else None


def list_dishes(
    category: str | None = None,
    q: str = "",
    limit: int = 50,
) -> list[dict]:
    qn = normalize(q)
    out: list[tuple[int, CookbookDish]] = []
    for dish in DISHES:
        if category and category != "favorites" and dish.category != category:
            continue
        if category == "favorites" and not dish.favorite:
            continue
        score = _score(qn, dish) if qn else (10 if dish.favorite else 1)
        if qn and score < 50:
            continue
        out.append((score, dish))
    out.sort(key=lambda x: (-x[0], x[1].id))
    return [
        {
            "id": d.id,
            "name_vi": d.name_vi,
            "name_en": d.name_en,
            "display_name": d.display_name,
            "category": d.category,
            "prep_minutes": d.prep_minutes,
            "commute_friendly": d.commute_friendly,
            "favorite": d.favorite,
            "deletable": False,
            "image_url": None,
        }
        for _, d in out[:limit]
    ]


def resolve_ingredient_line(line: IngLine) -> tuple[str, float]:
    ing_id, qty = line
    if ing_id in _PLACEHOLDER_DEFAULTS:
        pid, pq = _PLACEHOLDER_DEFAULTS[ing_id]
        ing_id = pid
        if qty is None:
            qty = pq
    meta = INGREDIENTS.get(ing_id)
    if meta is None:
        ing_id = "greens"
        meta = INGREDIENTS["greens"]
    amount = float(qty if qty is not None else meta["quantity"])
    return ing_id, amount


def catalog_to_grocery_items(dish: CookbookDish) -> list[tuple[str, str, float, str]]:
    lines: list[tuple[str, str, float, str]] = []
    seen: set[str] = set()
    for raw in dish.ingredients:
        ing_id, qty = resolve_ingredient_line(raw)
        if ing_id in seen:
            continue
        seen.add(ing_id)
        meta = INGREDIENTS[ing_id]
        lines.append((ing_id, meta["name"], qty, meta["unit"]))
    return lines
