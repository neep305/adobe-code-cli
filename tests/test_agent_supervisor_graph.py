"""Tests for supervisor routing and confidence gate behavior."""

from typing import Any, Dict, List

from adobe_experience.agent.contracts import (
    AgentResult,
    AgentResultStatus,
    Capability,
    ExecutionContext,
)
from adobe_experience.agent.registry import AgentRegistry
from adobe_experience.agent.supervisor_graph import SupervisorGraphRunner


class DummyAgent:
    """Simple test agent implementing contract shape."""

    def __init__(
        self,
        name: str,
        capabilities: List[Capability],
        priority: int,
        keyword: str,
        confidence: float,
    ) -> None:
        self.name = name
        self.capabilities = capabilities
        self.priority = priority
        self.keyword = keyword
        self._confidence = confidence

    def can_handle(self, context: ExecutionContext) -> bool:
        return self.keyword in context.intent.lower() or self.keyword == "*"

    def plan(self, context: ExecutionContext) -> Dict[str, Any]:
        return {"agent": self.name}

    def execute(self, context: ExecutionContext) -> AgentResult:
        return AgentResult(
            agent_name=self.name,
            status=AgentResultStatus.SUCCESS,
            summary=f"{self.name} ok",
            confidence=self._confidence,
            next_actions=[f"review:{self.name}"],
        )

    def summarize(self, result: AgentResult) -> str:
        return result.summary


def _runner() -> SupervisorGraphRunner:
    registry = AgentRegistry()
    registry.register(DummyAgent("data-analysis-agent", [Capability.ANALYSIS], 100, "analy", 0.8))
    registry.register(DummyAgent("schema-mapping-agent", [Capability.SCHEMA], 90, "schema", 0.9))
    return SupervisorGraphRunner(registry)


def test_analysis_route_selects_analysis_agent() -> None:
    runner = _runner()
    state = runner.run({"request_id": "r1", "intent": "analyze customer data"})

    assert state.route == "analysis"
    assert state.selected_agents == ["data-analysis-agent"]
    assert state.confidence == 0.8
    assert state.final_summary is not None


def test_mixed_route_executes_analysis_then_schema() -> None:
    runner = _runner()
    state = runner.run({"request_id": "r2", "intent": "analyze and generate schema"})

    assert state.route == "mixed"
    assert state.selected_agents == ["data-analysis-agent", "schema-mapping-agent"]
    assert len(state.results) == 2


def test_schema_route_runs_analysis_first_when_missing_analysis_payload() -> None:
    runner = _runner()
    state = runner.run({"request_id": "r3", "intent": "schema mapping for customer profile"})

    assert state.route == "schema"
    assert state.selected_agents == ["data-analysis-agent", "schema-mapping-agent"]


def test_unsupported_route_returns_fallback_summary() -> None:
    runner = _runner()
    state = runner.run({"request_id": "r4", "intent": "hello world"})

    assert state.route == "unsupported"
    assert state.results == {}
    assert state.final_summary == "No executable agent path found"


def test_confidence_gate_warns_when_medium_confidence() -> None:
    registry = AgentRegistry()
    registry.register(DummyAgent("data-analysis-agent", [Capability.ANALYSIS], 100, "analy", 0.6))
    runner = SupervisorGraphRunner(registry)

    state = runner.run({"request_id": "r5", "intent": "analyze this dataset"})

    assert any("Medium confidence" in warning for warning in state.warnings)


def test_confidence_gate_warns_when_low_confidence() -> None:
    registry = AgentRegistry()
    registry.register(DummyAgent("data-analysis-agent", [Capability.ANALYSIS], 100, "analy", 0.4))
    runner = SupervisorGraphRunner(registry)

    state = runner.run({"request_id": "r6", "intent": "analyze this dataset"})

    assert any("Low confidence" in warning for warning in state.warnings)


def test_supervisor_auto_registers_default_agents() -> None:
    registry = AgentRegistry()
    runner = SupervisorGraphRunner(registry)

    # Built-ins should be auto-registered during runner initialization.
    assert "data-analysis-agent" in registry.names()
    assert "schema-mapping-agent" in registry.names()

    state = runner.run(
        {
            "request_id": "r7",
            "intent": "analyze customer records and suggest schema mapping",
            "payload": {
                "records": [
                    {"customer_id": "c1", "email": "a@x.com", "country": "US"},
                    {"customer_id": "c2", "email": "b@x.com", "country": "KR"},
                ]
            },
        }
    )
    assert state.route == "mixed"
    assert len(state.results) == 2


class StubToolBridge:
    def __init__(self, success: bool = True) -> None:
        self.success = success
        self.calls = []

    def execute(self, tool_calls):
        self.calls = list(tool_calls)
        return [
            {
                "tool_name": "aep_dataset_list",
                "success": self.success,
                "output": "ok" if self.success else None,
                "error": None if self.success else "boom",
            }
        ]


def test_supervisor_executes_tool_calls_before_routing() -> None:
    bridge = StubToolBridge(success=True)
    runner = SupervisorGraphRunner(AgentRegistry(), tool_bridge=bridge)

    state = runner.run(
        {
            "request_id": "r8",
            "intent": "analyze dataset quality",
            "tool_calls": [{"name": "aep_dataset_list", "parameters": {"limit": 5}}],
        }
    )

    assert len(bridge.calls) == 1
    assert state.context is not None
    assert "tool_results" in state.context.payload
    assert state.context.payload["tool_results"][0]["success"] is True
    analysis_result = state.results["data-analysis-agent"]
    assert analysis_result.structured_output["tool_context"]["tool_call_count"] == 1


def test_supervisor_warns_when_tool_call_fails() -> None:
    bridge = StubToolBridge(success=False)
    runner = SupervisorGraphRunner(AgentRegistry(), tool_bridge=bridge)

    state = runner.run(
        {
            "request_id": "r9",
            "intent": "analyze dataset quality",
            "tool_calls": [{"name": "aep_dataset_list", "parameters": {"limit": 5}}],
        }
    )

    assert any("tool calls failed" in warning for warning in state.warnings)
