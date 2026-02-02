"""JSON to Parquet converter with schema inference and nested object handling.

Converts JSON files to Parquet format suitable for Adobe Experience Platform ingestion.
Supports:
- JSON arrays and newline-delimited JSON (NDJSON)
- Nested object flattening with configurable separator
- Array handling (explode or stringify)
- Automatic schema inference from JSON structure
- Type coercion and normalization
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from pydantic import BaseModel, Field


class JSONConversionOptions(BaseModel):
    """Options for JSON to Parquet conversion."""
    
    flatten_nested: bool = Field(True, description="Flatten nested objects to dot-notation columns")
    flatten_separator: str = Field(".", description="Separator for flattened nested keys (e.g., 'user.name')")
    explode_arrays: bool = Field(False, description="Explode arrays to separate rows (creates duplicate rows)")
    array_handling: str = Field("stringify", description="How to handle arrays: 'stringify', 'explode', or 'keep'")
    max_nesting_level: int = Field(10, description="Maximum nesting level to flatten")
    infer_schema: bool = Field(True, description="Automatically infer schema from data")
    type_coercion: bool = Field(True, description="Coerce types (e.g., string numbers to int/float)")


class JSONToParquetConverter:
    """Converts JSON files to Parquet format with schema inference and flattening."""
    
    def __init__(self, options: Optional[JSONConversionOptions] = None):
        """Initialize JSON to Parquet converter.
        
        Args:
            options: Conversion options (uses defaults if not provided)
        """
        self.options = options or JSONConversionOptions()
    
    def _flatten_dict(
        self,
        d: Dict[str, Any],
        parent_key: str = '',
        sep: str = '.',
        level: int = 0,
    ) -> Dict[str, Any]:
        """Recursively flatten nested dictionary.
        
        Args:
            d: Dictionary to flatten
            parent_key: Parent key prefix
            sep: Separator for nested keys
            level: Current nesting level
        
        Returns:
            Flattened dictionary
        """
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            
            if isinstance(v, dict) and level < self.options.max_nesting_level:
                # Recursively flatten nested dict
                items.extend(self._flatten_dict(v, new_key, sep, level + 1).items())
            elif isinstance(v, list):
                # Handle arrays based on configuration
                if self.options.array_handling == "stringify":
                    items.append((new_key, json.dumps(v)))
                elif self.options.array_handling == "keep":
                    items.append((new_key, v))
                else:  # explode handled at DataFrame level
                    items.append((new_key, v))
            else:
                items.append((new_key, v))
        
        return dict(items)
    
    def _read_json_file(self, json_path: Path) -> List[Dict[str, Any]]:
        """Read JSON file supporting both array and NDJSON formats.
        
        Args:
            json_path: Path to JSON file
        
        Returns:
            List of JSON objects
        """
        with open(json_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        
        # Try to parse as JSON array first
        try:
            data = json.loads(content)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                return [data]  # Single object
            else:
                raise ValueError(f"Unsupported JSON type: {type(data)}")
        except json.JSONDecodeError:
            # Try as newline-delimited JSON (NDJSON)
            records = []
            for line in content.split('\n'):
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError as e:
                        raise ValueError(f"Invalid JSON line: {line[:50]}... - {e}")
            return records
    
    def _coerce_types(self, df: pd.DataFrame) -> pd.DataFrame:
        """Coerce data types for better Parquet compatibility.
        
        Args:
            df: Input DataFrame
        
        Returns:
            DataFrame with coerced types
        """
        if not self.options.type_coercion:
            return df
        
        for col in df.columns:
            # Try to convert string numbers to numeric
            if df[col].dtype == 'object':
                # Try numeric conversion
                try:
                    converted = pd.to_numeric(df[col], errors='coerce')
                    # Check if conversion was successful (no new NaNs introduced)
                    original_nulls = df[col].isna().sum()
                    converted_nulls = converted.isna().sum()
                    
                    if converted_nulls == original_nulls:
                        # Successful conversion without data loss
                        if (converted % 1 == 0).all():
                            df[col] = converted.astype('Int64')  # Nullable int
                        else:
                            df[col] = converted.astype('float64')
                except (ValueError, TypeError):
                    pass
        
        return df
    
    def convert(
        self,
        json_path: Union[str, Path],
        output_path: Union[str, Path],
        compression: str = 'snappy',
    ) -> Dict[str, Any]:
        """Convert JSON file to Parquet format.
        
        Args:
            json_path: Path to input JSON file (array or NDJSON)
            output_path: Path to output Parquet file
            compression: Parquet compression codec ('snappy', 'gzip', 'brotli', 'none')
        
        Returns:
            Dictionary with conversion results:
            {
                "success": True,
                "input_file": "input.json",
                "output_file": "output.parquet",
                "rows_processed": 1000,
                "columns": 10,
                "output_size_bytes": 50000,
                "flattened_columns": ["user.name", "user.email"]
            }
        """
        json_path = Path(json_path)
        output_path = Path(output_path)
        
        # Check file exists
        if not json_path.exists():
            return {
                "success": False,
                "input_file": str(json_path),
                "output_file": str(output_path),
                "error": f"File not found: {json_path}",
            }
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # Read JSON file
            records = self._read_json_file(json_path)
            
            if not records:
                return {
                    "success": False,
                    "input_file": str(json_path),
                    "output_file": str(output_path),
                    "error": "JSON file is empty or contains no records",
                }
            
            # Flatten nested objects if enabled
            if self.options.flatten_nested:
                flattened_records = [
                    self._flatten_dict(record, sep=self.options.flatten_separator)
                    for record in records
                ]
            else:
                flattened_records = records
            
            # Convert to DataFrame
            df = pd.DataFrame(flattened_records)
            
            # Coerce types
            df = self._coerce_types(df)
            
            # Handle array explosion if requested
            if self.options.explode_arrays:
                # Find columns with arrays
                array_cols = [col for col in df.columns if df[col].apply(lambda x: isinstance(x, list)).any()]
                if array_cols:
                    # Explode first array column (can be extended to multiple)
                    df = df.explode(array_cols[0], ignore_index=True)
            
            # Convert to PyArrow table
            table = pa.Table.from_pandas(df)
            
            # Write Parquet file
            pq.write_table(
                table,
                output_path,
                compression=compression,
            )
            
            # Get output file size
            output_size = output_path.stat().st_size
            
            # Detect flattened columns (those with separator)
            flattened_cols = [col for col in df.columns if self.options.flatten_separator in col]
            
            return {
                "success": True,
                "input_file": str(json_path),
                "output_file": str(output_path),
                "rows_processed": len(df),
                "columns": len(df.columns),
                "output_size_bytes": output_size,
                "flattened_columns": flattened_cols if flattened_cols else None,
            }
        
        except Exception as e:
            return {
                "success": False,
                "input_file": str(json_path),
                "output_file": str(output_path),
                "error": str(e),
            }
    
    def batch_convert(
        self,
        json_files: List[Union[str, Path]],
        output_dir: Union[str, Path],
        file_naming: str = "same",
    ) -> List[Dict[str, Any]]:
        """Convert multiple JSON files to Parquet format.
        
        Args:
            json_files: List of JSON file paths
            output_dir: Directory for output Parquet files
            file_naming: "same" keeps original names, "numbered" uses output_001.parquet
        
        Returns:
            List of conversion result dictionaries
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        results = []
        for i, json_file in enumerate(json_files):
            json_path = Path(json_file)
            
            # Determine output filename
            if file_naming == "numbered":
                output_name = f"output_{i+1:03d}.parquet"
            else:
                output_name = json_path.stem + ".parquet"
            
            output_path = output_dir / output_name
            
            # Convert
            result = self.convert(json_path, output_path)
            results.append(result)
        
        return results
    
    def convert_with_schema_validation(
        self,
        json_path: Union[str, Path],
        output_path: Union[str, Path],
        required_fields: List[str],
    ) -> Dict[str, Any]:
        """Convert JSON to Parquet with field validation.
        
        Args:
            json_path: Path to input JSON file
            output_path: Path to output Parquet file
            required_fields: List of required field names (supports dot notation for nested)
        
        Returns:
            Conversion result dictionary
        """
        json_path = Path(json_path)
        
        try:
            # Read and flatten
            records = self._read_json_file(json_path)
            if self.options.flatten_nested:
                flattened_records = [
                    self._flatten_dict(record, sep=self.options.flatten_separator)
                    for record in records
                ]
            else:
                flattened_records = records
            
            # Check required fields
            if flattened_records:
                available_fields = set(flattened_records[0].keys())
                missing_fields = set(required_fields) - available_fields
                
                if missing_fields:
                    return {
                        "success": False,
                        "input_file": str(json_path),
                        "error": f"Missing required fields: {missing_fields}",
                    }
            
            # Proceed with conversion
            return self.convert(json_path, output_path)
        
        except Exception as e:
            return {
                "success": False,
                "input_file": str(json_path),
                "error": str(e),
            }
