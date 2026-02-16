"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from typing import List, Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # App
    APP_NAME: str = "College Newsletter API"
    DEBUG: bool = False
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_SECRET_KEY: str = "jwt-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/newsletter"
    DATABASE_POOL_SIZE: int = 20
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_POOL_SIZE: int = 50
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173", "http://localhost:8000", "http://127.0.0.1:8000", "null"]
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_PERIOD: int = 60
    
    # Email (SendGrid)
    SENDGRID_API_KEY: Optional[str] = None
    FROM_EMAIL: str = "newsletter@example.com"
    
    # Discord
    DISCORD_WEBHOOK_URL: Optional[str] = None

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
    
    # AI Services - Priority: Groq > OpenAI > HuggingFace > Free > Ollama
    
    # Groq (RECOMMENDED - FREE, Fast, No credit card)
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
