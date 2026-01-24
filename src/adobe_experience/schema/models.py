"""XDM Schema models and types."""

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
