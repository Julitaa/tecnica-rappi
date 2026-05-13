from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    use_mock_llm: bool = True
    data_path: Path = Path("data/source.xlsx")
    cache_path: Path = Path("data/cache.parquet")
    log_level: str = "INFO"


settings = Settings()
