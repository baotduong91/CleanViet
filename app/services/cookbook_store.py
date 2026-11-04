"""User-saved cookbook dishes (imports & favorites) in PostgreSQL."""

from __future__ import annotations

import json

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.dish_photos import remove_cached_photo
from app.services.ingredients import normalize
from app.services.parser import ParsedMeal


async def save_dish(session: AsyncSession, meal: ParsedMeal, source: str = "import") -> dict:
    key = normalize(meal.dish_name)
    payload = meal.model_dump(mode="json")
    await session.execute(
        text(
            """
            INSERT INTO cookbook_saved (dish_key, dish_name, payload, source, updated_at)
            VALUES (:key, :name, CAST(:payload AS jsonb), :source, now())
            ON CONFLICT (dish_key) DO UPDATE
            SET dish_name = EXCLUDED.dish_name,
                payload = EXCLUDED.payload,
                source = EXCLUDED.source,
                updated_at = now()
            """
        ),
        {
            "key": key,
            "name": meal.dish_name,
            "payload": json.dumps(payload),
            "source": source,
        },
    )
    return dict(dish_key=key, dish_name=meal.dish_name, payload=payload, source=source)


async def delete_saved(session: AsyncSession, dish_key: str) -> bool:
    result = await session.execute(
        text("DELETE FROM cookbook_saved WHERE dish_key = :key"),
        {"key": dish_key},
    )
    if result.rowcount > 0:
        remove_cached_photo(dish_key)
        return True
    return False


async def list_saved(session: AsyncSession, q: str = "", limit: int = 40) -> list[dict]:
    qn = normalize(q)
    rows = (
        await session.execute(
            text(
                """
                SELECT dish_key, dish_name, payload, source, updated_at
                FROM cookbook_saved
                ORDER BY updated_at DESC
                LIMIT :limit
                """
            ),
            {"limit": limit},
        )
    ).mappings().all()
    out: list[dict] = []
    for row in rows:
        if qn and qn not in normalize(row["dish_name"]) and qn not in row["dish_key"]:
            continue
        payload = row["payload"]
        if isinstance(payload, str):
            payload = json.loads(payload)
        out.append(
            {
                "id": f"saved:{row['dish_key']}",
                "name_vi": row["dish_name"],
                "name_en": row["dish_name"],
                "display_name": row["dish_name"],
                "category": "favorites",
                "prep_minutes": 0,
                "commute_friendly": True,
                "favorite": True,
                "deletable": True,
                "saved_key": row["dish_key"],
                "source": row["source"],
                "payload": payload,
                "image_url": payload.get("image_url"),
            }
        )
    return out
