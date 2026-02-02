"""Unit tests for XDM schema validator."""

import pandas as pd
import pytest

from adobe_experience.processors.xdm_validator import (
    ValidationResult,
    XDMField,
    XDMFieldFormat,
    XDMFieldType,
    XDMSchema,
    XDMValidator,
)


@pytest.fixture
def simple_schema():
    """Create simple XDM schema for testing."""
    return XDMSchema(
        name="TestSchema",
        fields=[
            XDMField(name="id", type=XDMFieldType.INTEGER, required=True),
            XDMField(name="name", type=XDMFieldType.STRING, required=True, min_length=2, max_length=50),
            XDMField(name="email", type=XDMFieldType.STRING, format=XDMFieldFormat.EMAIL),
            XDMField(name="age", type=XDMFieldType.INTEGER, minimum=0, maximum=150),
            XDMField(name="active", type=XDMFieldType.BOOLEAN),
        ]
    )


@pytest.fixture
def enum_schema():
    """Create schema with enum fields."""
    return XDMSchema(
        name="EnumSchema",
        fields=[
            XDMField(name="id", type=XDMFieldType.INTEGER, required=True),
            XDMField(name="status", type=XDMFieldType.STRING, enum=["active", "inactive", "pending"]),
            XDMField(name="priority", type=XDMFieldType.INTEGER, enum=[1, 2, 3, 4, 5]),
        ]
    )


def test_xdm_field_creation():
    """Test XDMField model creation."""
    field = XDMField(
        name="email",
        type=XDMFieldType.STRING,
        required=True,
        format=XDMFieldFormat.EMAIL
    )
    assert field.name == "email"
    assert field.type == XDMFieldType.STRING
    assert field.required is True
    assert field.format == XDMFieldFormat.EMAIL


def test_xdm_schema_get_required_fields(simple_schema: XDMSchema):
    """Test getting required fields from schema."""
    required = simple_schema.get_required_fields()
    assert required == {"id", "name"}


def test_xdm_schema_get_field(simple_schema: XDMSchema):
    """Test getting field by name."""
    field = simple_schema.get_field("email")
    assert field is not None
    assert field.name == "email"
    assert field.format == XDMFieldFormat.EMAIL
    
    missing = simple_schema.get_field("nonexistent")
    assert missing is None


def test_validate_valid_record(simple_schema: XDMSchema):
    """Test validation of valid record."""
    validator = XDMValidator(simple_schema)
    
    record = {
        "id": 1,
        "name": "Alice",
        "email": "alice@example.com",
        "age": 30,
        "active": True
    }
    
    result = validator.validate_record(record)
    assert result.valid is True
    assert len(result.errors) == 0


def test_validate_missing_required_field(simple_schema: XDMSchema):
    """Test validation fails with missing required field."""
    validator = XDMValidator(simple_schema)
    
    record = {
        "id": 1,
        # Missing "name" (required)
        "email": "alice@example.com"
    }
    
    result = validator.validate_record(record)
    assert result.valid is False
    assert len(result.errors) == 1
    assert result.errors[0].field == "name"
    assert result.errors[0].error_type == "missing_required"


def test_validate_type_mismatch_string(simple_schema: XDMSchema):
    """Test validation fails with type mismatch."""
    validator = XDMValidator(simple_schema)
    
    record = {
        "id": 1,
        "name": 12345,  # Should be string
        "email": "alice@example.com"
    }
    
    result = validator.validate_record(record)
    assert result.valid is False
    assert any(e.field == "name" and e.error_type == "type_mismatch" for e in result.errors)


def test_validate_type_mismatch_integer(simple_schema: XDMSchema):
    """Test integer type validation."""
    validator = XDMValidator(simple_schema)
    
    record = {
        "id": "not_an_int",  # Should be integer
        "name": "Alice"
    }
    
    result = validator.validate_record(record)
    assert result.valid is False
    assert any(e.field == "id" and e.error_type == "type_mismatch" for e in result.errors)


def test_validate_string_length_min(simple_schema: XDMSchema):
    """Test minimum string length validation."""
    validator = XDMValidator(simple_schema)
    
    record = {
        "id": 1,
        "name": "A",  # Too short (min=2)
    }
    
    result = validator.validate_record(record)
    assert result.valid is False
    assert any(e.field == "name" and e.error_type == "min_length" for e in result.errors)


def test_validate_string_length_max(simple_schema: XDMSchema):
    """Test maximum string length validation."""
    validator = XDMValidator(simple_schema)
    
    record = {
        "id": 1,
        "name": "A" * 51,  # Too long (max=50)
    }
    
    result = validator.validate_record(record)
    assert result.valid is False
    assert any(e.field == "name" and e.error_type == "max_length" for e in result.errors)


def test_validate_integer_minimum(simple_schema: XDMSchema):
    """Test minimum integer value validation."""
    validator = XDMValidator(simple_schema)
    
    record = {
        "id": 1,
        "name": "Alice",
        "age": -5  # Below minimum (0)
    }
    
    result = validator.validate_record(record)
    assert result.valid is False
    assert any(e.field == "age" and e.error_type == "minimum" for e in result.errors)


def test_validate_integer_maximum(simple_schema: XDMSchema):
    """Test maximum integer value validation."""
    validator = XDMValidator(simple_schema)
    
    record = {
        "id": 1,
        "name": "Alice",
        "age": 200  # Above maximum (150)
    }
    
    result = validator.validate_record(record)
    assert result.valid is False
    assert any(e.field == "age" and e.error_type == "maximum" for e in result.errors)


def test_validate_email_format(simple_schema: XDMSchema):
    """Test email format validation."""
    validator = XDMValidator(simple_schema)
    
    # Valid email
    record = {
        "id": 1,
        "name": "Alice",
        "email": "alice@example.com"
    }
    result = validator.validate_record(record)
    assert result.valid is True
    
    # Invalid email
    record["email"] = "not-an-email"
    result = validator.validate_record(record)
    assert result.valid is False
    assert any(e.field == "email" and e.error_type == "format_email" for e in result.errors)


def test_validate_enum_valid(enum_schema: XDMSchema):
    """Test enum validation with valid value."""
    validator = XDMValidator(enum_schema)
    
    record = {
        "id": 1,
        "status": "active",
        "priority": 3
    }
    
    result = validator.validate_record(record)
    assert result.valid is True


def test_validate_enum_invalid(enum_schema: XDMSchema):
    """Test enum validation with invalid value."""
    validator = XDMValidator(enum_schema)
    
    record = {
        "id": 1,
        "status": "invalid_status",  # Not in enum
        "priority": 3
    }
    
    result = validator.validate_record(record)
    assert result.valid is False
    assert any(e.field == "status" and e.error_type == "enum_violation" for e in result.errors)


def test_validate_boolean_type():
    """Test boolean type validation."""
    schema = XDMSchema(
        name="BoolSchema",
        fields=[
            XDMField(name="id", type=XDMFieldType.INTEGER, required=True),
            XDMField(name="active", type=XDMFieldType.BOOLEAN, required=True),
        ]
    )
    validator = XDMValidator(schema)
    
    # Valid boolean
    result = validator.validate_record({"id": 1, "active": True})
    assert result.valid is True
    
    # Invalid boolean
    result = validator.validate_record({"id": 1, "active": "yes"})
    assert result.valid is False


def test_validate_dataframe(simple_schema: XDMSchema):
    """Test DataFrame validation."""
    validator = XDMValidator(simple_schema)
    
    df = pd.DataFrame([
        {"id": 1, "name": "Alice", "email": "alice@example.com", "age": 30, "active": True},
        {"id": 2, "name": "Bob", "email": "bob@example.com", "age": 25, "active": False},
        {"id": 3, "name": "Charlie", "email": "charlie@example.com", "age": 35, "active": True},
    ])
    
    result = validator.validate_dataframe(df)
    assert result.valid is True
    assert result.rows_validated == 3


def test_validate_dataframe_with_errors(simple_schema: XDMSchema):
    """Test DataFrame validation with errors."""
    validator = XDMValidator(simple_schema)
    
    df = pd.DataFrame([
        {"id": 1, "name": "Alice", "email": "alice@example.com", "age": 30},
        {"id": 2, "name": "B", "email": "invalid", "age": 200},  # Multiple errors
        {"id": 3, "name": "Charlie", "email": "charlie@example.com", "age": 35},
    ])
    
    result = validator.validate_dataframe(df)
    assert result.valid is False
    assert len(result.errors) > 0
    
    # Check errors include row numbers
    assert any(e.row == 1 for e in result.errors)


def test_validate_dataframe_missing_column(simple_schema: XDMSchema):
    """Test DataFrame validation with missing required column."""
    validator = XDMValidator(simple_schema)
    
    df = pd.DataFrame([
        {"id": 1, "email": "alice@example.com"},  # Missing "name"
    ])
    
    result = validator.validate_dataframe(df)
    assert result.valid is False
    assert any(e.field == "name" and e.error_type == "missing_required" for e in result.errors)


def test_validate_null_values_required_field(simple_schema: XDMSchema):
    """Test null validation for required fields."""
    validator = XDMValidator(simple_schema)
    
    record = {
        "id": 1,
        "name": None,  # Required field is null
    }
    
    result = validator.validate_record(record)
    assert result.valid is False
    assert any(e.field == "name" and e.error_type == "missing_required" for e in result.errors)


def test_validate_null_values_optional_field(simple_schema: XDMSchema):
    """Test null values are ok for optional fields."""
    validator = XDMValidator(simple_schema)
    
    record = {
        "id": 1,
        "name": "Alice",
        "email": None,  # Optional field
        "age": None,  # Optional field
    }
    
    result = validator.validate_record(record)
    assert result.valid is True


def test_validate_unknown_field_strict_mode(simple_schema: XDMSchema):
    """Test unknown field in strict mode generates warning."""
    validator = XDMValidator(simple_schema, strict=True)
    
    record = {
        "id": 1,
        "name": "Alice",
        "unknown_field": "value"
    }
    
    result = validator.validate_record(record)
    assert result.valid is True  # Warnings don't fail validation
    assert len(result.warnings) > 0


def test_validation_result_add_error():
    """Test adding errors to ValidationResult."""
    result = ValidationResult(valid=True)
    
    result.add_error("field1", "type_mismatch", "Invalid type", row=5, value="bad")
    
    assert result.valid is False
    assert len(result.errors) == 1
    assert result.errors[0].field == "field1"
    assert result.errors[0].row == 5


def test_validation_max_errors(simple_schema: XDMSchema):
    """Test max_errors limit in DataFrame validation."""
    validator = XDMValidator(simple_schema)
    
    # Create DataFrame with many errors
    df = pd.DataFrame([
        {"id": "bad", "name": "A"}  # Multiple errors per row
        for _ in range(200)
    ])
    
    result = validator.validate_dataframe(df, max_errors=10)
    assert result.valid is False
    assert len(result.errors) <= 10
    assert len(result.warnings) > 0  # Should have warning about stopping


def test_validate_parquet_file(simple_schema: XDMSchema, tmp_path):
    """Test validating Parquet file."""
    validator = XDMValidator(simple_schema)
    
    # Create valid Parquet file
    df = pd.DataFrame([
        {"id": 1, "name": "Alice", "email": "alice@example.com", "age": 30, "active": True},
        {"id": 2, "name": "Bob", "email": "bob@example.com", "age": 25, "active": False},
    ])
    
    parquet_file = tmp_path / "test.parquet"
    df.to_parquet(parquet_file)
    
    result = validator.validate_parquet(str(parquet_file))
    assert result.valid is True
    assert result.rows_validated == 2
