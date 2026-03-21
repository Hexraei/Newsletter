"""Application configuration using Pydantic Settings."""

import secrets
from functools import lru_cache
from typing import List, Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings

_INSECURE_DEFAULTS = {
    "your-secret-key-change-in-production",
    "jwt-secret-key-change-in-production",
}


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # App
    APP_NAME: str = "College Newsletter API"
    ENVIRONMENT: str = "development"  # development, staging, production
    DEBUG: Optional[bool] = None
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    
    # Security — no defaults; must be set via .env or environment
    SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_SECRET_KEY: str = "jwt-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str, info) -> str:
        if v in _INSECURE_DEFAULTS:
            import os
            env = os.getenv("ENVIRONMENT", "development")
            if env != "development":
                raise ValueError(
                    f"SECRET_KEY must be changed from default in {env} mode. "
                    'Generate one with: python -c "import secrets; print(secrets.token_urlsafe(32))"'
                )
            import warnings
            warnings.warn(
                "SECRET_KEY is using an insecure placeholder. "
                "Set a strong random secret in .env before deploying.",
                stacklevel=2,
            )
        if len(v) < 16:
            raise ValueError("SECRET_KEY must be at least 16 characters")
        return v

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def validate_jwt_secret_key(cls, v: str, info) -> str:
        if v in _INSECURE_DEFAULTS:
            import os
            env = os.getenv("ENVIRONMENT", "development")
            if env != "development":
                raise ValueError(
                    f"JWT_SECRET_KEY must be changed from default in {env} mode. "
                    'Generate one with: python -c "import secrets; print(secrets.token_urlsafe(32))"'
                )
            import warnings
            warnings.warn(
                "JWT_SECRET_KEY is using an insecure placeholder. "
                "Set a strong random secret in .env before deploying.",
                stacklevel=2,
            )
        if len(v) < 16:
            raise ValueError("JWT_SECRET_KEY must be at least 16 characters")
        return v

    @field_validator("DEBUG", mode="before")
    @classmethod
    def auto_debug(cls, v, info):
        # If not explicitly set, derive from ENVIRONMENT
        if v is None:
            env = info.data.get("ENVIRONMENT", "development") if info.data else "development"
            return env == "development"
        return v

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            import json
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [s.strip() for s in v.split(",")]
        return v
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/newsletter"
    DATABASE_POOL_SIZE: int = 20
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_POOL_SIZE: int = 50
    
    # CORS — explicit allowlist only
    CORS_ORIGINS: List[str] = ["http://localhost:8000", "http://127.0.0.1:8000"]

    # Cookie settings (for httpOnly JWT cookies)
    COOKIE_DOMAIN: Optional[str] = None  # None = current domain; set for cloud
    COOKIE_SECURE: bool = False  # True in production (HTTPS only)
    COOKIE_SAMESITE: str = "lax"  # lax for OAuth compat

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # "json" for production, "text" for development
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_PERIOD: int = 60
    
    # Email (SendGrid)
    SENDGRID_API_KEY: Optional[str] = None
    FROM_EMAIL: str = "newsletter@example.com"
    
    # Discord
    DISCORD_WEBHOOK_URL: Optional[str] = None

    # Supabase (optional for lite feed source/cache)
    SUPABASE_URL: Optional[str] = None
    SUPABASE_ANON_KEY: Optional[str] = None
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None
    SUPABASE_SCRAPED_TABLE: str = "scraped_items"
    SUPABASE_RANKED_CACHE_TABLE: str = "ranked_sections_cache"
    SUPABASE_CACHE_KEY: str = "lite-all-sections"
    SUPABASE_CACHE_TTL_MINUTES: int = 15
    SUPABASE_FETCH_LIMIT: int = 400

    # Twitter/X (bird CLI)
    BIRD_AUTH_TOKEN: Optional[str] = None
    BIRD_CT0: Optional[str] = None
    AUTH_TOKEN: Optional[str] = None
    CT0: Optional[str] = None
    BIRD_CHROME_PROFILE: Optional[str] = None
    BIRD_FIREFOX_PROFILE: Optional[str] = None

    # File Storage
    STORAGE_ENDPOINT: Optional[str] = None
    STORAGE_ACCESS_KEY: Optional[str] = None
    STORAGE_SECRET_KEY: Optional[str] = None
    STORAGE_BUCKET: str = "newsletter"
    STORAGE_TYPE: str = "local"
    STORAGE_PATH: str = "./data/storage"

    # Image providers
    UNSPLASH_ACCESS_KEY: Optional[str] = None
    UNSPLASH_SECRET_KEY: Optional[str] = None
    UNSPLASH_HOURLY_LIMIT: int = 4800

    # Relevance policy (TN/India first)
    RELEVANCE_STRICT_MODE: bool = True
    RELEVANCE_MIN_GEO_SCORE: int = 45
    RELEVANCE_MIN_ACTIONABILITY_SCORE: int = 25
    RELEVANCE_MIN_ACTIONABILITY_SCORE_REDDIT: int = 38
    RELEVANCE_MIN_KNOWLEDGE_SCORE: int = 32
    RELEVANCE_GLOBAL_ACTIONABILITY_OVERRIDE: int = 65
    RELEVANCE_GLOBAL_KNOWLEDGE_OVERRIDE: int = 72
    RELEVANCE_PREFILTER_ENABLED: bool = True
    RELEVANCE_REDDIT_MAX_PER_SUBREDDIT: int = 8
    RELEVANCE_REDDIT_MAX_TOTAL_ITEMS: int = 60
    
    # AI Services - Priority: Gemini > Groq > OpenAI > HuggingFace > Free > Ollama
    
    # Gemini (Fast, generous free tier)
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-3.1-flash-lite-preview"
    
    # Groq (FREE, Fast, No credit card)
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "llama-3.1-8b-instant"
    
    # OpenAI (Best quality, paid)
    OPENAI_API_KEY: Optional[str] = None
    
    # Hugging Face (FREE tier available)
    HUGGINGFACE_API_KEY: Optional[str] = None
    
    # Azure OpenAI (Enterprise)
    AZURE_OPENAI_ENDPOINT: Optional[str] = None
    AZURE_OPENAI_KEY: Optional[str] = None
    AZURE_OPENAI_DEPLOYMENT: Optional[str] = None
    
    # Ollama (Local, FREE, slow)
    USE_LOCAL_AI: bool = False
    OLLAMA_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
