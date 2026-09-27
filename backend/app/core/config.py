import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application configuration loaded from environment variables or .env file.
    """
    PROJECT_NAME: str = "JobFit AI - Resume Ranking & Question Generator"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"

    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/jobfit_db"

    # Redis / Celery
    REDIS_URL: str = "redis://localhost:6379/0"

    # AI API Keys
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""

    # Scoring Weights Defaults
    DEFAULT_SKILLS_WEIGHT: float = 0.40
    DEFAULT_SEMANTIC_WEIGHT: float = 0.30
    DEFAULT_EXPERIENCE_WEIGHT: float = 0.20
    DEFAULT_EDUCATION_WEIGHT: float = 0.10

    # Security & Auth
    API_KEY: str = ""

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60

    # App Environment
    ENVIRONMENT: str = "development"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
