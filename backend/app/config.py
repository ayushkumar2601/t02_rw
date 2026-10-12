"""Configuration settings for the Autonomous Inbound Voice Agent backend.

Uses pydantic-settings to load settings from environment variables and .env file.
"""

from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable overrides."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Service & Environment
    ENVIRONMENT: str = Field(default="development", description="Runtime environment")
    APP_NAME: str = "Ava Inbound Voice Agent"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # LLM Settings (Groq API)
    GROQ_API_KEY: str = Field(default="", description="Optional Groq API key (free quota)")
    GROQ_MODEL: str = Field(
        default="llama-3.3-70b-versatile",
        description="Active Groq model supporting JSON mode/structured output",
    )
    GROQ_API_BASE_URL: str = Field(
        default="https://api.groq.com/openai/v1",
        description="Groq OpenAI-compatible base URL",
    )
    LLM_TIMEOUT_SECONDS: float = Field(default=8.0, description="Timeout for LLM API requests")
    LLM_MAX_RETRIES: int = Field(default=2, description="Bounded retries for LLM calls")

    # Database
    DATABASE_PATH: str = Field(default="leads.db", description="Path to SQLite database file")

    # Workflow Policies
    MAX_CLARIFICATION_ATTEMPTS: int = Field(
        default=1, description="Maximum clarification retries for ambiguous values (clarify once)"
    )

    # Security & CORS
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        description="Allowed frontend origins for Phase 2",
    )
    MAX_TRANSCRIPT_LENGTH: int = Field(
        default=4000, description="Max allowed length for caller transcript"
    )


settings = Settings()
