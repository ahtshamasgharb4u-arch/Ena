import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    secret_key: str
    database_url: str
    llm_provider: str
    openai_api_key: str | None
    openai_model: str
    anthropic_api_key: str | None
    anthropic_model: str
    dataforseo_login: str | None
    dataforseo_password: str | None
    dataforseo_location_code: int
    dataforseo_language_code: str

    @staticmethod
    def from_env() -> "Settings":
        return Settings(
            secret_key=os.environ.get("SECRET_KEY", "change-me"),
            database_url=os.environ.get("DATABASE_URL", "sqlite:///dev.db"),
            llm_provider=os.environ.get("LLM_PROVIDER", "openai").strip().lower(),
            openai_api_key=os.environ.get("OPENAI_API_KEY"),
            openai_model=os.environ.get("OPENAI_MODEL", "gpt-4o"),
            anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY"),
            anthropic_model=os.environ.get("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest"),
            dataforseo_login=os.environ.get("DATAFORSEO_LOGIN"),
            dataforseo_password=os.environ.get("DATAFORSEO_PASSWORD"),
            dataforseo_location_code=int(os.environ.get("DATAFORSEO_LOCATION_CODE", "2840")),
            dataforseo_language_code=os.environ.get("DATAFORSEO_LANGUAGE_CODE", "en"),
        )

