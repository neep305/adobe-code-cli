"""Command metadata system for CLI help organization."""

from enum import Enum
from typing import Dict, Optional, Callable, Any
from functools import wraps


class CommandCategory(str, Enum):
    """Command category classification."""
    
    API = "api"  # Direct AEP API wrappers (CRUD operations)
    ENHANCED = "enhanced"  # AI-powered features and adobe-code enhancements
    HYBRID = "hybrid"  # API operations with significant UX/AI enhancements


class CommandMetadata:
    """Metadata for a CLI command."""
    
    def __init__(
        self,
        category: CommandCategory,
        description: str,
        is_group: bool = False,
    ):
        self.category = category
        self.description = description
        self.is_group = is_group


# Global registry for command metadata
_command_registry: Dict[str, CommandMetadata] = {}


def command_metadata(
    category: CommandCategory,
    description: str,
    is_group: bool = False,
) -> Callable:
    """Decorator to register command metadata.
    
    Args:
        category: Command category (API, ENHANCED, or HYBRID)
        description: Brief description for help text
        is_group: Whether this is a command group (Typer app)
    
    Example:
        @command_metadata(CommandCategory.API, "List all schemas in AEP")
        @schema_app.command("list")
        def list_schemas():
            pass
    """
    def decorator(func: Any) -> Any:
        # Get qualified command name
        command_name = getattr(func, "__name__", str(func))
        
        # Store metadata
        metadata = CommandMetadata(category, description, is_group)
        _command_registry[command_name] = metadata
        
        # Attach metadata to function for easy access
        func._command_metadata = metadata
        
        return func
    
    return decorator


def get_command_metadata(command_name: str) -> Optional[CommandMetadata]:
    """Retrieve metadata for a command.
    
    Args:
        command_name: Name of the command
        
    Returns:
        CommandMetadata if found, None otherwise
    """
    return _command_registry.get(command_name)


def get_category_icon(category: CommandCategory) -> str:
    """Get icon for command category.
    
    Args:
        category: Command category
        
    Returns:
        Unicode icon/emoji string
    """
    icons = {
        CommandCategory.API: "🔵",
        CommandCategory.ENHANCED: "🟢",
        CommandCategory.HYBRID: "⚡",
    }
    return icons.get(category, "")


def get_category_label(category: CommandCategory, lang: str = "en") -> str:
    """Get localized label for command category.
    
    Args:
        category: Command category
        lang: Language code (en, ko)
        
    Returns:
        Localized category label
    """
    labels = {
        "en": {
            CommandCategory.API: "Core AEP API Operations",
            CommandCategory.ENHANCED: "AI-Powered Enhancements",
            CommandCategory.HYBRID: "Hybrid Features (API + AI/UX)",
        },
        "ko": {
            CommandCategory.API: "핵심 AEP API 작업",
            CommandCategory.ENHANCED: "AI 기반 향상 기능",
            CommandCategory.HYBRID: "하이브리드 기능 (API + AI/UX)",
        },
    }
    return labels.get(lang, labels["en"]).get(category, "")


def get_category_description(category: CommandCategory, lang: str = "en") -> str:
    """Get localized description for command category.
    
    Args:
        category: Command category
        lang: Language code (en, ko)
        
    Returns:
        Localized category description
    """
    descriptions = {
        "en": {
            CommandCategory.API: "Direct wrappers around Adobe Experience Platform REST APIs",
            CommandCategory.ENHANCED: "Adobe-code additions with AI intelligence and automation",
            CommandCategory.HYBRID: "API operations enhanced with progress tracking and AI features",
        },
        "ko": {
            CommandCategory.API: "Adobe Experience Platform REST API의 직접 래퍼",
            CommandCategory.ENHANCED: "AI 지능 및 자동화가 포함된 adobe-code 추가 기능",
            CommandCategory.HYBRID: "진행 상황 추적 및 AI 기능이 향상된 API 작업",
        },
    }
    return descriptions.get(lang, descriptions["en"]).get(category, "")


def register_command_group_metadata(
    group_name: str,
    category: CommandCategory,
    description: str,
) -> None:
    """Manually register metadata for a command group.
    
    Args:
        group_name: Name of the command group
        category: Command category
        description: Brief description
    """
    metadata = CommandMetadata(category, description, is_group=True)
    _command_registry[group_name] = metadata
