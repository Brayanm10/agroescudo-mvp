from functools import lru_cache

from pydantic import AliasChoices, Field, model_validator
from sqlalchemy.engine.url import make_url
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AgroEscudo API"
    environment: str = "local"
    database_url: str = "sqlite:///./agroescudo_dev.db"
    cors_origins: str = Field(default="", validation_alias=AliasChoices("CORS_ORIGINS", "cors_origins"))
    secret_key: str = Field(
        default="change-me-in-production",
        validation_alias=AliasChoices("JWT_SECRET", "SECRET_KEY"),
    )
    access_token_expire_minutes: int = 480
    whatsapp_enabled: bool = False
    whatsapp_access_token: str | None = None
    whatsapp_phone_number_id: str | None = None
    whatsapp_api_version: str = "v20.0"
    whatsapp_template_alert: str | None = None
    telegram_enabled: bool = False
    telegram_bot_token: str | None = None
    fcm_enabled: bool = False
    firebase_project_id: str | None = None
    firebase_service_account_file: str | None = None
    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"
    ai_enabled: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore", populate_by_name=True)

    @model_validator(mode="after")
    def validate_environment_settings(self) -> "Settings":
        environment = self.environment.lower().strip()
        if environment not in {"local", "demo", "production"}:
            raise ValueError("ENVIRONMENT must be one of: local, demo, production.")

        if environment in {"demo", "production"}:
            if not self.database_url.strip():
                raise ValueError("DATABASE_URL is required when ENVIRONMENT is demo or production.")
            if self.database_backend == "sqlite":
                raise ValueError("SQLite is only allowed in local environment. Use PostgreSQL for demo or production.")
            if self.secret_key.strip() in {"", "change-me-in-production", "default", "secret"}:
                raise ValueError("JWT_SECRET must be a secure non-default value in demo or production.")

        if environment == "production":
            origins = self.cors_origin_list
            if not origins or "*" in origins:
                raise ValueError("CORS_ORIGINS must list explicit origins in production. '*' is not allowed.")

        return self

    @property
    def database_backend(self) -> str:
        driver_name = make_url(self.database_url).drivername
        if driver_name.startswith("sqlite"):
            return "sqlite"
        if driver_name.startswith("postgresql"):
            return "postgresql"
        return driver_name

    @property
    def cors_origin_list(self) -> list[str]:
        configured_origins = [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
        environment = self.environment.lower().strip()

        if environment == "local":
            local_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
            return list(dict.fromkeys([*local_origins, *configured_origins]))

        if environment == "demo" and not configured_origins:
            return ["*"]

        return configured_origins


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
