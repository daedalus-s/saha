from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_key: str = "dev-app-key"
    search_provider: str = "mock"
    google_cse_key: str | None = None
    google_cse_cx: str | None = None
    brave_api_key: str | None = None
    llm_model: str = "none"
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    gemini_api_key: str | None = None
    cache_dir: str = "./.cache"
    cors_origins: str = "*"
    log_level: str = "INFO"
    docs_dir: str = ""

    @property
    def llm_enabled(self) -> bool:
        model = (self.llm_model or "").strip().lower()
        return model not in ("", "none", "off", "false")

    @property
    def cors_origin_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
