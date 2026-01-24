"""Configuration management for Adobe AEP Agent."""

from pathlib import Path
from typing import Optional

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class AEPConfig(BaseSettings):
    """Adobe Experience Platform configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # AEP Credentials (OAuth Server-to-Server)
    aep_client_id: str = Field(..., description="AEP API Client ID")
    aep_client_secret: SecretStr = Field(..., description="AEP API Client Secret")
    aep_org_id: str = Field(..., description="IMS Organization ID")
    aep_technical_account_id: str = Field(..., description="Technical Account ID")
    aep_sandbox_name: str = Field(default="prod", description="Sandbox name")
    aep_tenant_id: Optional[str] = Field(default=None, description="AEP Tenant ID")

    # API Configuration
    aep_api_base_url: str = Field(
        default="https://platform.adobe.io",
        description="AEP API base URL",
    )
    aep_ims_token_url: str = Field(
        default="https://ims-na1.adobelogin.com/ims/token/v3",
        description="Adobe IMS token endpoint",
    )

    # AI Provider Configuration
    anthropic_api_key: Optional[SecretStr] = Field(default=None, description="Anthropic API key")
    openai_api_key: Optional[SecretStr] = Field(default=None, description="OpenAI API key")
    ai_provider: str = Field(
        default="auto",
        description="AI provider to use (auto, openai, anthropic)",
    )
    ai_model: str = Field(
        default="claude-3-5-sonnet-20241022",
        description="AI model to use for inference",
    )

    # Rate Limiting
    max_retries: int = Field(default=3, description="Max API retry attempts")
    retry_delay: float = Field(default=1.0, description="Initial retry delay in seconds")
    timeout: float = Field(default=30.0, description="Request timeout in seconds")

    def model_post_init(self, __context) -> None:
        """Load AI credentials from storage if not set in .env"""
        from pathlib import Path
        import json
        
        # Load stored AI credentials
        ai_creds_file = Path.home() / ".adobe" / "ai-credentials.json"
        if not ai_creds_file.exists():
            return
        
        try:
            stored_creds = json.loads(ai_creds_file.read_text(encoding="utf-8"))
        except Exception:
            return
        
        # Priority: .env > stored keys > None
        
        # Load OpenAI key
        if not self.openai_api_key and "openai" in stored_creds:
            self.openai_api_key = SecretStr(stored_creds["openai"]["api_key"])
            # Load model if set and not in config
            if not self.ai_model and stored_creds["openai"].get("model"):
                self.ai_model = stored_creds["openai"]["model"]
        
        # Load Anthropic key
        if not self.anthropic_api_key and "anthropic" in stored_creds:
            self.anthropic_api_key = SecretStr(stored_creds["anthropic"]["api_key"])
            if not self.ai_model and stored_creds["anthropic"].get("model"):
                self.ai_model = stored_creds["anthropic"]["model"]
        
        # Load default provider
        if self.ai_provider == "auto" and "_default" in stored_creds:
            self.ai_provider = stored_creds["_default"]

    @property
    def credentials_path(self) -> Path:
        """Path to local credentials file."""
        return Path.home() / ".adobe" / "credentials.json"


def get_config() -> AEPConfig:
    """Get application configuration."""
    return AEPConfig()
