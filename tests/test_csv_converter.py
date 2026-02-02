"""Unit tests for CSV to Parquet converter."""

import json
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq
import pytest

from adobe_experience.processors.csv_to_parquet import (
    CSVColumnSchema,
    CSVSchema,
    CSVToParquetConverter,
)


@pytest.fixture
def converter():
    """Create CSVToParquetConverter instance."""
    return CSVToParquetConverter()


@pytest.fixture
def simple_csv(tmp_path: Path) -> Path:
    """Create a simple CSV file for testing."""
    csv_file = tmp_path / "simple.csv"
    csv_content = """id,name,age,salary,active,join_date
1,Alice,30,75000.50,true,2020-01-15
2,Bob,25,65000.00,true,2021-03-20
3,Charlie,35,85000.75,false,2019-07-10
4,Diana,28,70000.00,true,2022-05-01
"""
    csv_file.write_text(csv_content)
    return csv_file


@pytest.fixture
def csv_with_nulls(tmp_path: Path) -> Path:
    """Create CSV with null values."""
    csv_file = tmp_path / "with_nulls.csv"
    csv_content = """id,name,age,salary
1,Alice,30,75000.50
2,Bob,,65000.00
3,Charlie,35,
4,Diana,28,70000.00
5,,40,80000.00
"""
    csv_file.write_text(csv_content)
    return csv_file


@pytest.fixture
def large_csv(tmp_path: Path) -> Path:
    """Create a large CSV file for chunking tests (200k rows)."""
    csv_file = tmp_path / "large.csv"
    
    # Create 200k rows
    with open(csv_file, 'w') as f:
        f.write("id,name,value\n")
        for i in range(200_000):
            f.write(f"{i},User{i},{i * 1.5}\n")
    
    return csv_file


def test_column_schema_creation():
    """Test CSVColumnSchema model."""
    col = CSVColumnSchema(
        name="age",
        data_type="int64",
        nullable=False
    )
    assert col.name == "age"
    assert col.data_type == "int64"
    assert col.nullable is False


def test_csv_schema_to_pyarrow():
    """Test conversion of CSVSchema to PyArrow schema."""
    schema = CSVSchema(columns=[
        CSVColumnSchema(name="id", data_type="int64", nullable=False),
        CSVColumnSchema(name="name", data_type="string", nullable=True),
        CSVColumnSchema(name="salary", data_type="float64", nullable=True),
    ])
    
    arrow_schema = schema.to_pyarrow_schema()
    assert len(arrow_schema) == 3
    assert arrow_schema.field("id").name == "id"
    assert str(arrow_schema.field("id").type) == "int64"


def test_infer_schema_from_csv(converter: CSVToParquetConverter, simple_csv: Path):
    """Test schema inference from CSV file."""
    schema = converter.infer_schema_from_csv(simple_csv)
    
    assert len(schema.columns) == 6
    
    # Check inferred types
    col_map = {col.name: col for col in schema.columns}
    assert col_map["id"].data_type == "int64"
    assert col_map["name"].data_type == "string"
    assert col_map["age"].data_type == "int64"
    assert col_map["salary"].data_type == "float64"
    assert col_map["active"].data_type == "bool"


def test_infer_schema_with_date_columns(converter: CSVToParquetConverter, simple_csv: Path):
    """Test schema inference with datetime columns."""
    schema = converter.infer_schema_from_csv(
        simple_csv,
        date_columns=["join_date"],
        datetime_format="%Y-%m-%d"
    )
    
    col_map = {col.name: col for col in schema.columns}
    assert col_map["join_date"].data_type == "datetime"
    assert col_map["join_date"].format == "%Y-%m-%d"


def test_infer_schema_detects_nullability(converter: CSVToParquetConverter, csv_with_nulls: Path):
    """Test that schema inference detects nullable columns."""
    schema = converter.infer_schema_from_csv(csv_with_nulls)
    
    col_map = {col.name: col for col in schema.columns}
    assert col_map["name"].nullable is True  # Has null value
    assert col_map["salary"].nullable is True  # Has null value


def test_convert_simple_csv(converter: CSVToParquetConverter, simple_csv: Path, tmp_path: Path):
    """Test basic CSV to Parquet conversion."""
    output_file = tmp_path / "output.parquet"
    
    result = converter.convert(simple_csv, output_file)
    
    assert result["success"] is True
    assert result["rows_processed"] == 4
    assert result["columns"] == 6
    assert output_file.exists()
    
    # Verify Parquet file contents
    df = pd.read_parquet(output_file)
    assert len(df) == 4
    assert list(df.columns) == ["id", "name", "age", "salary", "active", "join_date"]


def test_convert_with_explicit_schema(converter: CSVToParquetConverter, simple_csv: Path, tmp_path: Path):
    """Test conversion with explicitly provided schema."""
    schema = CSVSchema(columns=[
        CSVColumnSchema(name="id", data_type="int64", nullable=False),
        CSVColumnSchema(name="name", data_type="string", nullable=True),
        CSVColumnSchema(name="age", data_type="int64", nullable=True),
        CSVColumnSchema(name="salary", data_type="float64", nullable=True),
        CSVColumnSchema(name="active", data_type="bool", nullable=False),
        CSVColumnSchema(name="join_date", data_type="datetime", nullable=False, format="%Y-%m-%d"),
    ])
    
    output_file = tmp_path / "output.parquet"
    result = converter.convert(simple_csv, output_file, schema=schema)
    
    assert result["success"] is True
    assert output_file.exists()


def test_convert_with_compression(converter: CSVToParquetConverter, simple_csv: Path, tmp_path: Path):
    """Test Parquet compression options."""
    # Test different compression codecs
    for compression in ['snappy', 'gzip', 'none']:
        output_file = tmp_path / f"output_{compression}.parquet"
        result = converter.convert(simple_csv, output_file, compression=compression)
        
        assert result["success"] is True
        assert output_file.exists()


def test_convert_handles_null_values(converter: CSVToParquetConverter, csv_with_nulls: Path, tmp_path: Path):
    """Test that null values are handled correctly."""
    output_file = tmp_path / "output.parquet"
    result = converter.convert(csv_with_nulls, output_file)
    
    assert result["success"] is True
    
    # Verify null handling
    df = pd.read_parquet(output_file)
    assert df["name"].isna().sum() == 1  # One null name
    assert df["age"].isna().sum() == 1  # One null age
    assert df["salary"].isna().sum() == 1  # One null salary


def test_convert_large_file_with_chunking(converter: CSVToParquetConverter, large_csv: Path, tmp_path: Path):
    """Test chunked processing of large CSV files."""
    output_file = tmp_path / "large_output.parquet"
    
    # Set small chunk size for testing
    converter.chunk_size = 50_000
    
    result = converter.convert(large_csv, output_file)
    
    assert result["success"] is True
    assert result["rows_processed"] == 200_000
    assert output_file.exists()
    
    # Verify all rows were written
    df = pd.read_parquet(output_file)
    assert len(df) == 200_000


def test_convert_with_validation_success(converter: CSVToParquetConverter, simple_csv: Path, tmp_path: Path):
    """Test conversion with schema validation (matching schema)."""
    # Infer schema first
    schema = converter.infer_schema_from_csv(simple_csv)
    
    output_file = tmp_path / "output.parquet"
    result = converter.convert_with_validation(simple_csv, output_file, schema, strict=True)
    
    assert result["success"] is True


def test_convert_with_validation_missing_column(converter: CSVToParquetConverter, simple_csv: Path, tmp_path: Path):
    """Test strict validation fails with missing required column."""
    # Schema with extra column not in CSV
    schema = CSVSchema(columns=[
        CSVColumnSchema(name="id", data_type="int64", nullable=False),
        CSVColumnSchema(name="name", data_type="string", nullable=True),
        CSVColumnSchema(name="missing_column", data_type="string", nullable=False),
    ])
    
    output_file = tmp_path / "output.parquet"
    result = converter.convert_with_validation(simple_csv, output_file, schema, strict=True)
    
    assert result["success"] is False
    assert "Missing required columns" in result["error"]


def test_convert_with_validation_extra_column(converter: CSVToParquetConverter, simple_csv: Path, tmp_path: Path):
    """Test strict validation fails with unexpected columns."""
    # Schema missing columns that exist in CSV
    schema = CSVSchema(columns=[
        CSVColumnSchema(name="id", data_type="int64", nullable=False),
        CSVColumnSchema(name="name", data_type="string", nullable=True),
    ])
    
    output_file = tmp_path / "output.parquet"
    result = converter.convert_with_validation(simple_csv, output_file, schema, strict=True)
    
    assert result["success"] is False
    assert "Unexpected columns" in result["error"]


def test_convert_file_not_found(converter: CSVToParquetConverter, tmp_path: Path):
    """Test error handling for non-existent file."""
    nonexistent = tmp_path / "nonexistent.csv"
    output_file = tmp_path / "output.parquet"
    
    result = converter.convert(nonexistent, output_file)
    
    assert result["success"] is False
    assert "error" in result


def test_batch_convert(converter: CSVToParquetConverter, tmp_path: Path):
    """Test batch conversion of multiple CSV files."""
    # Create multiple CSV files
    csv_files = []
    for i in range(3):
        csv_file = tmp_path / f"input_{i}.csv"
        csv_file.write_text(f"id,value\n{i},{i * 10}\n")
        csv_files.append(csv_file)
    
    output_dir = tmp_path / "output"
    results = converter.batch_convert(csv_files, output_dir, file_naming="same")
    
    assert len(results) == 3
    for result in results:
        assert result["success"] is True
    
    # Verify output files exist
    assert (output_dir / "input_0.parquet").exists()
    assert (output_dir / "input_1.parquet").exists()
    assert (output_dir / "input_2.parquet").exists()


def test_batch_convert_with_numbered_output(converter: CSVToParquetConverter, tmp_path: Path):
    """Test batch conversion with numbered output files."""
    csv_files = []
    for i in range(2):
        csv_file = tmp_path / f"input_{i}.csv"
        csv_file.write_text(f"id,value\n{i},{i * 10}\n")
        csv_files.append(csv_file)
    
    output_dir = tmp_path / "output"
    results = converter.batch_convert(csv_files, output_dir, file_naming="numbered")
    
    assert (output_dir / "output_001.parquet").exists()
    assert (output_dir / "output_002.parquet").exists()


def test_custom_delimiter(converter: CSVToParquetConverter, tmp_path: Path):
    """Test CSV with custom delimiter (TSV)."""
    tsv_file = tmp_path / "data.tsv"
    tsv_file.write_text("id\tname\tvalue\n1\tAlice\t100\n2\tBob\t200\n")
    
    output_file = tmp_path / "output.parquet"
    result = converter.convert(tsv_file, output_file, delimiter='\t')
    
    assert result["success"] is True
    df = pd.read_parquet(output_file)
    assert len(df) == 2
    assert list(df.columns) == ["id", "name", "value"]


def test_output_size_reported(converter: CSVToParquetConverter, simple_csv: Path, tmp_path: Path):
    """Test that output file size is reported in result."""
    output_file = tmp_path / "output.parquet"
    result = converter.convert(simple_csv, output_file)
    
    assert result["success"] is True
    assert "output_size_bytes" in result
    assert result["output_size_bytes"] > 0
    assert result["output_size_bytes"] == output_file.stat().st_size
