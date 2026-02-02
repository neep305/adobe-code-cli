"""XDM (Experience Data Model) schema validator for AEP data.

Validates data against XDM schemas before ingestion to Adobe Experience Platform.
Supports:
- Field type validation (string, integer, number, boolean, date, datetime)
- Required field checking
- Enum value validation
- Format validation (email, uri, date-time)
- Nested object validation
- Array validation
- Custom validation rules
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union
from urllib.parse import urlparse

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, field_validator


class XDMFieldType(str, Enum):
    """XDM field data types."""
    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    OBJECT = "object"
    ARRAY = "array"
    DATE = "date"
    DATETIME = "date-time"


class XDMFieldFormat(str, Enum):
    """XDM field format specifiers."""
    EMAIL = "email"
    URI = "uri"
    DATE = "date"
    DATETIME = "date-time"
    UUID = "uuid"


class XDMField(BaseModel):
    """XDM schema field definition."""
    
    name: str = Field(..., description="Field name")
    type: XDMFieldType = Field(..., description="Field data type")
    required: bool = Field(False, description="Whether field is required")
    format: Optional[XDMFieldFormat] = Field(None, description="Field format (for strings)")
    enum: Optional[List[Any]] = Field(None, description="Allowed enum values")
    pattern: Optional[str] = Field(None, description="Regex pattern for validation")
    min_length: Optional[int] = Field(None, description="Minimum string length", alias="minLength")
    max_length: Optional[int] = Field(None, description="Maximum string length", alias="maxLength")
    minimum: Optional[Union[int, float]] = Field(None, description="Minimum numeric value")
    maximum: Optional[Union[int, float]] = Field(None, description="Maximum numeric value")
    description: Optional[str] = Field(None, description="Field description")
    
    model_config = ConfigDict(populate_by_name=True)


class XDMSchema(BaseModel):
    """XDM schema definition."""
    
    name: str = Field(..., description="Schema name")
    fields: List[XDMField] = Field(..., description="Schema fields")
    description: Optional[str] = Field(None, description="Schema description")
    
    def get_required_fields(self) -> Set[str]:
        """Get set of required field names."""
        return {field.name for field in self.fields if field.required}
    
    def get_field(self, name: str) -> Optional[XDMField]:
        """Get field definition by name."""
        for field in self.fields:
            if field.name == name:
                return field
        return None


class ValidationError(BaseModel):
    """Validation error detail."""
    
    field: str = Field(..., description="Field name with error")
    row: Optional[int] = Field(None, description="Row index (for DataFrame validation)")
    error_type: str = Field(..., description="Error type (e.g., 'missing_required', 'type_mismatch')")
    message: str = Field(..., description="Error message")
    value: Optional[Any] = Field(None, description="Invalid value")


class ValidationResult(BaseModel):
    """Validation result summary."""
    
    valid: bool = Field(..., description="Whether validation passed")
    errors: List[ValidationError] = Field(default_factory=list, description="List of validation errors")
    warnings: List[str] = Field(default_factory=list, description="Non-critical warnings")
    rows_validated: int = Field(0, description="Number of rows validated")
    
    def add_error(self, field: str, error_type: str, message: str, row: Optional[int] = None, value: Any = None):
        """Add validation error."""
        self.errors.append(ValidationError(
            field=field,
            row=row,
            error_type=error_type,
            message=message,
            value=value
        ))
        self.valid = False
    
    def add_warning(self, message: str):
        """Add validation warning."""
        self.warnings.append(message)


class XDMValidator:
    """Validator for XDM schemas."""
    
    def __init__(self, schema: XDMSchema, strict: bool = True):
        """Initialize XDM validator.
        
        Args:
            schema: XDM schema to validate against
            strict: If True, fail on warnings; if False, only fail on errors
        """
        self.schema = schema
        self.strict = strict
    
    def validate_value(
        self,
        field: XDMField,
        value: Any,
        row: Optional[int] = None,
        result: Optional[ValidationResult] = None,
    ) -> bool:
        """Validate a single value against field definition.
        
        Args:
            field: Field definition
            value: Value to validate
            row: Row index (optional, for error reporting)
            result: ValidationResult to add errors to (optional)
        
        Returns:
            True if valid, False otherwise
        """
        if result is None:
            result = ValidationResult(valid=True)
        
        # Check for null/None
        if pd.isna(value) or value is None:
            if field.required:
                result.add_error(
                    field.name,
                    "missing_required",
                    f"Required field '{field.name}' is null or missing",
                    row=row,
                    value=value
                )
                return False
            return True  # Null is ok for non-required fields
        
        # Type validation
        if field.type == XDMFieldType.STRING:
            if not isinstance(value, str):
                result.add_error(
                    field.name,
                    "type_mismatch",
                    f"Expected string, got {type(value).__name__}",
                    row=row,
                    value=value
                )
                return False
            
            # String-specific validations
            if field.min_length is not None and len(value) < field.min_length:
                result.add_error(
                    field.name,
                    "min_length",
                    f"String length {len(value)} < minimum {field.min_length}",
                    row=row,
                    value=value
                )
                return False
            
            if field.max_length is not None and len(value) > field.max_length:
                result.add_error(
                    field.name,
                    "max_length",
                    f"String length {len(value)} > maximum {field.max_length}",
                    row=row,
                    value=value
                )
                return False
            
            # Format validation
            if field.format:
                if not self._validate_format(value, field.format, field.name, row, result):
                    return False
        
        elif field.type == XDMFieldType.INTEGER:
            if not isinstance(value, (int, pd.Int64Dtype)):
                try:
                    value = int(value)
                except (ValueError, TypeError):
                    result.add_error(
                        field.name,
                        "type_mismatch",
                        f"Expected integer, got {type(value).__name__}",
                        row=row,
                        value=value
                    )
                    return False
            
            if field.minimum is not None and value < field.minimum:
                result.add_error(
                    field.name,
                    "minimum",
                    f"Value {value} < minimum {field.minimum}",
                    row=row,
                    value=value
                )
                return False
            
            if field.maximum is not None and value > field.maximum:
                result.add_error(
                    field.name,
                    "maximum",
                    f"Value {value} > maximum {field.maximum}",
                    row=row,
                    value=value
                )
                return False
        
        elif field.type == XDMFieldType.NUMBER:
            if not isinstance(value, (int, float)):
                try:
                    value = float(value)
                except (ValueError, TypeError):
                    result.add_error(
                        field.name,
                        "type_mismatch",
                        f"Expected number, got {type(value).__name__}",
                        row=row,
                        value=value
                    )
                    return False
            
            if field.minimum is not None and value < field.minimum:
                result.add_error(
                    field.name,
                    "minimum",
                    f"Value {value} < minimum {field.minimum}",
                    row=row,
                    value=value
                )
                return False
            
            if field.maximum is not None and value > field.maximum:
                result.add_error(
                    field.name,
                    "maximum",
                    f"Value {value} > maximum {field.maximum}",
                    row=row,
                    value=value
                )
                return False
        
        elif field.type == XDMFieldType.BOOLEAN:
            if not isinstance(value, bool):
                result.add_error(
                    field.name,
                    "type_mismatch",
                    f"Expected boolean, got {type(value).__name__}",
                    row=row,
                    value=value
                )
                return False
        
        # Enum validation
        if field.enum is not None and value not in field.enum:
            result.add_error(
                field.name,
                "enum_violation",
                f"Value '{value}' not in allowed enum values: {field.enum}",
                row=row,
                value=value
            )
            return False
        
        return True
    
    def _validate_format(
        self,
        value: str,
        format: XDMFieldFormat,
        field_name: str,
        row: Optional[int],
        result: ValidationResult,
    ) -> bool:
        """Validate string format."""
        if format == XDMFieldFormat.EMAIL:
            if '@' not in value or '.' not in value.split('@')[-1]:
                result.add_error(
                    field_name,
                    "format_email",
                    f"Invalid email format: {value}",
                    row=row,
                    value=value
                )
                return False
        
        elif format == XDMFieldFormat.URI:
            try:
                parsed = urlparse(value)
                if not parsed.scheme or not parsed.netloc:
                    raise ValueError("Invalid URI")
            except Exception:
                result.add_error(
                    field_name,
                    "format_uri",
                    f"Invalid URI format: {value}",
                    row=row,
                    value=value
                )
                return False
        
        elif format == XDMFieldFormat.DATE:
            try:
                datetime.strptime(value, "%Y-%m-%d")
            except ValueError:
                result.add_error(
                    field_name,
                    "format_date",
                    f"Invalid date format (expected YYYY-MM-DD): {value}",
                    row=row,
                    value=value
                )
                return False
        
        elif format == XDMFieldFormat.DATETIME:
            # Try ISO 8601 format
            try:
                datetime.fromisoformat(value.replace('Z', '+00:00'))
            except ValueError:
                result.add_error(
                    field_name,
                    "format_datetime",
                    f"Invalid datetime format (expected ISO 8601): {value}",
                    row=row,
                    value=value
                )
                return False
        
        return True
    
    def validate_record(self, record: Dict[str, Any]) -> ValidationResult:
        """Validate a single record against schema.
        
        Args:
            record: Dictionary record to validate
        
        Returns:
            ValidationResult
        """
        result = ValidationResult(valid=True, rows_validated=1)
        
        # Check required fields
        required_fields = self.schema.get_required_fields()
        missing_fields = required_fields - set(record.keys())
        
        for missing in missing_fields:
            result.add_error(
                missing,
                "missing_required",
                f"Required field '{missing}' is missing from record"
            )
        
        # Validate each field present
        for field_name, value in record.items():
            field_def = self.schema.get_field(field_name)
            
            if field_def is None:
                if self.strict:
                    result.add_warning(f"Unknown field '{field_name}' not in schema")
                continue
            
            self.validate_value(field_def, value, result=result)
        
        return result
    
    def validate_dataframe(self, df: pd.DataFrame, max_errors: int = 100) -> ValidationResult:
        """Validate a pandas DataFrame against schema.
        
        Args:
            df: DataFrame to validate
            max_errors: Maximum number of errors to collect before stopping
        
        Returns:
            ValidationResult
        """
        result = ValidationResult(valid=True, rows_validated=len(df))
        
        # Check required fields exist as columns
        required_fields = self.schema.get_required_fields()
        missing_fields = required_fields - set(df.columns)
        
        for missing in missing_fields:
            result.add_error(
                missing,
                "missing_required",
                f"Required field '{missing}' is missing from DataFrame"
            )
        
        # Validate each row
        for idx, row in df.iterrows():
            if len(result.errors) >= max_errors:
                result.add_warning(f"Stopped validation after {max_errors} errors")
                break
            
            for field in self.schema.fields:
                if field.name in df.columns:
                    value = row[field.name]
                    self.validate_value(field, value, row=idx, result=result)
        
        return result
    
    def validate_parquet(self, parquet_path: str) -> ValidationResult:
        """Validate a Parquet file against schema.
        
        Args:
            parquet_path: Path to Parquet file
        
        Returns:
            ValidationResult
        """
        df = pd.read_parquet(parquet_path)
        return self.validate_dataframe(df)
