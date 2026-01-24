"""Tests for XDM schema analyzer."""

import pytest

from adobe_aep.schema.models import XDMDataType, XDMFieldFormat
from adobe_aep.schema.xdm import XDMSchemaAnalyzer


def test_infer_xdm_type_string():
    """Test string type inference."""
    assert XDMSchemaAnalyzer.infer_xdm_type("hello") == XDMDataType.STRING


def test_infer_xdm_type_integer():
    """Test integer type inference."""
    assert XDMSchemaAnalyzer.infer_xdm_type(42) == XDMDataType.INTEGER


def test_infer_xdm_type_number():
    """Test number type inference."""
    assert XDMSchemaAnalyzer.infer_xdm_type(3.14) == XDMDataType.NUMBER


def test_infer_xdm_type_boolean():
    """Test boolean type inference."""
    assert XDMSchemaAnalyzer.infer_xdm_type(True) == XDMDataType.BOOLEAN


def test_detect_format_email():
    """Test email format detection."""
    assert (
        XDMSchemaAnalyzer.detect_format("email", "user@example.com") == XDMFieldFormat.EMAIL
    )
    assert (
        XDMSchemaAnalyzer.detect_format("user_email", "test@test.com") == XDMFieldFormat.EMAIL
    )


def test_detect_format_uri():
    """Test URI format detection."""
    assert (
        XDMSchemaAnalyzer.detect_format("website", "https://example.com") == XDMFieldFormat.URI
    )
    assert XDMSchemaAnalyzer.detect_format("url", "http://test.com") == XDMFieldFormat.URI


def test_analyze_field_with_enum():
    """Test field analysis with enum detection."""
    values = ["active", "inactive", "active", "pending", "active"]
    field = XDMSchemaAnalyzer.analyze_field("status", values)

    assert field.type == XDMDataType.STRING
    assert field.enum is not None
    assert set(field.enum) == {"active", "inactive", "pending"}


def test_from_sample_data():
    """Test schema generation from sample data."""
    sample_data = [
        {"name": "John Doe", "age": 30, "email": "john@example.com"},
        {"name": "Jane Smith", "age": 25, "email": "jane@example.com"},
    ]

    schema = XDMSchemaAnalyzer.from_sample_data(
        sample_data,
        "Customer Profile",
        "Customer data schema",
    )

    assert schema.title == "Customer Profile"
    assert schema.description == "Customer data schema"
    assert schema.properties is not None
    assert "name" in schema.properties
    assert "age" in schema.properties
    assert "email" in schema.properties

    # Check types
    assert schema.properties["name"].type == XDMDataType.STRING
    assert schema.properties["age"].type == XDMDataType.INTEGER
    assert schema.properties["email"].type == XDMDataType.STRING
    assert schema.properties["email"].format == XDMFieldFormat.EMAIL


def test_analyze_nested_object():
    """Test analysis of nested objects."""
    sample_data = [
        {
            "user": {
                "name": "John",
                "contact": {
                    "email": "john@example.com",
                    "phone": "+1234567890",
                },
            }
        }
    ]

    schema = XDMSchemaAnalyzer.from_sample_data(sample_data, "Nested Schema")

    assert schema.properties is not None
    assert "user" in schema.properties
    assert schema.properties["user"].type == XDMDataType.OBJECT
    assert schema.properties["user"].properties is not None
    assert "contact" in schema.properties["user"].properties


def test_analyze_array_field():
    """Test analysis of array fields."""
    sample_data = [
        {"tags": ["python", "adobe", "aep"]},
        {"tags": ["data", "engineering"]},
    ]

    schema = XDMSchemaAnalyzer.from_sample_data(sample_data, "Tags Schema")

    assert schema.properties is not None
    assert "tags" in schema.properties
    assert schema.properties["tags"].type == XDMDataType.ARRAY
    assert schema.properties["tags"].items is not None
    assert schema.properties["tags"].items.type == XDMDataType.STRING


def test_empty_sample_data():
    """Test handling of empty sample data."""
    with pytest.raises(ValueError, match="Sample data cannot be empty"):
        XDMSchemaAnalyzer.from_sample_data([], "Empty Schema")
