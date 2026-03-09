"""Data analysis domain agent.

This v1 implementation intentionally stays lightweight: it builds a structured
analysis summary from provided payload data and preserves compatibility with the
new supervisor contracts.
"""

from __future__ import annotations

from typing import Any, Dict, List

from adobe_experience.agent.contracts import (
    AgentResult,
    AgentResultStatus,
    Capability,
    ExecutionContext,
)


class DataAnalysisAgent:
    """Agent that analyzes customer-like records for schema planning."""

    name = "data-analysis-agent"
    capabilities = [Capability.ANALYSIS]
    priority = 100

    _KEYWORDS = ["analy", "profil", "quality", "relationship", "dataset", "customer"]

    def can_handle(self, context: ExecutionContext) -> bool:
        text = context.intent.lower()
        return any(keyword in text for keyword in self._KEYWORDS)

    def plan(self, context: ExecutionContext) -> Dict[str, Any]:
        return {
            "agent": self.name,
            "mode": "read_only" if context.safety_mode.value == "read_only" else "write",
            "steps": ["profile_fields", "infer_relationship_hints", "summarize_quality"],
        }

    def execute(self, context: ExecutionContext) -> AgentResult:
        payload = dict(context.payload)
        records: List[Dict[str, Any]] = []
        tool_results = payload.get("tool_results") if isinstance(payload.get("tool_results"), list) else []

        if isinstance(payload.get("records"), list):
            records = [row for row in payload.get("records", []) if isinstance(row, dict)]
        elif isinstance(payload.get("sample_data"), list):
            records = [row for row in payload.get("sample_data", []) if isinstance(row, dict)]

        fields = self._collect_fields(records)
        quality = self._quality_snapshot(records, fields)
        relationship_hints = self._relationship_hints(fields)

        structured = {
            "record_count": len(records),
            "field_count": len(fields),
            "fields": fields,
            "quality": quality,
            "relationship_hints": relationship_hints,
            "tool_context": {
                "tool_call_count": len(tool_results),
                "successful_calls": len(
                    [item for item in tool_results if isinstance(item, dict) and item.get("success", False)]
                ),
            },
        }

        confidence = 0.65
        warnings: List[str] = []
        if not records:
            warnings.append("No structured sample records provided in payload")
            confidence = 0.45
            if tool_results:
                confidence = 0.55
                warnings.append("Using tool call results as supplemental context")
        elif len(records) >= 10:
            confidence = 0.8

        return AgentResult(
            agent_name=self.name,
            status=AgentResultStatus.WARNING if warnings else AgentResultStatus.SUCCESS,
            summary=f"Analyzed {len(records)} records across {len(fields)} fields",
            structured_output=structured,
            confidence=confidence,
            warnings=warnings,
            next_actions=[
                "Use schema-mapping-agent to generate XDM mapping guidance",
                "Review low-confidence fields before schema creation",
            ],
        )

    def summarize(self, result: AgentResult) -> str:
        return result.summary

    @staticmethod
    def _collect_fields(records: List[Dict[str, Any]]) -> List[str]:
        field_set = set()
        for row in records:
            field_set.update(row.keys())
        return sorted(field_set)

    @staticmethod
    def _quality_snapshot(records: List[Dict[str, Any]], fields: List[str]) -> Dict[str, Any]:
        if not records or not fields:
            return {
                "completeness": 0.0,
                "null_like_values": 0,
            }

        total_cells = len(records) * len(fields)
        null_like = 0
        for row in records:
            for field in fields:
                value = row.get(field)
                if value in (None, "", "null", "None"):
                    null_like += 1

        completeness = round((total_cells - null_like) / total_cells, 4) if total_cells else 0.0
        return {
            "completeness": completeness,
            "null_like_values": null_like,
        }

    @staticmethod
    def _relationship_hints(fields: List[str]) -> List[Dict[str, Any]]:
        hints: List[Dict[str, Any]] = []
        for field in fields:
            lowered = field.lower()
            if lowered.endswith("_id"):
                hints.append(
                    {
                        "field": field,
                        "hint": "possible_foreign_key",
                        "confidence": 0.7,
                    }
                )
        return hints
