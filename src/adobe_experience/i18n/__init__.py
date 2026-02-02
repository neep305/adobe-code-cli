"""Internationalization (i18n) support."""

import json
from pathlib import Path
from typing import Any, Dict, Optional


class I18n:
    """Internationalization helper."""

    def __init__(self, language: str = "en"):
        """Initialize i18n.

        Args:
            language: Language code (en, ko)
        """
        self.language = language
        self._messages: Dict[str, Any] = {}
        self._load_messages()

    def _load_messages(self) -> None:
        """Load message file for current language."""
        i18n_dir = Path(__file__).parent
        message_file = i18n_dir / f"{self.language}.json"

        if not message_file.exists():
            # Fallback to English
            self.language = "en"
            message_file = i18n_dir / "en.json"

        try:
            with open(message_file, "r", encoding="utf-8") as f:
                self._messages = json.load(f)
        except Exception:
            self._messages = {}

    def get(self, key: str, **kwargs) -> str:
        """Get translated message.

        Args:
            key: Message key (dot-notation, e.g., "onboarding.welcome")
            **kwargs: Format arguments

        Returns:
            Translated message
        """
        keys = key.split(".")
        value = self._messages

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return key  # Return key if not found

        if value is None:
            return key

        if isinstance(value, str) and kwargs:
            try:
                return value.format(**kwargs)
            except Exception:
                return value

        return str(value)

    def change_language(self, language: str) -> None:
        """Change current language.

        Args:
            language: Language code
        """
        self.language = language
        self._load_messages()


# Global i18n instance
_i18n: Optional[I18n] = None


def get_i18n(language: Optional[str] = None) -> I18n:
    """Get i18n instance.

    Args:
        language: Language code (if None, uses existing instance)

    Returns:
        I18n instance
    """
    global _i18n

    if _i18n is None or (language and language != _i18n.language):
        _i18n = I18n(language or "en")

    return _i18n


def t(key: str, language: Optional[str] = None, **kwargs) -> str:
    """Translate message (shorthand).

    Args:
        key: Message key
        language: Language code (optional)
        **kwargs: Format arguments

    Returns:
        Translated message
    """
    i18n = get_i18n(language)
    return i18n.get(key, **kwargs)
