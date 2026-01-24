"""AI inference engine for schema generation and data analysis."""

import json
from typing import Any, Dict, List, Optional

from anthropic import Anthropic
from pydantic import BaseModel

from adobe_experience.core.config import AEPConfig
from adobe_experience.schema.models import XDMSchema


class SchemaGenerationRequest(BaseModel):
    """Request for AI-powered schema generation."""

    sample_data: List[Dict[str, Any]]
    schema_name: str
    schema_description: Optional[str] = None
    identity_fields: Optional[List[str]] = None
    primary_identity: Optional[str] = None


class SchemaGenerationResponse(BaseModel):
    """Response from AI schema generation."""

    xdm_schema: XDMSchema
    reasoning: str
    identity_recommendations: Dict[str, str]
    data_quality_issues: List[str]


class AIInferenceEngine:
    """AI inference engine using LLM for intelligent schema operations."""

    SCHEMA_GENERATION_PROMPT = """You are an expert in Adobe Experience Platform XDM schemas.

Analyze the provided sample data and generate an optimal XDM schema that:
1. Properly identifies data types and formats
2. Suggests appropriate identity fields (email, phone, CRM ID, etc.)
3. Identifies data quality issues or inconsistencies
4. Recommends XDM field groups to use

Sample Data:
{sample_data}

Schema Name: {schema_name}
Description: {schema_description}

Provide your analysis in the following JSON format:
{{
    "recommended_identity_fields": {{"field_name": "namespace_reason"}},
    "primary_identity_field": "field_name",
    "data_quality_issues": ["issue1", "issue2"],
    "field_recommendations": {{
        "field_name": {{
            "xdm_type": "string|number|boolean|object|array",
            "format": "email|uri|date|date-time|null",
            "is_identity": true|false,
            "identity_namespace": "Email|Phone|ECID|null",
            "reasoning": "why this configuration"
        }}
    }},
    "xdm_mixins": ["recommended mixin URIs"],
    "reasoning": "overall analysis and recommendations"
}}

Focus on practical XDM best practices and AEP integration patterns."""

    def __init__(self, config: Optional[AEPConfig] = None) -> None:
        """Initialize inference engine.

        Args:
            config: Configuration. If None, loads from environment.
        """
        from adobe_experience.core.config import get_config

        self.config = config or get_config()

        if self.config.anthropic_api_key:
            self.anthropic = Anthropic(
                api_key=self.config.anthropic_api_key.get_secret_value()
            )
        else:
            self.anthropic = None

    async def generate_schema_with_ai(
        self,
        request: SchemaGenerationRequest,
    ) -> SchemaGenerationResponse:
        """Generate XDM schema using AI inference.

        Args:
            request: Schema generation request.

        Returns:
            AI-generated schema with recommendations.

        Raises:
            ValueError: If AI client is not configured.
        """
        if not self.anthropic:
            raise ValueError("Anthropic API key not configured")

        # Prepare prompt
        sample_json = json.dumps(request.sample_data[:5], indent=2)  # Limit to 5 samples
        prompt = self.SCHEMA_GENERATION_PROMPT.format(
            sample_data=sample_json,
            schema_name=request.schema_name,
            schema_description=request.schema_description or "User-provided data",
        )

        # Call LLM
        response = self.anthropic.messages.create(
            model=self.config.ai_model,
            max_tokens=4096,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        )

        # Parse AI response
        ai_output = response.content[0].text

        # Extract JSON from response (handle markdown code blocks)
        if "```json" in ai_output:
            json_start = ai_output.index("```json") + 7
            json_end = ai_output.index("```", json_start)
            ai_output = ai_output[json_start:json_end].strip()
        elif "```" in ai_output:
            json_start = ai_output.index("```") + 3
            json_end = ai_output.index("```", json_start)
            ai_output = ai_output[json_start:json_end].strip()

        ai_analysis = json.loads(ai_output)

        # Generate schema using analyzer with AI enhancements
        from adobe_experience.schema.xdm import XDMSchemaAnalyzer

        schema = XDMSchemaAnalyzer.from_sample_data(
            request.sample_data,
            request.schema_name,
            request.schema_description,
        )

        # Apply AI recommendations to schema fields
        if schema.properties:
            for field_name, recommendations in ai_analysis.get("field_recommendations", {}).items():
                if field_name in schema.properties:
                    field = schema.properties[field_name]

                    # Update format if recommended
                    if recommendations.get("format"):
                        from adobe_experience.schema.models import XDMFieldFormat
                        try:
                            field.format = XDMFieldFormat(recommendations["format"])
                        except ValueError:
                            pass

                    # Add identity if recommended
                    if recommendations.get("is_identity"):
                        from adobe_experience.schema.models import XDMIdentity
                        field.identity = XDMIdentity(
                            namespace=recommendations.get("identity_namespace", "Custom"),
                            is_primary=(field_name == ai_analysis.get("primary_identity_field")),
                        )

        return SchemaGenerationResponse(
            xdm_schema=schema,
            reasoning=ai_analysis.get("reasoning", "AI-generated schema"),
            identity_recommendations=ai_analysis.get("recommended_identity_fields", {}),
            data_quality_issues=ai_analysis.get("data_quality_issues", []),
        )

    async def suggest_identity_namespace(
        self,
        field_name: str,
        sample_values: List[str],
    ) -> Dict[str, Any]:
        """Suggest appropriate identity namespace for a field.

        Args:
            field_name: Field name to analyze.
            sample_values: Sample values from the field.

        Returns:
            Identity namespace suggestions and reasoning.

        Raises:
            ValueError: If AI client is not configured.
        """
        if not self.anthropic:
            raise ValueError("Anthropic API key not configured")

        prompt = f"""Analyze this field and suggest the most appropriate Adobe Experience Platform identity namespace.

Field Name: {field_name}
Sample Values: {json.dumps(sample_values[:10], indent=2)}

Available standard namespaces:
- Email: Email addresses
- Phone: Phone numbers
- ECID: Experience Cloud ID
- CRM_ID: CRM system identifiers
- Cookie_ID: Browser cookies
- Mobile_ID: Mobile device identifiers

Respond with JSON:
{{
    "recommended_namespace": "namespace_name",
    "confidence": 0.0-1.0,
    "reasoning": "explanation",
    "is_suitable_for_identity": true|false
}}"""

        response = self.anthropic.messages.create(
            model=self.config.ai_model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )

        ai_output = response.content[0].text

        # Extract JSON
        if "```json" in ai_output:
            json_start = ai_output.index("```json") + 7
            json_end = ai_output.index("```", json_start)
            ai_output = ai_output[json_start:json_end].strip()

        return json.loads(ai_output)
