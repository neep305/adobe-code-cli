"""Tests for domain agents used in supervisor routing."""

from adobe_experience.agent.agents import DataAnalysisAgent, SchemaMappingAgent
from adobe_experience.agent.contracts import ExecutionContext, SafetyMode
from adobe_experience.agent.registry import AgentRegistry, register_default_agents


def _context(intent: str, payload=None) -> ExecutionContext:
    return ExecutionContext(
        request_id="req-domain",
        trace_id="trace-domain",
        intent=intent,
        input_source="file",
        payload=payload or {},
        safety_mode=SafetyMode.READ_ONLY,
    )


def test_data_analysis_agent_handles_analysis_intent() -> None:
    agent = DataAnalysisAgent()
    ctx = _context("analyze customer dataset")

    assert agent.can_handle(ctx)


def test_data_analysis_agent_returns_structured_summary() -> None:
    agent = DataAnalysisAgent()
    ctx = _context(
        "analyze customer dataset",
        payload={
            "records": [
                {"customer_id": "c1", "email": "a@x.com", "age": 30},
                {"customer_id": "c2", "email": "", "age": 22},
            ]
        },
    )

    result = agent.execute(ctx)
    assert "record_count" in result.structured_output
    assert result.structured_output["record_count"] == 2
    assert result.confidence > 0.45


def test_schema_mapping_agent_can_handle_schema_intent() -> None:
    agent = SchemaMappingAgent()
    ctx = _context("generate xdm schema mapping")

    assert agent.can_handle(ctx)


def test_schema_mapping_agent_generates_mapping() -> None:
    agent = SchemaMappingAgent()
    ctx = _context(
        "generate schema mapping",
        payload={
            "analysis_result": {
                "fields": ["customer_id", "email", "country", "created_timestamp"]
            }
        },
    )

    result = agent.execute(ctx)
    mapping = result.structured_output
    assert "xdm_class" in mapping
    assert "identity" in mapping
    assert "schema_create_template" in mapping


def test_register_default_agents_adds_builtins() -> None:
    registry = AgentRegistry()
    register_default_agents(registry)

    assert "data-analysis-agent" in registry.names()
    assert "schema-mapping-agent" in registry.names()
