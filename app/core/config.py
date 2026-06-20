from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env')

    GROQ_API_KEY: Optional[str] = None
    LLM_MODEL: str = "llama-3.1-8b-instant"

    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    VECTOR_SIZE: int = 384

    REDIS_URL: str = "redis://localhost:6379/0"
    QDRANT_URL: str = "http://localhost:6333"
    POSTGRES_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/legalrag"

    JWT_PRIVATE_KEY: Optional[str] = None
    JWT_PUBLIC_KEY: Optional[str] = None
    SECRET_KEY: str = "change-me"

    LANGCHAIN_TRACING_V2: bool = False

    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"


settings = Settings()
