"""Schema mapping domain agent.

Generates practical XDM mapping guidance from analysis payloads.
"""

from __future__ import annotations

from typing import Any, Dict, List

from adobe_experience.agent.contracts import (
    AgentResult,
    AgentResultStatus,
    Capability,
    ExecutionContext,
)


class SchemaMappingAgent:
    """Agent that converts analysis signals into XDM mapping recommendations."""

    name = "schema-mapping-agent"
    capabilities = [Capability.SCHEMA]
    priority = 90

    _KEYWORDS = ["schema", "xdm", "mapping", "identity", "field group", "class id"]

    def can_handle(self, context: ExecutionContext) -> bool:
        text = context.intent.lower()
        return any(keyword in text for keyword in self._KEYWORDS)

    def plan(self, context: ExecutionContext) -> Dict[str, Any]:
        return {
            "agent": self.name,
            "steps": ["class_recommendation", "identity_recommendation", "field_group_suggestions"],
        }

    def execute(self, context: ExecutionContext) -> AgentResult:
        payload = dict(context.payload)
        fields = self._extract_fields(payload)

        class_id, class_name = self._recommend_class(fields, context.intent)
        identity = self._recommend_identity(fields)
        field_groups = self._recommend_field_groups(fields)

        structured = {
            "xdm_class": {
                "name": class_name,
                "class_id": class_id,
            },
            "identity": identity,
            "field_groups": field_groups,
            "schema_create_template": self._schema_command_template(class_id),
        }

        # Confidence based on field coverage
        # 0.5 (LOW): No fields to map, placeholder recommendations only
        # 0.7 (MEDIUM-HIGH): Fields present, actionable XDM mapping generated
        confidence = 0.7 if fields else 0.5
        warnings: List[str] = []
        if not fields:
            warnings.append("No fields found for mapping; provide analysis_result or records")

        return AgentResult(
            agent_name=self.name,
            status=AgentResultStatus.WARNING if warnings else AgentResultStatus.SUCCESS,
            summary=f"Generated XDM mapping guidance for {len(fields)} fields",
            structured_output=structured,
            confidence=confidence,
            warnings=warnings,
            next_actions=[
                "Review recommended identity namespace",
                "Run aep schema create with suggested class_id",
            ],
        )

    def summarize(self, result: AgentResult) -> str:
        return result.summary

    @staticmethod
    def _extract_fields(payload: Dict[str, Any]) -> List[str]:
        # Preferred input from prior analysis agent.
        analysis = payload.get("analysis_result")
        if isinstance(analysis, dict):
            fields = analysis.get("fields")
            if isinstance(fields, list):
                return sorted([field for field in fields if isinstance(field, str)])

        # Fallback: infer fields from sample records.
        records = payload.get("records")
        if isinstance(records, list):
            field_set = set()
            for row in records:
                if isinstance(row, dict):
                    field_set.update(row.keys())
            return sorted(field_set)

        return []

    @staticmethod
    def _recommend_class(fields: List[str], intent: str) -> tuple[str, str]:
        lowered_fields = [field.lower() for field in fields]
        lowered_intent = intent.lower()

        event_signals = ["event", "timestamp", "occurred", "action", "interaction"]
        if any(signal in lowered_intent for signal in event_signals) or any(
            any(signal in field for signal in event_signals) for field in lowered_fields
        ):
            return ("https://ns.adobe.com/xdm/context/experienceevent", "ExperienceEvent")

        return ("https://ns.adobe.com/xdm/context/profile", "Profile")

    @staticmethod
    def _recommend_identity(fields: List[str]) -> Dict[str, Any]:
        lowered = {field.lower(): field for field in fields}

        if "email" in lowered:
            return {
                "primary_field": lowered["email"],
                "namespace": "Email",
                "reasoning": "Email is a common primary identity for customer profile use cases",
            }
        if "customer_id" in lowered:
            return {
                "primary_field": lowered["customer_id"],
                "namespace": "CRMID",
                "reasoning": "customer_id is suitable for CRM-linked identity resolution",
            }

        for field in fields:
            if field.lower().endswith("_id"):
                return {
                    "primary_field": field,
                    "namespace": "Custom",
                    "reasoning": "ID-like field selected as fallback identity",
                }

        return {
            "primary_field": None,
            "namespace": "Custom",
            "reasoning": "No obvious identity field detected; manual selection required",
        }

    @staticmethod
    def _recommend_field_groups(fields: List[str]) -> List[str]:
        lowered = [field.lower() for field in fields]
        suggestions = ["https://ns.adobe.com/xdm/context/profile"]

        if any("email" in field or "phone" in field for field in lowered):
            suggestions.append("https://ns.adobe.com/xdm/context/person-details")
        if any("address" in field or "city" in field or "country" in field for field in lowered):
            suggestions.append("https://ns.adobe.com/xdm/context/address")

        return suggestions

    @staticmethod
    def _schema_command_template(class_id: str) -> str:
        return (
            "aep schema create --name \"<schema-name>\" --from-sample <data.json> "
            f"--class-id {class_id} --use-ai"
        )
