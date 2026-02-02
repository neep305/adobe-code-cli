"""AI inference engine for schema generation and data analysis."""

import json
from enum import Enum
from typing import Any, Dict, List, Optional

from anthropic import Anthropic
from openai import OpenAI
from pydantic import BaseModel, Field

from adobe_experience.core.config import AEPConfig
from adobe_experience.schema.models import XDMSchema


class SchemaGenerationRequest(BaseModel):
    """Request for AI-powered schema generation."""

    sample_data: List[Dict[str, Any]]
    schema_name: str
    schema_description: Optional[str] = None
    identity_fields: Optional[List[str]] = None
    primary_identity: Optional[str] = None
    tenant_id: Optional[str] = None
    class_id: Optional[str] = None


class SchemaGenerationResponse(BaseModel):
    """Response from AI schema generation."""

    xdm_schema: XDMSchema
    reasoning: str
    identity_recommendations: Dict[str, str]
    data_quality_issues: List[str]


class ValidationSeverity(str, Enum):
    """Severity level for validation issues."""
    
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class ValidationIssue(BaseModel):
    """Single validation issue found in data."""
    
    severity: ValidationSeverity
    field_path: str
    issue_type: str
    message: str
    sample_value: Optional[Any] = None
    expected_type: Optional[str] = None
    actual_type: Optional[str] = None
    suggestion: Optional[str] = None
    auto_fixable: bool = False


class SchemaValidationReport(BaseModel):
    """Validation report for schema against actual data."""
    
    schema_id: str
    schema_title: str
    total_records_validated: int
    total_issues: int
    critical_issues: int
    warning_issues: int
    info_issues: int
    issues: List[ValidationIssue] = Field(default_factory=list)
    ai_summary: Optional[str] = None
    overall_status: str = "pending"  # pending, passed, failed


class RelationshipType(str, Enum):
    """Type of relationship between entities."""
    
    ONE_TO_ONE = "1:1"
    ONE_TO_MANY = "1:N"
    MANY_TO_ONE = "N:1"
    MANY_TO_MANY = "N:M"
    UNKNOWN = "unknown"


class EntityRelationship(BaseModel):
    """Detected relationship between two entities."""
    
    source_entity: str
    source_field: str
    target_entity: str
    target_field: str
    relationship_type: RelationshipType
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str


class XDMClassRecommendation(BaseModel):
    """XDM class recommendation for an entity."""
    
    entity_name: str
    recommended_class: str  # Profile, ExperienceEvent, etc.
    recommended_class_id: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    alternative_classes: List[str] = Field(default_factory=list)


class IdentityStrategy(BaseModel):
    """Identity configuration strategy for an entity."""
    
    entity_name: str
    primary_identity_field: str
    identity_namespace: str
    additional_identity_fields: List[str] = Field(default_factory=list)
    reasoning: str


class DatasetAnalysisResult(BaseModel):
    """Result of AI-powered dataset ERD analysis."""
    
    entities: List[str]
    relationships: List[EntityRelationship]
    xdm_class_recommendations: List[XDMClassRecommendation]
    identity_strategies: List[IdentityStrategy]
    field_group_suggestions: Dict[str, List[str]]  # entity -> suggested field groups
    implementation_strategy: str  # Overall strategy (denormalized vs normalized)
    ai_reasoning: str  # Overall reasoning and recommendations


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
        self.anthropic = None
        self.openai = None

        # Determine which AI provider to use
        provider = self.config.ai_provider.lower()
        
        # Initialize Anthropic client if key is available
        if self.config.anthropic_api_key:
            api_key = self.config.anthropic_api_key.get_secret_value()
            if api_key and len(api_key) >= 20 and not api_key.startswith("test-"):
                self.anthropic = Anthropic(api_key=api_key)
        
        # Initialize OpenAI client if key is available
        if self.config.openai_api_key:
            api_key = self.config.openai_api_key.get_secret_value()
            if api_key and len(api_key) >= 20:
                self.openai = OpenAI(api_key=api_key)
        
        # Set active client based on provider preference
        if provider == "anthropic":
            self.active_client = "anthropic" if self.anthropic else None
        elif provider == "openai":
            self.active_client = "openai" if self.openai else None
        elif provider == "auto":
            # Auto-select first available
            if self.openai:
                self.active_client = "openai"
            elif self.anthropic:
                self.active_client = "anthropic"
            else:
                self.active_client = None
        else:
            self.active_client = None

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
        if not self.active_client:
            raise ValueError(
                "No AI provider configured. "
                "Run 'adobe ai set-key anthropic' or 'adobe ai set-key openai' to configure your API key, "
                "or use --no-ai flag to skip AI-powered features."
            )

        # Prepare prompt
        sample_json = json.dumps(request.sample_data[:5], indent=2)  # Limit to 5 samples
        prompt = self.SCHEMA_GENERATION_PROMPT.format(
            sample_data=sample_json,
            schema_name=request.schema_name,
            schema_description=request.schema_description or "User-provided data",
        )

        # Call LLM with error handling
        try:
            if self.active_client == "anthropic":
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
                ai_output = response.content[0].text
            elif self.active_client == "openai":
                response = self.openai.chat.completions.create(
                    model=self.config.ai_model,
                    max_tokens=4096,
                    messages=[
                        {
                            "role": "user",
                            "content": prompt,
                        }
                    ],
                )
                ai_output = response.choices[0].message.content
            else:
                raise ValueError(f"Unknown AI provider: {self.active_client}")
        except Exception as e:
            if "invalid x-api-key" in str(e).lower() or "authentication" in str(e).lower() or "401" in str(e):
                provider_name = self.active_client.title()
                raise ValueError(
                    f"{provider_name} API authentication failed: {e}\n\n"
                    f"Your API key may be invalid or expired. "
                    f"Run 'adobe ai set-key {self.active_client}' to update your API key."
                ) from e
            raise

        # Parse AI response
        ai_output = ai_output or ""

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
            tenant_id=request.tenant_id,
            class_id=request.class_id,
        )

        # Apply AI recommendations to schema fields
        if schema.properties:
            # Handle tenant-nested properties
            if request.tenant_id and f"_{request.tenant_id}" in schema.properties:
                tenant_obj = schema.properties[f"_{request.tenant_id}"]
                target_properties = tenant_obj.properties if tenant_obj.properties else {}
            else:
                target_properties = schema.properties
            
            for field_name, recommendations in ai_analysis.get("field_recommendations", {}).items():
                if field_name in target_properties:
                    field = target_properties[field_name]

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

    async def validate_schema_against_data(
        self,
        schema: Dict[str, Any],
        data: List[Dict[str, Any]],
    ) -> SchemaValidationReport:
        """Validate actual data against XDM schema.

        Args:
            schema: XDM schema definition.
            data: List of data records to validate.

        Returns:
            Validation report with issues and suggestions.
        """
        schema_id = schema.get("$id", "unknown")
        schema_title = schema.get("title", "Unknown Schema")
        issues: List[ValidationIssue] = []

        # Extract schema properties
        properties = schema.get("properties", {})
        
        # Validate each record
        for record_idx, record in enumerate(data):
            # Check for type mismatches
            for field_name, field_def in properties.items():
                # Handle tenant namespace (e.g., _tenant_id:field)
                actual_field = field_name
                if ":" in field_name:
                    actual_field = field_name.split(":", 1)[1]
                
                if actual_field in record:
                    value = record[actual_field]
                    expected_type = field_def.get("type")
                    actual_type = self._get_json_type(value)
                    
                    # Type mismatch
                    if expected_type and actual_type != expected_type:
                        # Allow integer to pass as number
                        if not (expected_type == "number" and actual_type == "integer"):
                            issues.append(ValidationIssue(
                                severity=ValidationSeverity.CRITICAL,
                                field_path=actual_field,
                                issue_type="type_mismatch",
                                message=f"Type mismatch in field '{actual_field}'",
                                sample_value=value,
                                expected_type=expected_type,
                                actual_type=actual_type,
                                suggestion=f"Convert '{actual_field}' to {expected_type}",
                                auto_fixable=True,
                            ))
                    
                    # Format validation
                    expected_format = field_def.get("format")
                    if expected_format and isinstance(value, str):
                        if not self._validate_format(value, expected_format):
                            issues.append(ValidationIssue(
                                severity=ValidationSeverity.WARNING,
                                field_path=actual_field,
                                issue_type="format_mismatch",
                                message=f"Field '{actual_field}' does not match expected format '{expected_format}'",
                                sample_value=value,
                                expected_type=expected_format,
                                actual_type="string",
                                suggestion=f"Update schema to remove format constraint or fix data format",
                                auto_fixable=True,
                            ))
            
            # Check for fields in data but not in schema
            for field_name in record.keys():
                # Check if field exists in schema (with or without tenant namespace)
                field_exists = (
                    field_name in properties or
                    any(prop.endswith(f":{field_name}") for prop in properties.keys())
                )
                
                if not field_exists:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.INFO,
                        field_path=field_name,
                        issue_type="extra_field",
                        message=f"Field '{field_name}' exists in data but not in schema",
                        sample_value=record[field_name],
                        suggestion=f"Add '{field_name}' field to schema",
                        auto_fixable=True,
                    ))

        # Calculate summary statistics
        critical_count = sum(1 for issue in issues if issue.severity == ValidationSeverity.CRITICAL)
        warning_count = sum(1 for issue in issues if issue.severity == ValidationSeverity.WARNING)
        info_count = sum(1 for issue in issues if issue.severity == ValidationSeverity.INFO)
        
        # Determine overall status
        if critical_count > 0:
            overall_status = "failed"
        elif warning_count > 0:
            overall_status = "passed_with_warnings"
        else:
            overall_status = "passed"
        
        # AI summary if available
        ai_summary = None
        if self.active_client and issues:
            ai_summary = await self._generate_validation_summary(schema_title, issues)

        return SchemaValidationReport(
            schema_id=schema_id,
            schema_title=schema_title,
            total_records_validated=len(data),
            total_issues=len(issues),
            critical_issues=critical_count,
            warning_issues=warning_count,
            info_issues=info_count,
            issues=issues,
            ai_summary=ai_summary,
            overall_status=overall_status,
        )

    def _get_json_type(self, value: Any) -> str:
        """Get JSON schema type from Python value."""
        if value is None:
            return "null"
        elif isinstance(value, bool):
            return "boolean"
        elif isinstance(value, int):
            return "integer"
        elif isinstance(value, float):
            return "number"
        elif isinstance(value, str):
            return "string"
        elif isinstance(value, list):
            return "array"
        elif isinstance(value, dict):
            return "object"
        return "unknown"

    def _validate_format(self, value: str, format_type: str) -> bool:
        """Validate string format."""
        import re
        
        if format_type == "email":
            return bool(re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", value))
        elif format_type == "uri":
            return value.startswith(("http://", "https://"))
        elif format_type == "date":
            return bool(re.match(r"^\d{4}-\d{2}-\d{2}$", value))
        elif format_type == "date-time":
            return "T" in value or " " in value
        return True

    async def _generate_validation_summary(
        self,
        schema_title: str,
        issues: List[ValidationIssue],
    ) -> str:
        """Generate AI summary of validation issues."""
        if not self.active_client:
            return None

        issue_summary = "\n".join([
            f"- {issue.severity.upper()}: {issue.message} (field: {issue.field_path})"
            for issue in issues[:10]  # Limit to 10 issues
        ])

        prompt = f"""Analyze these schema validation issues and provide a concise summary with recommendations:

Schema: {schema_title}

Issues found:
{issue_summary}

Provide a brief 2-3 sentence summary of the main problems and recommended actions."""

        try:
            if self.active_client == "anthropic":
                response = self.anthropic.messages.create(
                    model=self.config.ai_model,
                    max_tokens=512,
                    messages=[{"role": "user", "content": prompt}],
                )
                return response.content[0].text.strip()
            elif self.active_client == "openai":
                response = self.openai.chat.completions.create(
                    model=self.config.ai_model,
                    max_tokens=512,
                    messages=[{"role": "user", "content": prompt}],
                )
                return response.choices[0].message.content.strip()
        except Exception:
            # If AI summary fails, continue without it
            return None

    async def analyze_dataset_relationships(
        self,
        scan_result: "DatasetScanResult",
    ) -> DatasetAnalysisResult:
        """Analyze relationships and structure across multiple entities.
        
        Args:
            scan_result: Dataset scan result from DatasetScanner.
            
        Returns:
            AI analysis of dataset structure and relationships.
        """
        from adobe_experience.schema.dataset_scanner import DatasetScanResult
        
        if not self.active_client:
            raise ValueError(
                "No AI provider configured. "
                "Run 'adobe ai set-key anthropic' or 'adobe ai set-key openai'."
            )
        
        # Prepare dataset summary for AI
        entities_summary = []
        for entity in scan_result.entities:
            field_list = []
            for field_name, field_meta in entity.fields.items():
                field_info = f"{field_name} ({field_meta.detected_type})"
                if field_meta.is_potential_id:
                    field_info += " [ID]"
                field_list.append(field_info)
            
            entities_summary.append({
                "name": entity.entity_name,
                "file": entity.file_path,
                "record_count": entity.record_count,
                "fields": field_list[:20],  # Limit to 20 fields
                "potential_pk": entity.potential_primary_key,
                "potential_fks": entity.potential_foreign_keys,
                "sample": entity.sample_records[0] if entity.sample_records else {}
            })
        
        prompt = f"""You are an expert data architect analyzing an e-commerce dataset for Adobe Experience Platform (AEP) schema design.

Dataset contains {scan_result.total_files} entities with {scan_result.total_records} total records.

Entities:
{json.dumps(entities_summary, indent=2)}

Analyze this dataset and provide a comprehensive ERD analysis in JSON format:

{{
  "entities": ["list of entity names"],
  "relationships": [
    {{
      "source_entity": "orders",
      "source_field": "customer_id",
      "target_entity": "customers",
      "target_field": "customer_id",
      "relationship_type": "N:1",
      "confidence": 0.95,
      "reasoning": "orders.customer_id references customers.customer_id"
    }}
  ],
  "xdm_class_recommendations": [
    {{
      "entity_name": "customers",
      "recommended_class": "XDM Individual Profile",
      "recommended_class_id": "https://ns.adobe.com/xdm/context/profile",
      "confidence": 0.98,
      "reasoning": "Contains person-level attributes and demographics",
      "alternative_classes": []
    }}
  ],
  "identity_strategies": [
    {{
      "entity_name": "customers",
      "primary_identity_field": "customer_id",
      "identity_namespace": "CRM_ID",
      "additional_identity_fields": ["email"],
      "reasoning": "customer_id is unique identifier, email for cross-channel identity"
    }}
  ],
  "field_group_suggestions": {{
    "customers": ["Demographic Details", "Personal Contact Details", "Loyalty Details"],
    "orders": ["Commerce Details", "Order Details"]
  }},
  "implementation_strategy": "Denormalized approach recommended: embed critical customer fields in events to avoid joins. Use Profile for customer master data, ExperienceEvent for orders/events.",
  "ai_reasoning": "Overall analysis of the dataset structure, recommended approach, and key considerations for AEP implementation."
}}

Key considerations:
1. Identify foreign key relationships by matching field names (e.g., customer_id, product_id)
2. Recommend XDM classes: Profile for people/accounts, ExperienceEvent for time-series events, Custom classes for products
3. Suggest identity namespaces: CRM_ID for customer IDs, Email for email addresses, etc.
4. Consider denormalization for AEP: embed frequently accessed data to avoid joins
5. Recommend field groups from Adobe's standard field groups when possible
6. Use ONLY these relationship types: "1:1", "1:N", "N:1", "N:M"

Provide ONLY the JSON response, no other text."""

        try:
            if self.active_client == "anthropic":
                response = self.anthropic.messages.create(
                    model=self.config.ai_model,
                    max_tokens=4096,
                    messages=[{"role": "user", "content": prompt}],
                )
                ai_output = response.content[0].text
            elif self.active_client == "openai":
                response = self.openai.chat.completions.create(
                    model=self.config.ai_model,
                    max_tokens=4096,
                    messages=[{"role": "user", "content": prompt}],
                )
                ai_output = response.choices[0].message.content
            else:
                raise ValueError(f"Unknown AI provider: {self.active_client}")
        except Exception as e:
            if "invalid x-api-key" in str(e).lower() or "authentication" in str(e).lower() or "401" in str(e):
                provider_name = self.active_client.title()
                raise ValueError(
                    f"{provider_name} API authentication failed: {e}\n\n"
                    f"Run 'adobe ai set-key {self.active_client}' to update your API key."
                ) from e
            raise
        
        # Parse AI response
        ai_output = ai_output or ""
        
        # Extract JSON from response (handle markdown code blocks)
        if "```json" in ai_output:
            json_start = ai_output.index("```json") + 7
            json_end = ai_output.index("```", json_start)
            ai_output = ai_output[json_start:json_end].strip()
        elif "```" in ai_output:
            json_start = ai_output.index("```") + 3
            json_end = ai_output.index("```", json_start)
            ai_output = ai_output[json_start:json_end].strip()
        
        analysis_data = json.loads(ai_output)
        
        # Parse relationships
        relationships = []
        for rel in analysis_data.get("relationships", []):
            relationships.append(EntityRelationship(
                source_entity=rel["source_entity"],
                source_field=rel["source_field"],
                target_entity=rel["target_entity"],
                target_field=rel["target_field"],
                relationship_type=RelationshipType(rel["relationship_type"]),
                confidence=rel["confidence"],
                reasoning=rel["reasoning"],
            ))
        
        # Parse XDM class recommendations
        xdm_recommendations = []
        for rec in analysis_data.get("xdm_class_recommendations", []):
            xdm_recommendations.append(XDMClassRecommendation(
                entity_name=rec["entity_name"],
                recommended_class=rec["recommended_class"],
                recommended_class_id=rec.get("recommended_class_id"),
                confidence=rec["confidence"],
                reasoning=rec["reasoning"],
                alternative_classes=rec.get("alternative_classes", []),
            ))
        
        # Parse identity strategies
        identity_strategies = []
        for strat in analysis_data.get("identity_strategies", []):
            identity_strategies.append(IdentityStrategy(
                entity_name=strat["entity_name"],
                primary_identity_field=strat["primary_identity_field"],
                identity_namespace=strat["identity_namespace"],
                additional_identity_fields=strat.get("additional_identity_fields", []),
                reasoning=strat["reasoning"],
            ))
        
        return DatasetAnalysisResult(
            entities=analysis_data.get("entities", []),
            relationships=relationships,
            xdm_class_recommendations=xdm_recommendations,
            identity_strategies=identity_strategies,
            field_group_suggestions=analysis_data.get("field_group_suggestions", {}),
            implementation_strategy=analysis_data.get("implementation_strategy", ""),
            ai_reasoning=analysis_data.get("ai_reasoning", ""),
        )

    async def suggest_schema_fields(
        self,
        schema_name: str,
        schema_description: str,
        domain: str,
    ) -> List[Dict[str, Any]]:
        """Suggest schema fields based on schema description and domain.

        Args:
            schema_name: Name of the schema
            schema_description: Description of what the schema is for
            domain: Domain of the schema (customer, product, event, etc.)

        Returns:
            List of suggested fields with name, type, and description
        """
        if not self.active_client:
            raise ValueError("No AI provider configured")

        prompt = f"""Based on the following schema requirements, suggest appropriate XDM fields:

Schema Name: {schema_name}
Schema Description: {schema_description}
Domain: {domain}

Please suggest 5-10 relevant fields that would be commonly needed for this type of schema.

Return your response as a JSON array of field objects with the following structure:
[
  {{
    "name": "fieldName",
    "type": "string|integer|number|boolean|date|datetime|array|object",
    "description": "Brief description of the field",
    "required": true|false
  }}
]

Important:
- Use camelCase for field names
- Choose appropriate data types
- Mark critical fields as required
- Include identity fields if relevant (email, userId, etc.)
- Follow XDM best practices

Return ONLY the JSON array, no additional text."""

        try:
            if self.active_client == "anthropic":
                response = self.anthropic.messages.create(
                    model=self.config.ai_model,
                    max_tokens=2048,
                    messages=[{"role": "user", "content": prompt}],
                )
                ai_output = response.content[0].text
            elif self.active_client == "openai":
                response = self.openai.chat.completions.create(
                    model=self.config.ai_model,
                    max_tokens=2048,
                    messages=[{"role": "user", "content": prompt}],
                )
                ai_output = response.choices[0].message.content
            else:
                raise ValueError(f"Unknown AI provider: {self.active_client}")

            # Extract JSON from response
            if "```json" in ai_output:
                json_start = ai_output.index("```json") + 7
                json_end = ai_output.index("```", json_start)
                ai_output = ai_output[json_start:json_end].strip()
            elif "```" in ai_output:
                json_start = ai_output.index("```") + 3
                json_end = ai_output.index("```", json_start)
                ai_output = ai_output[json_start:json_end].strip()

            fields = json.loads(ai_output)
            return fields if isinstance(fields, list) else []

        except Exception as e:
            # Return basic fields as fallback
            return [
                {"name": "id", "type": "string", "description": "Unique identifier", "required": True},
                {"name": "name", "type": "string", "description": "Name or title", "required": True},
                {"name": "createdAt", "type": "datetime", "description": "Creation timestamp", "required": False},
            ]

