"""Apply the additive migration without changing existing household records."""

import asyncio
from pathlib import Path
import asyncpg
from app.config import settings


async def migrate():
    connection = await asyncpg.connect(
        settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    )
    try:
        await connection.execute(
            (Path(__file__).parent / "migrations/002_meal_canvas.sql").read_text()
        )
    finally:
        await connection.close()
    print("Meal canvas migration applied.")


if __name__ == "__main__":
    asyncio.run(migrate())
