from functools import cached_property

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App configuration, overridable via environment / .env."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./aura.db"
    jwt_secret: str = "dev-secret-change-me-in-production"
    jwt_alg: str = "HS256"
    access_token_minutes: int = 60 * 24 * 7  # one week

    # comma-separated list of allowed front-end origins
    cors_origins: str = (
        "http://localhost:5173,"
        "http://localhost:5174,"
        "https://aurabybel.shop,"
        "https://www.aurabybel.shop"
    )

    @cached_property
    def origins(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
