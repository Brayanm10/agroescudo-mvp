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
    whatsapp_template_alert: str | None = Field(default=None, validation_alias=AliasChoices("WHATSAPP_TEMPLATE_ALERT", "WHATSAPP_TEMPLATE_ALERT_NAME", "whatsapp_template_alert"))
    whatsapp_template_language: str = "es"
    telegram_enabled: bool = False
    telegram_bot_token: str | None = None
    notifications_dry_run: bool = Field(default=True, validation_alias=AliasChoices("NOTIFICATIONS_DRY_RUN", "notifications_dry_run"))
    fcm_enabled: bool = False
    firebase_project_id: str | None = None
    firebase_service_account_file: str | None = None
    firebase_service_account_json: str | None = None
    ai_provider: str = "rules"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"
    ai_request_timeout_seconds: int = 30
    ai_enabled: bool = False
    agro_assistant_llm_enabled: bool = Field(default=False, validation_alias=AliasChoices("AGRO_ASSISTANT_LLM_ENABLED", "agro_assistant_llm_enabled"))
    iot_signature_window_seconds: int = 300
    email_enabled: bool = False
    email_provider: str = "resend"
    email_from: str | None = None
    email_api_key: str | None = None
    email_reply_to: str | None = None
    public_app_url: str = "http://localhost:3000"
    storage_provider: str = "local"
    s3_endpoint_url: str | None = None
    s3_bucket: str | None = None
    s3_access_key_id: str | None = None
    s3_secret_access_key: str | None = None
    s3_public_base_url: str | None = None
    device_offline_after_minutes: int = 120
    public_landing_url: str | None = None
    demo_lead_url: str | None = None
    public_whatsapp_url: str | None = None
    support_whatsapp: str | None = None
    support_email: str = "soporte@agroescudo.com"
    support_hours: str = "Lunes a viernes, 08:30-18:00"
    support_timezone: str = "America/La_Paz"
    sentry_enabled: bool = False
    sentry_dsn: str | None = None
    release_version: str = "control-center-v1.0.0"

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

        provider = self.ai_provider.lower().strip()
        if provider not in {"rules", "gemini", "openai"}:
            raise ValueError("AI_PROVIDER must be one of: rules, gemini, openai.")
        if self.ai_enabled and self.agro_assistant_llm_enabled:
            if provider == "gemini" and not self.gemini_api_key:
                raise ValueError("GEMINI_API_KEY is required when AI_PROVIDER=gemini.")
            if provider == "openai" and not self.openai_api_key:
                raise ValueError("OPENAI_API_KEY is required when AI_PROVIDER=openai.")

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
