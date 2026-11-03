from collections.abc import AsyncIterator
import ssl
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.config import settings

database_url = make_url(settings.database_url)
connect_args = {}
sslmode = database_url.query.get("sslmode")
if sslmode:
    database_url = database_url.difference_update_query(["sslmode", "channel_binding"])
    if sslmode != "disable":
        connect_args["ssl"] = ssl.create_default_context()
engine = create_async_engine(
    database_url,
    pool_pre_ping=True,
    pool_size=2,
    max_overflow=0,
    connect_args=connect_args,
)

Session = async_sessionmaker(engine, expire_on_commit=False)


async def session_dependency() -> AsyncIterator[AsyncSession]:
    async with Session() as session:
        async with session.begin():
            yield session
