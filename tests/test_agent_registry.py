"""Tests for agent registry and routing contract matching."""

from typing import Any, Dict, List

import pytest

from adobe_experience.agent.contracts import (
    AgentResult,
    AgentResultStatus,
    Capability,
    ExecutionContext,
    SafetyMode,
)
from adobe_experience.agent.registry import AgentRegistry


class DummyAgent:
    """Small test double implementing AgentContract shape."""

    def __init__(self, name: str, capabilities: List[Capability], priority: int, supports: str):
        self.name = name
        self.capabilities = capabilities
        self.priority = priority
        self._supports = supports

    def can_handle(self, context: ExecutionContext) -> bool:
        return self._supports in context.intent

    def plan(self, context: ExecutionContext) -> Dict[str, Any]:
        return {"agent": self.name, "intent": context.intent}

    def execute(self, context: ExecutionContext) -> AgentResult:
        return AgentResult(
            agent_name=self.name,
            status=AgentResultStatus.SUCCESS,
            summary=f"{self.name} executed",
            structured_output={"intent": context.intent},
            confidence=0.9,
        )

    def summarize(self, result: AgentResult) -> str:
        return result.summary


def _context(intent: str) -> ExecutionContext:
    return ExecutionContext(
        request_id="req-1",
        trace_id="trace-1",
        intent=intent,
        input_source="llm",
        safety_mode=SafetyMode.READ_ONLY,
    )


def test_registry_register_and_get() -> None:
    registry = AgentRegistry()
    agent = DummyAgent("data-analysis-agent", [Capability.ANALYSIS], 100, "analyze")

    registry.register(agent)

    found = registry.get("data-analysis-agent")
    assert found is not None
    assert found.name == "data-analysis-agent"
    assert registry.names() == ["data-analysis-agent"]


def test_registry_rejects_duplicate_name() -> None:
    registry = AgentRegistry()
    first = DummyAgent("same", [Capability.ANALYSIS], 100, "analyze")
    second = DummyAgent("same", [Capability.SCHEMA], 80, "schema")

    registry.register(first)
    with pytest.raises(ValueError, match="already registered"):
        registry.register(second)


def test_registry_filters_by_capability() -> None:
    registry = AgentRegistry()
    a = DummyAgent("analysis", [Capability.ANALYSIS], 90, "analyze")
    b = DummyAgent("schema", [Capability.SCHEMA], 95, "schema")
    registry.register(a)
    registry.register(b)

    analysis_agents = registry.list_agents(capability=Capability.ANALYSIS)
    assert [agent.name for agent in analysis_agents] == ["analysis"]


def test_registry_match_is_deterministic_by_priority_then_name() -> None:
    registry = AgentRegistry()
    high = DummyAgent("b-high", [Capability.ANALYSIS], 100, "customer")
    high_same = DummyAgent("a-high", [Capability.ANALYSIS], 100, "customer")
    low = DummyAgent("c-low", [Capability.ANALYSIS], 10, "customer")
    registry.register(high)
    registry.register(high_same)
    registry.register(low)

    matched = registry.match(_context("analyze customer records"), capability=Capability.ANALYSIS)
    assert [agent.name for agent in matched] == ["a-high", "b-high", "c-low"]


def test_registry_match_respects_can_handle() -> None:
    registry = AgentRegistry()
    analysis = DummyAgent("analysis", [Capability.ANALYSIS], 90, "analyze")
    schema = DummyAgent("schema", [Capability.ANALYSIS, Capability.SCHEMA], 80, "schema")
    registry.register(analysis)
    registry.register(schema)

    matched = registry.match(_context("analyze dataset"), capability=Capability.ANALYSIS)
    assert [agent.name for agent in matched] == ["analysis"]
