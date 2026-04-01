"""Configuration settings for the Web UI backend."""

from functools import lru_cache
from typing import Optional

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    # Application
    app_name: str = "Adobe AEP Web UI"
    app_version: str = "0.1.0"
    debug: bool = False
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Security
    secret_key: SecretStr = Field(
        default="change-this-in-production-min-32-chars",
        description="Secret key for JWT token signing (min 32 characters)"
    )
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24 hours
    
    # CORS
    cors_origins: list[str] = Field(
        default=[
            "http://localhost:3000",
            "http://localhost:3001",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
        ],
        description="Allowed CORS origins",
    )
    
    # Web Mode
    web_mode: str = Field(
        default="standalone",
        description="Web server mode: standalone, docker, or dev"
    )
    
    # Database
    database_url: str = Field(
        default="sqlite+aiosqlite:///.adobe/web/aep.db",
        description="Database URL (SQLite for standalone, PostgreSQL for docker)"
    )
    
    # Redis
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis URL for caching (only used in docker/dev mode)"
    )
    
    # Cache
    cache_backend: str = Field(
        default="memory",
        description="Cache backend: memory (standalone) or redis (docker/dev)"
    )
    
    # Adobe Experience Platform
    aep_client_id: Optional[str] = Field(default=None, alias="AEP_CLIENT_ID")
    aep_client_secret: Optional[SecretStr] = Field(default=None, alias="AEP_CLIENT_SECRET")
    aep_org_id: Optional[str] = Field(default=None, alias="AEP_ORG_ID")
    aep_technical_account_id: Optional[str] = Field(default=None, alias="AEP_TECHNICAL_ACCOUNT_ID")
    aep_sandbox_name: str = Field(default="prod", alias="AEP_SANDBOX_NAME")
    aep_tenant_id: Optional[str] = Field(default=None, alias="AEP_TENANT_ID")
    
    # AI Providers
    anthropic_api_key: Optional[SecretStr] = Field(default=None, alias="ANTHROPIC_API_KEY")
    openai_api_key: Optional[SecretStr] = Field(default=None, alias="OPENAI_API_KEY")
    ai_provider: str = Field(default="anthropic", alias="AI_PROVIDER")
    ai_model: Optional[str] = Field(default=None, alias="AI_MODEL")
    
    # Cache TTL (seconds)
    cache_ttl_token: int = 82800  # 23 hours
    cache_ttl_schemas: int = 300  # 5 minutes
    cache_ttl_datasets: int = 300  # 5 minutes
    cache_ttl_ai_responses: int = 604800  # 7 days
    
    # Upload limits
    max_upload_size_mb: int = 500
    upload_chunk_size: int = 1024 * 1024  # 1MB chunks
    
    # Batch monitoring
    batch_poll_interval_seconds: int = 10
    
    # WebSocket
    ws_heartbeat_interval: int = 30
    ws_message_max_size: int = 1024 * 1024  # 1MB
    
    @property
    def max_upload_size_bytes(self) -> int:
        """Get max upload size in bytes."""
        return self.max_upload_size_mb * 1024 * 1024


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
