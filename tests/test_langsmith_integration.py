"""Tests for LangSmith tracing integration."""

import os
from typing import Any, Dict

import pytest

from adobe_experience.agent.tracing import (
    LangSmithTracer,
    get_tracer,
    sanitize_for_tracing,
    trace_call,
)


def test_sanitize_removes_sensitive_keys() -> None:
    """Verify sensitive keys are masked in trace payloads."""
    payload = {
        "api_key": "sk-12345678901234567890",
        "client_secret": "secret-value-here",
        "email": "user@example.com",
        "nested": {
            "password": "my-password",
            "safe_field": "visible",
        },
    }

    sanitized = sanitize_for_tracing(payload)

    assert sanitized["api_key"] == "sk-1***90"
    assert sanitized["client_secret"] == "secr***re"
    assert sanitized["email"] == "user@example.com"  # Not masked
    assert sanitized["nested"]["password"] == "my-p***rd"  # Actual masking format
    assert sanitized["nested"]["safe_field"] == "visible"


def test_tracer_disabled_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify LangSmith tracing is opt-in."""
    monkeypatch.delenv("LANGSMITH_ENABLED", raising=False)
    tracer = LangSmithTracer(scope="test")
    assert tracer.enabled is False


def test_tracer_span_no_op_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify span context manager works without LangSmith enabled."""
    monkeypatch.setenv("LANGSMITH_ENABLED", "false")
    tracer = get_tracer("test")

    with tracer.span(
        "test-operation",
        inputs={"key": "value"},
        metadata={"component": "test"},
    ) as span:
        span.set_outputs({"result": "success"})

    # Should not raise any errors even though LangSmith is disabled


def test_tracer_enabled_flag_parsing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify LANGSMITH_ENABLED flag is parsed correctly."""
    test_cases = [
        ("true", True),
        ("True", True),
        ("TRUE", True),
        ("1", True),
        ("yes", True),
        ("on", True),
        ("false", False),
        ("False", False),
        ("0", False),
        ("no", False),
        ("", False),
        ("invalid", False),
    ]

    for value, expected in test_cases:
        monkeypatch.setenv("LANGSMITH_ENABLED", value)
        tracer = LangSmithTracer(scope="test")
        assert tracer.enabled == expected, f"Failed for LANGSMITH_ENABLED={value}"


def test_get_tracer_returns_cached_instance() -> None:
    """Verify get_tracer returns same instance for same scope."""
    tracer1 = get_tracer("my-scope")
    tracer2 = get_tracer("my-scope")
    assert tracer1 is tracer2  # Same cached instance


def test_get_tracer_different_scopes() -> None:
    """Verify different scopes return different tracer instances."""
    tracer1 = get_tracer("scope-a")
    tracer2 = get_tracer("scope-b")
    assert tracer1 is not tracer2
    assert tracer1.scope == "scope-a"
    assert tracer2.scope == "scope-b"


def test_trace_call_decorator_sync() -> None:
    """Verify trace_call decorator works with sync functions."""

    @trace_call(name="test_function", scope="decorator")
    def add_numbers(a: int, b: int) -> int:
        return a + b

    result = add_numbers(5, 3)
    assert result == 8  # Function still works correctly


@pytest.mark.asyncio
async def test_trace_call_decorator_async() -> None:
    """Verify trace_call decorator works with async functions."""

    @trace_call(name="async_test", scope="decorator")
    async def fetch_data(value: str) -> Dict[str, Any]:
        return {"data": value}

    result = await fetch_data("test-value")
    assert result == {"data": "test-value"}


def test_tracer_graceful_fallback_without_langsmith_package(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify tracer works even if langsmith package import fails."""
    monkeypatch.setenv("LANGSMITH_ENABLED", "true")

    # Create new tracer (will try to import but may fail)
    tracer = LangSmithTracer(scope="fallback-test")

    # Should not raise even if langsmith is not available
    with tracer.span("test-span", inputs={"test": "data"}) as span:
        span.set_outputs({"result": "ok"})


def test_sanitize_handles_nested_lists() -> None:
    """Verify sanitization works with nested list structures."""
    payload = {
        "items": [
            {"api_key": "key1", "name": "item1"},
            {"api_key": "key2", "name": "item2"},
        ],
        "normal_list": ["value1", "value2"],  # Non-sensitive list
    }

    sanitized = sanitize_for_tracing(payload)

    assert sanitized["items"][0]["api_key"] == "***"
    assert sanitized["items"][0]["name"] == "item1"
    assert sanitized["items"][1]["api_key"] == "***"
    assert sanitized["normal_list"] == ["value1", "value2"]


def test_sanitize_handles_empty_values() -> None:
    """Verify sanitization handles empty or None values."""
    payload = {
        "api_key": "",
        "password": None,
        "normal_field": "value",
    }

    sanitized = sanitize_for_tracing(payload)

    assert sanitized["api_key"] == "***"
    assert sanitized["password"] == "***"
    assert sanitized["normal_field"] == "value"


def test_tracer_span_captures_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify span captures and propagates errors correctly."""
    monkeypatch.setenv("LANGSMITH_ENABLED", "false")
    tracer = get_tracer("error-test")

    with pytest.raises(ValueError, match="test error"):
        with tracer.span("failing-operation") as span:
            span.set_outputs({"status": "starting"})
            raise ValueError("test error")


def test_project_name_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify project name can be customized via environment variable."""
    monkeypatch.setenv("LANGSMITH_PROJECT", "custom-project-name")
    tracer = LangSmithTracer(scope="test")
    assert tracer.project == "custom-project-name"


def test_project_name_default() -> None:
    """Verify default project name is used when env var not set."""
    # Temporarily clear env var if present
    original = os.environ.pop("LANGSMITH_PROJECT", None)
    try:
        tracer = LangSmithTracer(scope="test")
        assert tracer.project == "adobe-aep-cli"
    finally:
        if original:
            os.environ["LANGSMITH_PROJECT"] = original
