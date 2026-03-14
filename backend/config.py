from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://f1user:f1password@localhost:5432/f1db"
    fastf1_cache_dir: str = "data/fastf1_cache"
    anthropic_api_key: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
