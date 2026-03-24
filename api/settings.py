from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://dirascan:dirascan_dev@localhost:5432/dirascan"
    cors_origins: list[str] = ["http://localhost:3000"]
    api_secret_key: str = "change_me"


settings = Settings()
