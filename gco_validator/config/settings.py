"""
Configuration settings for the GEO Content Quality Validator
"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file"""
    
    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    RELOAD: bool = True
    DEBUG: bool = False
    
    # CORS settings
    ALLOWED_ORIGINS: List[str] = ["*"]
    
    # Database settings
    DATABASE_URL: str = "sqlite:///./gco_validator.db"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_POOL_TIMEOUT: int = 30
    
    # Logging settings
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_FILE: str = "logs/app.log"
    
    # AI Platform settings
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    GOOGLE_API_KEY: str = ""
    
    # Test execution settings
    MAX_CONCURRENT_TESTS: int = 10
    TEST_TIMEOUT: int = 30
    RETRY_ATTEMPTS: int = 3
    
    class Config:
        env_file = ".env"


settings = Settings()