"""LangSmith tracing adapter using official traceable pattern."""

from __future__ import annotations

import os
from contextlib import contextmanager
from functools import lru_cache
from typing import Any, Callable, Dict, Iterator, Optional


_SENSITIVE_KEYS = {
    "api_key",
    "apikey",
    "secret",
    "password",
    "token",
    "authorization",
   "client_secret",
}


def _is_enabled() -> bool:
    """Check if LangSmith tracing is enabled using official detection."""
    try:
        from langsmith import utils as ls_utils
        return ls_utils.tracing_is_enabled() is True
    except Exception:
        return False


def _mask(value: Any) -> str:
    text = str(value)
    if len(text) <= 8:
        return "***"
    return f"{text[:4]}***{text[-2:]}"


def sanitize_for_tracing(value: Any) -> Any:
    """Recursively sanitize payloads before sending to tracing backend."""
    if isinstance(value, dict):
        masked: Dict[str, Any] = {}
        for key, item in value.items():
            lowered = key.lower()
            if any(token in lowered for token in _SENSITIVE_KEYS):
                masked[key] = _mask(item)
            else:
                masked[key] = sanitize_for_tracing(item)
        return masked

    if isinstance(value, list):
        return [sanitize_for_tracing(item) for item in value]

    if isinstance(value, tuple):
        return [sanitize_for_tracing(item) for item in value]

    return value


class TraceSpan:
    """Context manager for one trace span using LangSmith traceable pattern."""

    def __init__(
        self,
        tracer: "LangSmithTracer",
        name: str,
        inputs: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        run_type: str = "chain",
        tags: Optional[list[str]] = None,
    ) -> None:
        self.tracer = tracer
        self.name = name
        self.inputs = sanitize_for_tracing(inputs or {})
        self.metadata = sanitize_for_tracing(metadata or {})
        self.run_type = run_type
        self.tags = tags or []
        self.outputs: Dict[str, Any] = {}
        self._run_fn: Any = None

    def __enter__(self) -> "TraceSpan":
        if not self.tracer.enabled:
            return self
        
        try:
            from langsmith import traceable
            from langsmith.run_helpers import get_current_run_tree
            
            # Use traceable decorator pattern
            @traceable(
                name=self.name,
                run_type=self.run_type,
                tags=self.tags,
                metadata=self.metadata,
                project_name=self.tracer.project,
            )
            def run_span(inputs: Dict[str, Any]) -> Dict[str, Any]:
                # This will be called in __exit__ with outputs
                return self.outputs
            
            # Enter the tracing context
            self._run_fn = run_span
            # Get or create run tree
            _ = get_current_run_tree()
        except Exception:
            pass
        
        return self

    def __exit__(self, exc_type, exc, _tb) -> bool:
        if self._run_fn and self.tracer.enabled:
            try:
                # Complete the span with outputs
                self._run_fn(self.inputs)
            except Exception:
                pass
        return False

    def set_outputs(self, outputs: Dict[str, Any]) -> None:
        self.outputs = sanitize_for_tracing(outputs)


class LangSmithTracer:
    """LangSmith tracer using official traceable pattern."""

    def __init__(self, scope: str) -> None:
        self.scope = scope
        self.enabled = _is_enabled()
        self.project = os.getenv("LANGSMITH_PROJECT", os.getenv("LANGCHAIN_PROJECT", "adobe-aep-cli"))

    @contextmanager
    def span(
        self,
        name: str,
        inputs: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        run_type: str = "chain",
        tags: Optional[list[str]] = None,
    ) -> Iterator[TraceSpan]:
        span = TraceSpan(
            tracer=self,
            name=name,
            inputs=inputs,
            metadata=metadata,
            run_type=run_type,
            tags=tags,
        )
        try:
            span.__enter__()
            yield span
        except Exception as exc:
            span.__exit__(type(exc), exc, None)
            raise
        else:
            span.__exit__(None, None, None)


@lru_cache(maxsize=16)
def get_tracer(scope: str) -> LangSmithTracer:
    """Return cached tracer for a logical scope."""
    return LangSmithTracer(scope=scope)


def trace_call(name: str, scope: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator for tracing sync and async functions using LangSmith traceable."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        if not _is_enabled():
            return func
        
        try:
            from langsmith import traceable
            
            return traceable(
                name=name,
                tags=[scope],
            )(func)
        except Exception:
            return func

    return decorator
