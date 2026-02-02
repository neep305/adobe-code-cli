"""Configuration management for Adobe AEP Agent."""

import json
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import BaseModel


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
        
        # Load default provider first
        if self.ai_provider == "auto" and "_default" in stored_creds:
            self.ai_provider = stored_creds["_default"]
        
        # Load OpenAI key and model
        if not self.openai_api_key and "openai" in stored_creds:
            self.openai_api_key = SecretStr(stored_creds["openai"]["api_key"])
        
        # Load Anthropic key and model
        if not self.anthropic_api_key and "anthropic" in stored_creds:
            self.anthropic_api_key = SecretStr(stored_creds["anthropic"]["api_key"])
        
        # Load model based on active provider
        if self.ai_model == "claude-3-5-sonnet-20241022":  # Default value
            if self.ai_provider == "openai" and "openai" in stored_creds:
                if stored_creds["openai"].get("model"):
                    self.ai_model = stored_creds["openai"]["model"]
            elif self.ai_provider == "anthropic" and "anthropic" in stored_creds:
                if stored_creds["anthropic"].get("model"):
                    self.ai_model = stored_creds["anthropic"]["model"]

    @property
    def credentials_path(self) -> Path:
        """Path to local credentials file."""
        return Path.home() / ".adobe" / "credentials.json"


def get_config() -> AEPConfig:
    """Get application configuration."""
    return AEPConfig()


class TutorialScenario(str, Enum):
    """Available tutorial scenarios."""

    BASIC = "basic"
    DATA_ENGINEER = "data-engineer"
    MARKETER = "marketer"
    CUSTOM = "custom"


class Milestone(str, Enum):
    """Achievement milestones."""

    FIRST_AUTH = "first-auth"
    FIRST_SCHEMA = "first-schema"
    FIRST_DATASET = "first-dataset"
    FIRST_UPLOAD = "first-upload"
    DATA_100MB = "data-100mb"
    PROFILE_ENABLED = "profile-enabled"
    AI_CONFIGURED = "ai-configured"
    TUTORIAL_COMPLETED = "tutorial-completed"


class OnboardingState(BaseModel):
    """Onboarding progress tracking."""

    scenario: Optional[TutorialScenario] = None
    language: str = "en"
    current_step: int = 0
    completed_steps: List[int] = Field(default_factory=list)
    skipped_steps: List[int] = Field(default_factory=list)
    created_resources: Dict[str, str] = Field(default_factory=dict)
    milestones_achieved: List[Milestone] = Field(default_factory=list)
    tutorial_version: str = "1.0.0"
    share_token: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    last_updated: datetime = Field(default_factory=datetime.now)

    @classmethod
    def load(cls, state_file: Optional[Path] = None) -> "OnboardingState":
        """Load onboarding state from file.

        Args:
            state_file: Path to state file. Defaults to ~/.adobe/onboarding_progress.json

        Returns:
            OnboardingState instance
        """
        if state_file is None:
            state_file = Path.home() / ".adobe" / "onboarding_progress.json"

        if not state_file.exists():
            return cls()

        try:
            with open(state_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return cls(**data)
        except Exception:
            return cls()

    def save(self, state_file: Optional[Path] = None) -> bool:
        """Save onboarding state to file.

        Args:
            state_file: Path to state file. Defaults to ~/.adobe/onboarding_progress.json

        Returns:
            True if saved successfully
        """
        if state_file is None:
            state_file = Path.home() / ".adobe" / "onboarding_progress.json"

        state_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            self.last_updated = datetime.now()
            with open(state_file, "w", encoding="utf-8") as f:
                data = self.model_dump(mode="json")
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception:
            return False

    def mark_step_complete(self, step: int) -> None:
        """Mark a step as completed.

        Args:
            step: Step number
        """
        if step not in self.completed_steps:
            self.completed_steps.append(step)
        if step in self.skipped_steps:
            self.skipped_steps.remove(step)
        self.current_step = step + 1

    def mark_step_skipped(self, step: int) -> None:
        """Mark a step as skipped.

        Args:
            step: Step number
        """
        if step not in self.skipped_steps:
            self.skipped_steps.append(step)
        self.current_step = step + 1

    def add_milestone(self, milestone: Milestone) -> bool:
        """Add an achieved milestone.

        Args:
            milestone: Milestone to add

        Returns:
            True if newly achieved (not already in list)
        """
        if milestone not in self.milestones_achieved:
            self.milestones_achieved.append(milestone)
            return True
        return False

    def is_step_completed(self, step: int) -> bool:
        """Check if step is completed.

        Args:
            step: Step number

        Returns:
            True if completed
        """
        return step in self.completed_steps

    def get_progress_percentage(self, total_steps: int) -> float:
        """Calculate progress percentage.

        Args:
            total_steps: Total number of steps in tutorial

        Returns:
            Progress percentage (0-100)
        """
        if total_steps == 0:
            return 0.0
        return (len(self.completed_steps) / total_steps) * 100


def load_onboarding_state() -> OnboardingState:
    """Load onboarding state.

    Returns:
        OnboardingState instance
    """
    return OnboardingState.load()


def save_onboarding_state(state: OnboardingState) -> bool:
    """Save onboarding state.

    Args:
        state: OnboardingState to save

    Returns:
        True if saved successfully
    """
    return state.save()

