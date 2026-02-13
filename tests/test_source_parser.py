"""Tests for source parser utility functions."""

import pytest
from adobe_experience.flow.models import SourceConnection, ConnectionSpec
from adobe_experience.flow.source_parser import (
    extract_source_entity,
    extract_source_summary,
    format_source_params,
    get_source_type_from_spec,
)


def test_extract_s3_source():
    """Test extracting S3 bucket and path."""
    conn = SourceConnection(
        id="test-123",
        name="S3 Source",
        connection_spec=ConnectionSpec(id="test-spec", version="1.0"),
        params={
            "s3": {
                "bucketName": "customer-data",
                "folderPath": "/daily-exports"
            }
        }
    )
    
    entity = extract_source_entity(conn)
    assert entity == "s3://customer-data/daily-exports"


def test_extract_s3_alternative_format():
    """Test S3 with params directly in dict."""
    conn = SourceConnection(
        id="test-123",
        name="S3 Source",
        connection_spec=ConnectionSpec(id="test-spec", version="1.0"),
        params={
            "bucketName": "my-bucket",
            "path": "/data"
        }
    )
    
    entity = extract_source_entity(conn)
    assert entity == "s3://my-bucket/data"


def test_extract_salesforce_object():
    """Test extracting Salesforce object name."""
    conn = SourceConnection(
        id="test-123",
        name="SF Source",
        connection_spec=ConnectionSpec(id="test-spec", version="1.0"),
        params={
            "objectName": "Account"
        }
    )
    
    entity = extract_source_entity(conn)
    assert entity == "Salesforce Object: Account"


def test_extract_database_table_with_schema():
    """Test extracting database table with schema."""
    conn = SourceConnection(
        id="test-123",
        name="DB Source",
        connection_spec=ConnectionSpec(id="test-spec", version="1.0"),
        params={
            "schemaName": "analytics",
            "tableName": "user_events"
        }
    )
    
    entity = extract_source_entity(conn)
    assert entity == "analytics.user_events"


def test_extract_database_table_without_schema():
    """Test extracting database table without schema."""
    conn = SourceConnection(
        id="test-123",
        name="DB Source",
        connection_spec=ConnectionSpec(id="test-spec", version="1.0"),
        params={
            "tableName": "users"
        }
    )
    
    entity = extract_source_entity(conn)
    assert entity == "users"


def test_extract_azure_blob():
    """Test extracting Azure Blob Storage path."""
    conn = SourceConnection(
        id="test-123",
        name="Azure Source",
        connection_spec=ConnectionSpec(id="test-spec", version="1.0"),
        params={
            "containerName": "data-container",
            "blobPath": "/exports/daily"
        }
    )
    
    entity = extract_source_entity(conn)
    assert entity == "azure://data-container/exports/daily"


def test_extract_adls_gen2():
    """Test extracting Azure Data Lake Storage Gen2 path."""
    conn = SourceConnection(
        id="test-123",
        name="ADLS Source",
        connection_spec=ConnectionSpec(id="test-spec", version="1.0"),
        params={
            "filesystem": "datalake",
            "directoryPath": "/raw/events"
        }
    )
    
    entity = extract_source_entity(conn)
    assert entity == "adls://datalake/raw/events"


def test_extract_gcs():
    """Test extracting Google Cloud Storage path."""
    conn = SourceConnection(
        id="test-123",
        name="GCS Source",
        connection_spec=ConnectionSpec(
            id="32e8f412-cdf7-464c-9885-8a96ce6e7b1e",  # GCS spec ID
            name="Google Cloud Storage",
            version="1.0"
        ),
        params={
            "bucketName": "gcs-bucket",
            "path": "/data"
        }
    )
    
    entity = extract_source_entity(conn)
    # With GCS spec ID, should return gs://
    assert entity == "gs://gcs-bucket/data"


def test_extract_sftp():
    """Test extracting SFTP path."""
    conn = SourceConnection(
        id="test-123",
        name="SFTP Source",
        connection_spec=ConnectionSpec(id="test-spec", version="1.0"),
        params={
            "host": "sftp.example.com",
            "port": 22,
            "remotePath": "/uploads/data"
        }
    )
    
    entity = extract_source_entity(conn)
    assert entity == "sftp://sftp.example.com/uploads/data"


def test_extract_api_endpoint():
    """Test extracting API endpoint."""
    conn = SourceConnection(
        id="test-123",
        name="API Source",
        connection_spec=ConnectionSpec(id="test-spec", version="1.0"),
        params={
            "url": "https://api.example.com/v1/data"
        }
    )
    
    entity = extract_source_entity(conn)
    assert entity == "API: https://api.example.com/v1/data"


def test_extract_no_params():
    """Test with no params returns None."""
    conn = SourceConnection(
        id="test-123",
        name="Source",
        connection_spec=ConnectionSpec(id="test-spec", version="1.0"),
        params=None
    )
    
    entity = extract_source_entity(conn)
    assert entity is None


def test_extract_unknown_params():
    """Test with unknown params returns None."""
    conn = SourceConnection(
        id="test-123",
        name="Source",
        connection_spec=ConnectionSpec(id="test-spec", version="1.0"),
        params={
            "unknownKey": "value"
        }
    )
    
    entity = extract_source_entity(conn)
    assert entity is None


def test_extract_source_summary():
    """Test extracting full source summary."""
    conn = SourceConnection(
        id="test-123",
        name="S3 Source",
        connection_spec=ConnectionSpec(
            id="ecadc60c-7455-4d65-9f77-8f1b1e6e1a1a",
            name="Amazon S3",
            version="1.0"
        ),
        params={
            "s3": {
                "bucketName": "customer-data",
                "folderPath": "/exports"
            }
        }
    )
    
    summary = extract_source_summary(conn)
    assert summary == "Amazon S3: s3://customer-data/exports"


def test_format_source_params_simple():
    """Test formatting simple params."""
    params = {
        "bucketName": "my-bucket",
        "path": "/data"
    }
    
    formatted = format_source_params(params)
    assert "bucketName" in formatted
    assert "my-bucket" in formatted


def test_format_source_params_nested():
    """Test formatting nested params."""
    params = {
        "s3": {
            "bucketName": "test",
            "folderPath": "/path"
        }
    }
    
    formatted = format_source_params(params)
    assert "s3" in formatted
    assert "bucketName" in formatted


def test_format_source_params_truncate_long_value():
    """Test truncating long values."""
    params = {
        "longValue": "a" * 100
    }
    
    formatted = format_source_params(params)
    assert "..." in formatted
    assert len(formatted) < 200


def test_get_source_type_from_spec():
    """Test getting source type from spec ID."""
    s3_spec = "ecadc60c-7455-4d65-9f77-8f1b1e6e1a1a"
    source_type = get_source_type_from_spec(s3_spec)
    assert source_type == "Amazon S3"
    
    # Unknown spec
    unknown = get_source_type_from_spec("unknown-id")
    assert unknown is None


def test_source_connection_helper_methods():
    """Test SourceConnection helper methods."""
    conn = SourceConnection(
        id="test-123",
        name="S3 Source",
        connection_spec=ConnectionSpec(
            id="ecadc60c-7455-4d65-9f77-8f1b1e6e1a1a",
            name="Amazon S3",
            version="1.0"
        ),
        params={
            "s3": {
                "bucketName": "data",
                "folderPath": "/exports"
            }
        }
    )
    
    # Test get_entity_name method
    entity = conn.get_entity_name()
    assert entity == "s3://data/exports"
    
    # Test get_source_summary method
    summary = conn.get_source_summary()
    assert summary == "Amazon S3: s3://data/exports"
