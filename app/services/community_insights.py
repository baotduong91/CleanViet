"""Official Google Places review sampling. No provider content is persisted."""

from urllib.parse import quote
from datetime import datetime, timedelta, timezone
import httpx
from app.config import settings
from app.services.ingredients import normalize
from app.services.recommender import STORES

KEYWORDS = [
    "fresh fish",
    "produce",
    "lines",
    "cashier",
    "smell",
    "price increase",
    "squid",
    "seafood",
    "rau",
    "ca tuoi",
    "muc",
]


def analyze_reviews(reviews, now=None):
    now = now or datetime.now(timezone.utc)
    found = []
    for r in reviews:
        try:
            published = datetime.fromisoformat(
                r.get("publishTime", "").replace("Z", "+00:00")
            )
        except ValueError:
            continue
        if published.tzinfo is None:
            continue
        content = r.get("text", {}).get("text", "")
        topics = [k for k in KEYWORDS if k in normalize(content)]
        if topics and now - timedelta(days=30) <= published <= now:
            author = r.get("authorAttribution", {})
            found.append(
                dict(
                    author=author.get("displayName", "Google reviewer"),
                    author_url=author.get("uri"),
                    published_at=published.isoformat(),
                    topics=topics,
                    excerpt=content[:140],
                    url=r.get("googleMapsUri"),
                )
            )
    return sorted(found, key=lambda r: r["published_at"], reverse=True)


async def fetch_insights(store_id):
    store = STORES[store_id]
    maps_url = f"https://www.google.com/maps/search/?api=1&query={quote(store['query'] or store['name'])}"
    if not settings.google_places_api_key or not store["query"]:
        return dict(
            status="not_configured",
            url=maps_url,
            summary="Review summaries are unavailable. Use View store reviews to open Google Maps.",
            reviews=[],
        )
    try:
        async with httpx.AsyncClient(timeout=12) as client:
            r = await client.post(
                "https://places.googleapis.com/v1/places:searchText",
                headers={
                    "X-Goog-Api-Key": settings.google_places_api_key,
                    "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.googleMapsUri,places.reviews",
                },
                json={"textQuery": store["query"], "pageSize": 1},
            )
            r.raise_for_status()
            places = r.json().get("places", [])
        if not places:
            return dict(
                status="no_match", summary="No matching place returned. Open Google Maps to select a store.", reviews=[], url=maps_url
            )
        place = places[0]
        reviews = analyze_reviews(place.get("reviews", []))
        return dict(
            status="live",
            provider="Google Maps",
            place_name=place.get("displayName", {}).get("text"),
            address=place.get("formattedAddress"),
            url=place.get("googleMapsUri"),
            checked_at=datetime.now(timezone.utc).isoformat(),
            summary=f"{len(reviews)} relevant review(s) in the last 30 days. Limited provider sample; reviews cannot confirm today’s stock or lowest price.",
            reviews=reviews,
        )
    except (httpx.HTTPError, ValueError):
        return dict(
            status="unavailable",
            url=maps_url,
            summary="Review provider unavailable; check stock with the store.",
            reviews=[],
        )
