from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    TOKEN: str

    REDIS_PASSWORD: str
    REDIS_HOST: str
    REDIS_PORT: int

    MONGODB_URL: str
    MONGO_DB_NAME: str
    MONGODB_COLLECTION: str

    LOG_FILE_PATH: Path = BASE_DIR / "logs/app.log"

    @property
    def redis_url(self) -> str:
        return (
            f"redis://:{self.REDIS_PASSWORD}@"
            f"{self.REDIS_HOST}:{self.REDIS_PORT}"
        )

    model_config = SettingsConfigDict(
        env_file=".env",
        frozen=True
    )
