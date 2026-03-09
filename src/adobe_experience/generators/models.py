"""Pydantic models for data generation."""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from adobe_experience.schema.models import XDMDataType, XDMFieldFormat


class RelationType(str, Enum):
    """Entity relationship types."""

    ONE_TO_ONE = "1:1"
    ONE_TO_MANY = "1:N"
    MANY_TO_ONE = "N:1"
    MANY_TO_MANY = "N:M"


class OutputFormat(str, Enum):
    """Output file formats."""

    JSON = "json"
    CSV = "csv"
    JSONL = "jsonl"
    PARQUET = "parquet"


class FieldConstraints(BaseModel):
    """Constraints for field generation."""

    min_value: Optional[float] = Field(None, description="Minimum numeric value")
    max_value: Optional[float] = Field(None, description="Maximum numeric value")
    min_length: Optional[int] = Field(None, description="Minimum string length")
    max_length: Optional[int] = Field(None, description="Maximum string length")
    pattern: Optional[str] = Field(None, description="Regex pattern")
    unique: bool = Field(False, description="Generate unique values")
    nullable: bool = Field(True, description="Allow NULL values")
    null_probability: float = Field(0.1, description="Probability of NULL (0.0-1.0)")


class FieldDefinition(BaseModel):
    """Field definition for data generation."""

    name: str = Field(..., description="Field name")
    description: Optional[str] = Field(None, description="Field description")
    xdm_type: XDMDataType = Field(..., description="XDM data type")
    format: Optional[XDMFieldFormat] = Field(None, description="XDM field format")
    generation_strategy: str = Field("auto", description="Generation strategy")
    faker_provider: Optional[str] = Field(None, description="Faker provider method")
    enum_values: Optional[List[str]] = Field(None, description="Enum values")
    constraints: FieldConstraints = Field(default_factory=FieldConstraints)
    default_value: Optional[Any] = Field(None, description="Default value")


class Relationship(BaseModel):
    """Relationship between entities."""

    from_entity: str = Field(..., description="Source entity name")
    to_entity: str = Field(..., description="Target entity name")
    type: RelationType = Field(..., description="Relationship type")
    foreign_key: str = Field(..., description="Foreign key field name")
    reference_field: str = Field("id", description="Referenced field in target entity")
    cardinality: str = Field(..., description="Cardinality description")
    description: Optional[str] = Field(None, description="Relationship description")


class EntityDefinition(BaseModel):
    """Entity definition for data generation."""

    name: str = Field(..., description="Entity name")
    description: str = Field(..., description="Entity description")
    primary_key: str = Field("id", description="Primary key field name")
    fields: List[FieldDefinition] = Field(..., description="Field definitions")
    relationships: List[Relationship] = Field(default_factory=list, description="Relationships")
    estimated_record_count: int = Field(10, description="Default record count")
    generation_order: int = Field(0, description="Generation order (0=first)")


class DomainERD(BaseModel):
    """Complete ERD for a domain."""

    domain: str = Field(..., description="Domain name")
    description: str = Field(..., description="Domain description")
    entities: List[EntityDefinition] = Field(..., description="Entity definitions")
    generation_order: List[str] = Field(..., description="Entity generation order")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    def get_entity(self, name: str) -> Optional[EntityDefinition]:
        """Get entity by name."""
        for entity in self.entities:
            if entity.name == name:
                return entity
        return None


class GenerationConfig(BaseModel):
    """Configuration for data generation."""

    output_format: OutputFormat = Field(OutputFormat.JSON, description="Output format")
    record_count: Optional[int] = Field(None, description="Override record count per entity")
    locale: str = Field("en_US", description="Faker locale (en_US, ko_KR, ja_JP, etc.)")
    include_null_values: bool = Field(True, description="Include NULL values based on probability")
    preserve_relationships: bool = Field(True, description="Maintain referential integrity")
    seed: Optional[int] = Field(None, description="Random seed for reproducibility")
    indent_json: bool = Field(True, description="Pretty-print JSON")
    include_metadata: bool = Field(False, description="Include generation metadata")


class GenerationResult(BaseModel):
    """Result of data generation."""

    domain: str = Field(..., description="Domain name")
    entities: Dict[str, int] = Field(..., description="Entity name to record count")
    output_files: List[str] = Field(..., description="Generated file paths")
    schemas_generated: int = Field(0, description="Number of XDM schemas generated")
    generation_time_seconds: float = Field(..., description="Generation time")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
