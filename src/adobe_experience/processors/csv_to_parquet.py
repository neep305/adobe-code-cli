"""CSV to Parquet converter with schema inference and validation.

Converts CSV files to Parquet format suitable for Adobe Experience Platform ingestion.
Supports:
- Automatic schema inference from CSV headers and data types
- Manual schema specification
- Data type conversion (string, int, float, boolean, datetime)
- Null value handling
- Large file processing with chunking
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from pydantic import BaseModel, Field


class CSVColumnSchema(BaseModel):
    """Schema definition for a CSV column."""
    
    name: str = Field(..., description="Column name")
    data_type: str = Field(..., description="Data type: string, int64, float64, bool, datetime")
    nullable: bool = Field(True, description="Whether column can contain null values")
    format: Optional[str] = Field(None, description="Format string for datetime parsing (e.g., '%Y-%m-%d')")


class CSVSchema(BaseModel):
    """Complete schema definition for CSV file."""
    
    columns: List[CSVColumnSchema] = Field(..., description="List of column schemas")
    
    def to_pyarrow_schema(self) -> pa.Schema:
        """Convert to PyArrow schema."""
        type_mapping = {
            "string": pa.string(),
            "int64": pa.int64(),
            "float64": pa.float64(),
            "bool": pa.bool_(),
            "datetime": pa.timestamp('us'),  # microsecond precision
        }
        
        fields = []
        for col in self.columns:
            arrow_type = type_mapping.get(col.data_type, pa.string())
            fields.append(pa.field(col.name, arrow_type, nullable=col.nullable))
        
        return pa.schema(fields)


class CSVToParquetConverter:
    """Converts CSV files to Parquet format with schema inference and validation."""
    
    # Type inference rules
    TYPE_INFERENCE_RULES = {
        'int64': lambda x: pd.api.types.is_integer_dtype(x),
        'float64': lambda x: pd.api.types.is_float_dtype(x),
        'bool': lambda x: pd.api.types.is_bool_dtype(x),
        'datetime': lambda x: pd.api.types.is_datetime64_any_dtype(x),
        'string': lambda x: True,  # Default fallback
    }
    
    def __init__(
        self,
        chunk_size: int = 100_000,
        null_values: Optional[List[str]] = None,
    ):
        """Initialize CSV to Parquet converter.
        
        Args:
            chunk_size: Number of rows to process at once for large files
            null_values: Additional strings to recognize as null (e.g., ['NA', 'N/A', ''])
        """
        self.chunk_size = chunk_size
        self.null_values = null_values or ['', 'NA', 'N/A', 'null', 'NULL', 'None']
    
    def infer_schema_from_csv(
        self,
        csv_path: Union[str, Path],
        sample_size: int = 10000,
        date_columns: Optional[List[str]] = None,
        datetime_format: Optional[str] = None,
        delimiter: str = ',',
    ) -> CSVSchema:
        """Infer schema from CSV file by analyzing sample data.
        
        Args:
            csv_path: Path to CSV file
            sample_size: Number of rows to sample for inference
            date_columns: Column names to parse as datetime
            datetime_format: Format string for datetime parsing (e.g., '%Y-%m-%d')
            delimiter: CSV delimiter character
        
        Returns:
            Inferred CSVSchema
        """
        csv_path = Path(csv_path)
        
        # Check file exists
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")
        
        # Read sample of CSV
        parse_dates = date_columns or []
        df_sample = pd.read_csv(
            csv_path,
            delimiter=delimiter,
            nrows=sample_size,
            na_values=self.null_values,
            parse_dates=parse_dates,
            date_format=datetime_format,
        )
        
        # Infer column schemas
        columns = []
        for col_name in df_sample.columns:
            col_data = df_sample[col_name]
            
            # Determine data type
            data_type = self._infer_column_type(col_data)
            
            # Check nullability
            nullable = col_data.isna().any()
            
            # Get format for datetime columns
            format_str = datetime_format if data_type == "datetime" else None
            
            columns.append(CSVColumnSchema(
                name=col_name,
                data_type=data_type,
                nullable=nullable,
                format=format_str,
            ))
        
        return CSVSchema(columns=columns)
    
    def _infer_column_type(self, series: pd.Series) -> str:
        """Infer column data type from pandas Series."""
        for dtype, check_func in self.TYPE_INFERENCE_RULES.items():
            if check_func(series):
                return dtype
        return "string"  # Default
    
    def convert(
        self,
        csv_path: Union[str, Path],
        output_path: Union[str, Path],
        schema: Optional[CSVSchema] = None,
        delimiter: str = ',',
        encoding: str = 'utf-8',
        compression: str = 'snappy',
        **csv_read_kwargs,
    ) -> Dict[str, Any]:
        """Convert CSV file to Parquet format.
        
        Args:
            csv_path: Path to input CSV file
            output_path: Path to output Parquet file
            schema: Optional schema definition (will be inferred if not provided)
            delimiter: CSV delimiter character
            encoding: CSV file encoding
            compression: Parquet compression codec ('snappy', 'gzip', 'brotli', 'none')
            **csv_read_kwargs: Additional arguments for pd.read_csv()
        
        Returns:
            Dictionary with conversion results:
            {
                "success": True,
                "input_file": "input.csv",
                "output_file": "output.parquet",
                "rows_processed": 1000,
                "columns": 10,
                "output_size_bytes": 50000,
                "schema": CSVSchema(...)
            }
        """
        csv_path = Path(csv_path)
        output_path = Path(output_path)
        
        # Check file exists
        if not csv_path.exists():
            return {
                "success": False,
                "input_file": str(csv_path),
                "output_file": str(output_path),
                "error": f"File not found: {csv_path}",
            }
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Infer schema if not provided
        if schema is None:
            try:
                schema = self.infer_schema_from_csv(csv_path, delimiter=delimiter)
            except Exception as e:
                return {
                    "success": False,
                    "input_file": str(csv_path),
                    "output_file": str(output_path),
                    "error": f"Schema inference failed: {str(e)}",
                }
        
        # Prepare column types for pandas
        dtype_map = {}
        parse_dates = []
        date_format = None
        
        for col in schema.columns:
            if col.data_type == "string":
                dtype_map[col.name] = str
            elif col.data_type == "int64":
                dtype_map[col.name] = 'Int64'  # Nullable integer
            elif col.data_type == "float64":
                dtype_map[col.name] = float
            elif col.data_type == "bool":
                dtype_map[col.name] = bool
            elif col.data_type == "datetime":
                parse_dates.append(col.name)
                if col.format:
                    date_format = col.format
        
        # Read CSV and convert to Parquet
        try:
            # For small files, read all at once
            csv_size = csv_path.stat().st_size
            
            if csv_size < 100_000_000:  # Less than 100MB
                df = pd.read_csv(
                    csv_path,
                    delimiter=delimiter,
                    encoding=encoding,
                    dtype=dtype_map,
                    parse_dates=parse_dates,
                    date_format=date_format,
                    na_values=self.null_values,
                    **csv_read_kwargs,
                )
                
                # Convert to PyArrow table
                table = pa.Table.from_pandas(df, schema=schema.to_pyarrow_schema())
                
                # Write Parquet file
                pq.write_table(
                    table,
                    output_path,
                    compression=compression,
                )
                
                rows_processed = len(df)
            
            else:
                # For large files, use chunked reading
                rows_processed = 0
                writer = None
                
                for chunk_df in pd.read_csv(
                    csv_path,
                    delimiter=delimiter,
                    encoding=encoding,
                    dtype=dtype_map,
                    parse_dates=parse_dates,
                    date_format=date_format,
                    na_values=self.null_values,
                    chunksize=self.chunk_size,
                    **csv_read_kwargs,
                ):
                    # Convert chunk to PyArrow table
                    chunk_table = pa.Table.from_pandas(
                        chunk_df,
                        schema=schema.to_pyarrow_schema()
                    )
                    
                    # Write or append to Parquet file
                    if writer is None:
                        writer = pq.ParquetWriter(
                            output_path,
                            schema.to_pyarrow_schema(),
                            compression=compression,
                        )
                    
                    writer.write_table(chunk_table)
                    rows_processed += len(chunk_df)
                
                if writer:
                    writer.close()
            
            # Get output file size
            output_size = output_path.stat().st_size
            
            return {
                "success": True,
                "input_file": str(csv_path),
                "output_file": str(output_path),
                "rows_processed": rows_processed,
                "columns": len(schema.columns),
                "output_size_bytes": output_size,
                "schema": schema,
            }
        
        except Exception as e:
            return {
                "success": False,
                "input_file": str(csv_path),
                "output_file": str(output_path),
                "error": str(e),
            }
    
    def convert_with_validation(
        self,
        csv_path: Union[str, Path],
        output_path: Union[str, Path],
        schema: CSVSchema,
        strict: bool = True,
    ) -> Dict[str, Any]:
        """Convert CSV to Parquet with strict schema validation.
        
        Args:
            csv_path: Path to input CSV file
            output_path: Path to output Parquet file
            schema: Required schema definition
            strict: If True, fail on schema mismatches; if False, coerce types
        
        Returns:
            Conversion result dictionary
        """
        # Validate that CSV columns match schema
        csv_path = Path(csv_path)
        df_sample = pd.read_csv(csv_path, nrows=1)
        csv_columns = set(df_sample.columns)
        schema_columns = {col.name for col in schema.columns}
        
        if strict:
            # Check for missing columns
            missing = schema_columns - csv_columns
            if missing:
                return {
                    "success": False,
                    "input_file": str(csv_path),
                    "error": f"Missing required columns: {missing}",
                }
            
            # Check for extra columns
            extra = csv_columns - schema_columns
            if extra:
                return {
                    "success": False,
                    "input_file": str(csv_path),
                    "error": f"Unexpected columns in CSV: {extra}",
                }
        
        # Perform conversion with provided schema
        return self.convert(csv_path, output_path, schema=schema)
    
    def batch_convert(
        self,
        csv_files: List[Union[str, Path]],
        output_dir: Union[str, Path],
        schema: Optional[CSVSchema] = None,
        file_naming: str = "same",  # "same" or "numbered"
    ) -> List[Dict[str, Any]]:
        """Convert multiple CSV files to Parquet format.
        
        Args:
            csv_files: List of CSV file paths
            output_dir: Directory for output Parquet files
            schema: Optional schema to apply to all files
            file_naming: "same" keeps original names, "numbered" uses output_001.parquet
        
        Returns:
            List of conversion result dictionaries
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        results = []
        for i, csv_file in enumerate(csv_files):
            csv_path = Path(csv_file)
            
            # Determine output filename
            if file_naming == "numbered":
                output_name = f"output_{i+1:03d}.parquet"
            else:
                output_name = csv_path.stem + ".parquet"
            
            output_path = output_dir / output_name
            
            # Convert
            result = self.convert(csv_path, output_path, schema=schema)
            results.append(result)
        
        return results
