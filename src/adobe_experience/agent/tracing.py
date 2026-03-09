"""LangSmith tracing adapter with safe no-op fallback."""

from __future__ import annotations

import inspect
import os
from contextlib import contextmanager
from datetime import datetime
from functools import lru_cache, wraps
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
    value = os.getenv("LANGSMITH_ENABLED", "false").strip().lower()
    return value in {"1", "true", "yes", "on"}


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
    """Context manager for one trace span."""

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
        self.inputs = inputs or {}
        self.metadata = metadata or {}
        self.run_type = run_type
        self.tags = tags or []
        self.run_id: Any = None
        self.outputs: Dict[str, Any] = {}

    def __enter__(self) -> "TraceSpan":
        self.run_id = self.tracer._start(  # pylint: disable=protected-access
            name=self.name,
            inputs=self.inputs,
            metadata=self.metadata,
            run_type=self.run_type,
            tags=self.tags,
        )
        return self

    def __exit__(self, exc_type, exc, _tb) -> bool:
        self.tracer._finish(  # pylint: disable=protected-access
            run_id=self.run_id,
            outputs=self.outputs,
            error=str(exc) if exc else None,
        )
        return False

    def set_outputs(self, outputs: Dict[str, Any]) -> None:
        self.outputs = outputs


class LangSmithTracer:
    """Best-effort LangSmith tracer with graceful fallback."""

    def __init__(self, scope: str) -> None:
        self.scope = scope
        self.enabled = _is_enabled()
        self.project = os.getenv("LANGSMITH_PROJECT", "adobe-aep-cli")
        self._client: Any = None
        self._stack: list[Any] = []

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

    def _ensure_client(self) -> Any:
        if not self.enabled:
            return None
        if self._client is not None:
            return self._client

        try:
            from langsmith import Client

            self._client = Client()
            return self._client
        except Exception:
            return None

    def _start(
        self,
        name: str,
        inputs: Dict[str, Any],
        metadata: Dict[str, Any],
        run_type: str,
        tags: list[str],
    ) -> Any:
        client = self._ensure_client()
        if client is None:
            return None

        payload: Dict[str, Any] = {
            "name": name,
            "run_type": run_type,
            "inputs": sanitize_for_tracing(inputs),
            "extra": {"metadata": sanitize_for_tracing(metadata)},
            "tags": tags,
            "project_name": self.project,
        }
        if self._stack:
            payload["parent_run_id"] = self._stack[-1]

        run: Any = None
        try:
            run = client.create_run(**payload)
        except Exception:
            return None

        run_id = getattr(run, "id", None)
        if run_id is None and isinstance(run, dict):
            run_id = run.get("id")

        if run_id is not None:
            self._stack.append(run_id)
        return run_id

    def _finish(self, run_id: Any, outputs: Dict[str, Any], error: Optional[str]) -> None:
        if self._stack and self._stack[-1] == run_id:
            self._stack.pop()

        client = self._ensure_client()
        if client is None or run_id is None:
            return

        payload: Dict[str, Any] = {
            "end_time": datetime.utcnow(),
            "outputs": sanitize_for_tracing(outputs or {}),
        }
        if error:
            payload["error"] = error

        try:
            client.update_run(run_id, **payload)
        except Exception:
            return


@lru_cache(maxsize=16)
def get_tracer(scope: str) -> LangSmithTracer:
    """Return cached tracer for a logical scope."""
    return LangSmithTracer(scope=scope)


def trace_call(name: str, scope: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator for tracing sync and async functions with minimal boilerplate."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        if inspect.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                tracer = get_tracer(scope)
                with tracer.span(
                    name=name,
                    inputs={
                        "args": sanitize_for_tracing(list(args[1:])),
                        "kwargs": sanitize_for_tracing(kwargs),
                    },
                    metadata={"scope": scope, "function": func.__name__},
                    run_type="chain",
                ) as span:
                    result = await func(*args, **kwargs)
                    span.set_outputs({"result_type": type(result).__name__})
                    return result

            return async_wrapper

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            tracer = get_tracer(scope)
            with tracer.span(
                name=name,
                inputs={
                    "args": sanitize_for_tracing(list(args[1:])),
                    "kwargs": sanitize_for_tracing(kwargs),
                },
                metadata={"scope": scope, "function": func.__name__},
                run_type="chain",
            ) as span:
                result = func(*args, **kwargs)
                span.set_outputs({"result_type": type(result).__name__})
                return result

        return sync_wrapper

    return decorator