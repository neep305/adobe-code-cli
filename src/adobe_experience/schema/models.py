"""XDM Schema models and types."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class XDMDataType(str, Enum):
    """XDM data types."""

    STRING = "string"
    NUMBER = "number"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    OBJECT = "object"
    ARRAY = "array"
    DATE = "date"
    DATE_TIME = "date-time"


class XDMFieldFormat(str, Enum):
    """XDM field formats."""

    EMAIL = "email"
    URI = "uri"
    DATE = "date"
    DATE_TIME = "date-time"
    UUID = "uuid"


class XDMIdentityNamespace(str, Enum):
    """Common XDM identity namespaces."""

    EMAIL = "Email"
    PHONE = "Phone"
    ECID = "ECID"
    CRM_ID = "CRM_ID"
    COOKIE_ID = "Cookie_ID"
    MOBILE_ID = "Mobile_ID"


class XDMFieldMeta(BaseModel):
    """XDM field metadata."""

    ui_title: Optional[str] = Field(None, alias="meta:ui_title")
    ui_description: Optional[str] = Field(None, alias="meta:ui_description")
    xdm_type: Optional[str] = Field(None, alias="meta:xdmType")


class XDMIdentity(BaseModel):
    """XDM identity configuration."""

    namespace: str = Field(..., description="Identity namespace")
    is_primary: bool = Field(False, alias="xdm:isPrimary", description="Primary identity flag")


class XDMField(BaseModel):
    """XDM schema field definition."""

    title: str = Field(..., description="Field title")
    description: Optional[str] = Field(None, description="Field description")
    type: XDMDataType = Field(..., description="Field data type")
    format: Optional[XDMFieldFormat] = Field(None, description="Field format")
    enum: Optional[List[str]] = Field(None, description="Allowed enum values")
    minimum: Optional[float] = Field(None, description="Minimum value for numbers")
    maximum: Optional[float] = Field(None, description="Maximum value for numbers")
    items: Optional["XDMField"] = Field(None, description="Array item schema")
    properties: Optional[Dict[str, "XDMField"]] = Field(None, description="Object properties")
    required: Optional[List[str]] = Field(None, description="Required properties")
    identity: Optional[XDMIdentity] = Field(None, alias="meta:xdmIdentity")
    meta: Optional[XDMFieldMeta] = Field(None)

    model_config = {"populate_by_name": True}


class XDMSchemaRef(BaseModel):
    """Reference to an XDM schema or mixin."""

    ref: str = Field(..., alias="$ref", description="Schema reference URI")
    id: Optional[str] = Field(None, alias="$id")

    model_config = {"populate_by_name": True}


class XDMSchema(BaseModel):
    """XDM schema definition."""

    schema_id: str = Field(..., alias="$id", description="Schema ID")
    schema_ref: str = Field(
        default="http://json-schema.org/draft-06/schema#",
        alias="$schema",
        description="JSON Schema version",
    )
    title: str = Field(..., description="Schema title")
    description: Optional[str] = Field(None, description="Schema description")
    type: XDMDataType = Field(default=XDMDataType.OBJECT, description="Root type (always object)")
    version: str = Field(default="1.0", description="Schema version")

    # Schema composition
    all_of: List[XDMSchemaRef] = Field(
        default_factory=list,
        alias="allOf",
        description="List of schema references to compose",
    )

    # Field definitions
    definitions: Optional[Dict[str, XDMField]] = Field(
        None,
        description="Field definitions",
    )
    properties: Optional[Dict[str, XDMField]] = Field(
        None,
        description="Schema properties",
    )

    # Metadata
    meta_class: str = Field(
        default="https://ns.adobe.com/xdm/context/profile",
        alias="meta:class",
        description="XDM class",
    )
    meta_abstract: bool = Field(default=False, alias="meta:abstract")
    meta_extends: Optional[List[str]] = Field(
        default=None,
        alias="meta:extends",
        description="Extended schemas",
    )

    model_config = {"populate_by_name": True}


class SchemaRegistryResponse(BaseModel):
    """Response from Schema Registry API."""

    schema_id: str = Field(..., alias="$id")
    title: str
    description: Optional[str] = None
    version: str
    created: Optional[str] = Field(None, alias="meta:created")
    updated: Optional[str] = Field(None, alias="meta:updated")

    model_config = {"populate_by_name": True}


class SchemaTemplate(BaseModel):
    """Schema template for quick schema creation."""

    name: str = Field(..., description="Template name (unique identifier)")
    title: str = Field(..., description="Display title")
    description: str = Field(..., description="Template description")
    domain: str = Field(..., description="Business domain (e.g., customer, product, event)")
    sample_fields: List[Dict[str, Any]] = Field(..., description="Sample field definitions")
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    version: str = Field(default="1.0.0", description="Template version")
    xdm_class: Optional[str] = Field(None, description="XDM class ID")

    model_config = {"populate_by_name": True}


# AI-Powered Schema Generation Models (for structured output)

class AIFieldRecommendation(BaseModel):
    """AI recommendation for a single field configuration."""

    field_name: str = Field(..., description="Field name from the data")
    xdm_type: str = Field(..., description="XDM data type: string, number, integer, boolean, object, array, date, date-time")
    xdm_format: Optional[str] = Field(None, description="XDM format: email, uri, date, date-time, uuid")
    is_identity: bool = Field(default=False, description="Whether this field should be marked as an identity")
    identity_namespace: Optional[str] = Field(None, description="Identity namespace: Email, Phone, ECID, CRM_ID, Cookie_ID, Mobile_ID")
    is_required: bool = Field(default=False, description="Whether this field is required")
    is_primary_identity: bool = Field(default=False, description="Whether this is the primary identity field")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score for this recommendation (0.0-1.0)")
    reasoning: str = Field(..., description="Explanation for the field type and identity recommendation")
    enum_values: Optional[List[str]] = Field(None, description="Detected enum values if applicable")
    field_group_match: Optional[str] = Field(None, description="Standard Adobe field group that matches this field")


class AIDataQualityIssue(BaseModel):
    """Data quality issue detected by AI analysis."""

    severity: str = Field(..., description="Issue severity: critical, warning, info")
    issue_type: str = Field(..., description="Type: missing_values, inconsistent_format, data_type_mismatch, outliers")
    field_name: str = Field(..., description="Field with the issue")
    description: str = Field(..., description="Human-readable description of the issue")
    impact: str = Field(..., description="Impact on data ingestion or profile activation")
    recommendation: str = Field(..., description="Suggested fix or workaround")
    affected_percentage: Optional[float] = Field(None, ge=0.0, le=100.0, description="Percentage of records affected")


class AIIdentityStrategy(BaseModel):
    """AI-recommended identity strategy for Profile/Event activation."""

    primary_identity_field: str = Field(..., description="Recommended primary identity field")
    primary_namespace: str = Field(..., description="Primary identity namespace")
    secondary_identities: List[Dict[str, str]] = Field(default_factory=list, description="Additional identity fields [{field, namespace}]")
    identity_graph_strategy: str = Field(..., description="Strategy: email-based, crm-based, device-graph, hybrid")
    profile_merge_policy: str = Field(..., description="Recommended merge policy approach")
    reasoning: str = Field(..., description="Explanation for identity strategy choice")
    aep_best_practice_compliance: str = Field(..., description="How this aligns with AEP best practices")


class AIFieldGroupSuggestion(BaseModel):
    """Suggestion to use an Adobe standard field group."""

    field_group_name: str = Field(..., description="Name of the standard field group")
    field_group_id: Optional[str] = Field(None, description="Field group $id URI")
    matched_fields: List[str] = Field(..., description="Fields from data that match this field group")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in the match")
    reasoning: str = Field(..., description="Why this field group is recommended")


class AISchemaAnalysis(BaseModel):
    """Complete AI analysis result for schema generation (structured output)."""

    field_recommendations: Dict[str, AIFieldRecommendation] = Field(..., description="Field-level recommendations keyed by field name")
    identity_strategy: AIIdentityStrategy = Field(..., description="Identity configuration strategy")
    data_quality_issues: List[AIDataQualityIssue] = Field(default_factory=list, description="Detected data quality issues")
    xdm_class_recommendation: str = Field(..., description="Recommended XDM class ID (Profile, ExperienceEvent, etc.)")
    xdm_class_reasoning: str = Field(..., description="Why this XDM class is recommended")
    field_group_suggestions: List[AIFieldGroupSuggestion] = Field(default_factory=list, description="Standard field groups to include")
    overall_reasoning: str = Field(..., description="Overall analysis and recommendations")
    schema_version: str = Field(default="1.0", description="Recommended schema version")
    complexity_score: float = Field(..., ge=0.0, le=10.0, description="Data complexity score (0=simple, 10=very complex)")


# AI-Powered Type Inference Models

class AIFieldTypeInference(BaseModel):
    """AI-powered field type inference result with edge case handling."""

    field_name: str = Field(..., description="Field name being analyzed")
    recommended_xdm_type: str = Field(..., description="Recommended XDM type: string, number, integer, boolean, date, date-time, object, array")
    recommended_format: Optional[str] = Field(None, description="Recommended format: email, uri, date, date-time, uuid, phone, currency")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in type recommendation")
    reasoning: str = Field(..., description="Explanation for type choice")
    edge_case_detected: Optional[str] = Field(None, description="Edge case type: mixed_array, boolean_variant, date_format, phone_number, currency")
    edge_case_handling: Optional[str] = Field(None, description="How to handle the edge case")
    alternative_types: List[str] = Field(default_factory=list, description="Alternative type options")
    semantic_meaning: Optional[str] = Field(None, description="Semantic meaning inferred from field name and values")
    preprocessing_needed: Optional[str] = Field(None, description="Data transformation needed before ingestion")
