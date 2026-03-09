"""Tests for LangSmith tracing adapter behavior."""

from __future__ import annotations

from typing import Any, Dict

import pytest

from adobe_experience.agent.tracing import LangSmithTracer, sanitize_for_tracing, trace_call


class FakeClient:
    def __init__(self) -> None:
        self.created: list[Dict[str, Any]] = []
        self.updated: list[Dict[str, Any]] = []

    def create_run(self, **kwargs):
        self.created.append(kwargs)
        return {"id": f"run-{len(self.created)}"}

    def update_run(self, run_id, **kwargs):
        self.updated.append({"run_id": run_id, **kwargs})


def test_sanitize_for_tracing_masks_sensitive_values() -> None:
    payload = {
        "api_key": "abcd1234xyz",
        "nested": {"token": "tok-123456", "ok": "value"},
    }

    cleaned = sanitize_for_tracing(payload)
    assert cleaned["api_key"] != "abcd1234xyz"
    assert cleaned["nested"]["token"] != "tok-123456"
    assert cleaned["nested"]["ok"] == "value"


def test_tracer_span_records_when_enabled(monkeypatch) -> None:
    monkeypatch.setenv("LANGSMITH_ENABLED", "true")

    tracer = LangSmithTracer(scope="unit-test")
    fake = FakeClient()
    tracer._client = fake

    with tracer.span("unit.span", inputs={"k": "v"}, metadata={"m": 1}) as span:
        span.set_outputs({"done": True})

    assert len(fake.created) == 1
    assert len(fake.updated) == 1
    assert fake.updated[0]["outputs"]["done"] is True


def test_tracer_noop_when_disabled(monkeypatch) -> None:
    monkeypatch.setenv("LANGSMITH_ENABLED", "false")

    tracer = LangSmithTracer(scope="unit-test")
    with tracer.span("noop", inputs={"x": 1}):
        value = 42

    assert value == 42


@pytest.mark.asyncio
async def test_trace_call_decorator_async(monkeypatch) -> None:
    monkeypatch.setenv("LANGSMITH_ENABLED", "false")

    class Service:
        @trace_call("service.compute", scope="unit-test")
        async def compute(self, x: int) -> int:
            return x + 1

    result = await Service().compute(1)
    assert result == 2
