from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Patient Assistance Copilot"
    database_url: str = "sqlite:///./pap_copilot.db"
    fpl_year: int = 2026
    default_fpl_limit_percent: float = 400.0
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"


settings = Settings()
