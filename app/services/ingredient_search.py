"""Bilingual, cut-aware store lookup without changing recipe ingredient identities."""

from difflib import SequenceMatcher
import re

from app.services.ingredients import INGREDIENTS, normalize

SEARCH_TERMS = {
    "beef_tenderloin": ("Thịt bò phi lê", ("thit bo phi le", "bo phi le", "bo phile", "than noi bo", "beef fillet", "filet mignon", "beef filet")),
    "beef": ("Thịt bò bằm", ("thit bo bam", "thit bo xay", "bo xay", "ground beef", "minced beef")),
    "pork": ("Thịt heo bằm", ("thit heo bam", "thit heo xay", "thit lon bam", "ground pork", "minced pork")),
    "pork_ribs": ("Sườn heo", ("suon heo", "suon lon", "suon non", "pork spare ribs", "pork baby back ribs")),
    "chicken": ("Gà nguyên con", ("ga nguyen con", "ga di bo", "ga ta", "whole chicken")),
    "tilapia": ("Cá rô phi phi lê", ("phi le ca ro phi", "ca ro phi", "tilapia fillet")),
    "salmon": ("Cá hồi phi lê", ("phi le ca hoi", "ca hoi phi le", "salmon fillet")),
    "catfish": ("Cá basa / cá tra", ("ca basa", "basa fillet", "swai fillet", "phi le ca tra")),
    "red_snapper": ("Cá diêu hồng", ("ca dieu hong", "ca hong", "red snapper")),
    "squid": ("Mực ống trứng", ("muc ong", "muc trung", "muc ong trung", "roe squid")),
    "shrimp": ("Tôm bóc vỏ", ("tom boc vo", "tom lot vo", "peeled shrimp", "raw shrimp")),
    "fish_paste": ("Chả cá thác lác", ("cha ca that lac", "ca thac lac", "cha ca thac lac", "featherback fish paste")),
    "king_oyster": ("Nấm đùi gà", ("nam dui ga", "king oyster mushroom", "king trumpet mushroom")),
    "shiitake": ("Nấm hương / nấm đông cô", ("nam huong", "nam dong co", "shiitake mushroom")),
    "wood_ear": ("Nấm mèo / mộc nhĩ", ("moc nhi", "nam meo kho", "wood ear mushroom")),
    "tofu": ("Đậu hũ / đậu phụ", ("dau hu", "dau phu", "bean curd")),
    "calamansi": ("Tắc / quất", ("quat", "trai tac", "trai quat", "calamondin")),
    "broccoli": ("Bông cải xanh", ("sup lo xanh", "bong cai xanh")),
    "napa": ("Cải thảo", ("cai thao", "napa cabbage")),
    "bottle_gourd": ("Bầu", ("trai bau", "qua bau", "bottle gourd")),
    "pumpkin": ("Bí đỏ / bí ngô", ("bi do", "bi ngo", "kabocha squash")),
    "carrot": ("Cà rốt", ("ca rot", "carrots")),
    "onion": ("Hành tây", ("hanh tay", "onions")),
    "scallion": ("Hành lá", ("hanh la", "green onion", "spring onion")),
    "lemongrass": ("Sả", ("cu sa", "cay sa", "lemongrass stalk")),
    "garlic": ("Tỏi", ("cu toi", "garlic cloves")),
    "ginger": ("Gừng", ("cu gung", "fresh ginger")),
    "tomato": ("Cà chua", ("ca chua", "tomatoes")),
    "rice": ("Gạo", ("gao te", "gao jasmine", "jasmine rice")),
    "bun": ("Bún khô", ("bun kho", "rice noodles", "rice vermicelli")),
    "nui": ("Nui", ("nui ong", "elbow macaroni")),
    "glass_noodle": ("Miến", ("mien kho", "glass noodles", "cellophane noodles")),
    "lotus_root": ("Củ sen", ("cu sen",)),
    "seaweed": ("Rong biển", ("rong bien",)),
    "taro_stem": ("Bạc hà / tần ô", ("bac ha", "tan o")),
    "rau_ram": ("Rau răm", ("rau ram",)),
    "lime_leaf": ("Lá chanh", ("la chanh", "makrut lime leaf")),
    "broth": ("Nước dùng", ("nuoc dung", "nuoc leo")),
    "eggs": ("Trứng gà", ("trung ga", "trung vit", "chicken eggs")),
    "milk": ("Sữa", ("sua tuoi", "sua huu co", "whole milk")),
    "fruit": ("Trái cây", ("hoa qua", "trai cay")),
}

# Additional searchable cuts have no invented price benchmark.
EXTRA_ITEMS = (
    ("beef_sirloin", "Beef sirloin", "Thăn ngoại bò", "bulk", ("than ngoai bo", "bo than ngoai", "sirloin steak")),
    ("beef_flank", "Beef flank steak", "Thịt bò hông", "bulk", ("thit bo hong", "bo hong", "flank steak")),
    ("beef_shank", "Beef shank", "Bắp bò", "greens", ("bap bo", "bo bap", "beef shin")),
    ("beef_brisket", "Beef brisket", "Nạm bò", "bulk", ("nam bo", "bo nam", "brisket")),
    ("chicken_breast", "Chicken breast", "Ức gà", "bulk", ("uc ga", "uc ga phi le", "chicken breast fillet")),
    ("chicken_thigh", "Chicken thighs", "Đùi gà", "bulk", ("dui ga", "chicken thigh")),
    ("chicken_wings", "Chicken wings", "Cánh gà", "bulk", ("canh ga", "chicken wing")),
    ("pork_tenderloin", "Pork tenderloin", "Thịt heo phi lê", "bulk", ("thit heo phi le", "than heo", "than lon", "pork fillet")),
    ("pork_belly", "Pork belly", "Thịt ba chỉ", "greens", ("thit ba chi", "ba roi", "thit ba roi")),
    ("pork_shoulder", "Pork shoulder", "Thịt nạc vai", "bulk", ("thit nac vai", "nac vai", "pork butt")),
    ("tiger_shrimp", "Shell-on tiger shrimp", "Tôm sú", "seafood", ("tom su", "tiger prawns", "shell on shrimp")),
    ("clams", "Clams", "Nghêu / ngao", "seafood", ("ngheu", "ngao", "littleneck clams")),
    ("oysters", "Oysters", "Hàu", "seafood", ("hau", "oyster")),
    ("oyster_mushroom", "Oyster mushrooms", "Nấm bào ngư", "greens", ("nam bao ngu", "oyster mushroom")),
    ("bok_choy", "Bok choy", "Cải thìa", "greens", ("cai thia", "cai chip", "baby bok choy")),
    ("water_spinach", "Water spinach", "Rau muống", "greens", ("rau muong", "ong choy", "morning glory")),
    ("cabbage", "Cabbage", "Bắp cải", "bulk", ("bap cai", "cai bap", "green cabbage")),
    ("cucumber", "Cucumber", "Dưa leo", "bulk", ("dua leo", "dua chuot", "cucumbers")),
)


def normalize_search(query: str) -> str:
    text = " ".join(normalize(query).split())
    return re.sub(r"\b(?:phi\s*le|fi\s*le|filets?|fillets?)\b", "fillet", text)


def _score(query: str, terms: list[str]) -> float:
    words = query.split()
    best = 0
    for term in terms:
        phrase = normalize_search(term)
        tokens = phrase.split()
        if query == phrase:
            score = 1000
        elif words and all(word in tokens for word in words):
            score = 800 + len(words) / max(1, len(tokens))
        elif words and all(any(token.startswith(word) for token in tokens) for word in words):
            score = 600
        elif words and all(
            any(word == token or (len(word) >= 4 and len(token) >= 4 and
                SequenceMatcher(None, word, token).ratio() >= 0.84) for token in tokens)
            for word in words
        ):
            score = 400
        else:
            score = 0
        best = max(best, score)
    return best


def search_ingredients(query: str, limit: int = 8) -> list[dict]:
    q = normalize_search(query)
    if not q:
        return []
    candidates = []
    for ingredient in INGREDIENTS.values():
        vi, extra = SEARCH_TERMS.get(ingredient["id"], ("", ()))
        candidates.append({**ingredient, "name_vi": vi, "search_terms": list(extra)})
    for kid, name, vi, specialty, aliases in EXTRA_ITEMS:
        candidates.append(dict(id=kid, name=name, name_vi=vi, specialty=specialty,
                               aliases=list(aliases), unit="lb", local_price=None, weee_price=None,
                               search_terms=[]))
    ranked = []
    for item in candidates:
        terms = [item["name"], item["name_vi"], *item["aliases"], *item["search_terms"]]
        score = _score(q, terms)
        if score:
            item = {k: v for k, v in item.items() if k != "search_terms"}
            ranked.append((score, item))
    ranked.sort(key=lambda row: (-row[0], row[1]["name"]))
    return [item for _, item in ranked[:limit]]


def flyer_search_term(ingredient: dict) -> str:
    if ingredient["id"] == "beef_tenderloin":
        return "beef tenderloin"
    return ingredient["name"]
