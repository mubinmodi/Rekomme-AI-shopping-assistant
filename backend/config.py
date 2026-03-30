from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    # AWS
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    AWS_REGION: str
    AWS_S3_BUCKET: str

    # JWT Authentication
    JWT_SECRET_KEY: str
    JWT_ACCESS_TOKEN_EXPIRATION_SECONDS: int = 60 * 60 * 3  # 3 hours
    JWT_REFRESH_TOKEN_EXPIRATION_SECONDS: int = 60 * 60 * 24 * 1  # 1 day
    JWT_ALGORITHM: str = "HS256"

    # Postgres
    POSTGRES_CONN_STRING: str
    POSTGRES_HOSTNAME: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str
    POSTGRES_URI: str | None = None

    # Pinecone
    PINECONE_API_KEY: str
    PINECONE_ENVIRONMENT: str
    PINECONE_INDEX_NAME: str = "damg7245-a4"

    # OpenAI
    OPENAI_API_KEY: str
    OPENAI_EMBEDDINGS_MODEL: str = "text-embedding-3-small"

    # Tavily
    TAVILY_API_KEY: str

    # OxyLabs
    OXYLABS_USERNAME: str
    OXYLABS_PASSWORD: str

    # Fast API config
    APP_TITLE: str = "Rekomme - AI Powered Shopping Assistant"
    APP_VERSION: str = "0.1"

    # Logging Config
    LOG_LEVEL: str = "INFO"
    LOG_FILE_PATH: str = "logs/app.log"
    LOG_MAX_BYTES: int = 2000000  # Default to 2MB
    LOG_BACKUP_COUNT: int = 10


    @model_validator(mode="after")
    def validator(self) -> "Settings":
        self.POSTGRES_URI = self.POSTGRES_CONN_STRING
        return self


@lru_cache
def get_settings():
    return Settings()


settings = get_settings()
