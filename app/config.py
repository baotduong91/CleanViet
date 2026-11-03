from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://cleanviet:cleanviet_local_change_me@localhost:5436/cleanviet"
    google_places_api_key: str = ""
    allowed_hosts: str = "localhost,127.0.0.1,[::1],testserver"
    vercel_url: str = ""
    vercel_project_production_url: str = ""

    @field_validator("database_url")
    @classmethod
    def async_database_url(cls, value: str) -> str:
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+asyncpg://", 1)
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+asyncpg://", 1)
        return value

    @property
    def trusted_hosts(self) -> list[str]:
        return list(
            dict.fromkeys(
                [host.strip() for host in self.allowed_hosts.split(",") if host.strip()]
                + [
                    host
                    for host in (self.vercel_url, self.vercel_project_production_url)
                    if host
                ]
            )
        )

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
