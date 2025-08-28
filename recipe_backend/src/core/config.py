from functools import lru_cache
from pydantic import BaseModel, Field
import os
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()


class Settings(BaseModel):
    """Application configuration settings loaded from environment variables."""

    # FastAPI app info
    APP_NAME: str = Field(default="Recipe Hub Backend", description="Application name")
    APP_VERSION: str = Field(default="0.1.0", description="Application version")
    APP_DESCRIPTION: str = Field(
        default="Provides recipe data, user management, and API endpoints for the frontend.",
        description="Application description",
    )

    # Database
    DATABASE_URL: str = Field(
        default=os.getenv("DATABASE_URL", "sqlite:///./data.db"),
        description="SQLAlchemy database URL, e.g., postgresql+psycopg2://user:pass@host:5432/db",
    )

    # Security
    SECRET_KEY: str = Field(
        default=os.getenv("SECRET_KEY", "change-this-in-production"),
        description="Secret key for token generation",
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")),
        description="Access token expiry in minutes",
    )
    ALGORITHM: str = Field(
        default=os.getenv("ALGORITHM", "HS256"),
        description="JWT signing algorithm",
    )

    # CORS
    CORS_ALLOW_ORIGINS: list[str] = Field(
        default_factory=lambda: os.getenv("CORS_ALLOW_ORIGINS", "*").split(","),
        description="Comma separated list of allowed origins",
    )
    CORS_ALLOW_CREDENTIALS: bool = Field(
        default=os.getenv("CORS_ALLOW_CREDENTIALS", "true").lower() == "true",
        description="Allow credentials",
    )
    CORS_ALLOW_METHODS: list[str] = Field(
        default_factory=lambda: os.getenv("CORS_ALLOW_METHODS", "*").split(","),
        description="Allowed methods",
    )
    CORS_ALLOW_HEADERS: list[str] = Field(
        default_factory=lambda: os.getenv("CORS_ALLOW_HEADERS", "*").split(","),
        description="Allowed headers",
    )


# PUBLIC_INTERFACE
@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
