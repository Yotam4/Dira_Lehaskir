from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://dirascan:dirascan_dev@localhost:5432/dirascan"
    playwright_headless: bool = True
    scraper_request_delay_seconds: float = 2.0
    facebook_email: str = ""
    facebook_password: str = ""
    # Directory for persistent browser profiles (cookies survive between runs).
    # Mount a Docker volume here for real persistence across container restarts.
    cookies_dir: Path = Path("/tmp/dirascan_cookies")


settings = Settings()
