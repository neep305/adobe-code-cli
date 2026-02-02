"""Dataset scanner for multi-file ERD analysis."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class FieldMetadata(BaseModel):
    """Metadata for a field in a dataset."""
    
    name: str
    detected_type: str  # string, number, integer, boolean, object, array
    sample_values: List[Any] = Field(default_factory=list)
    null_count: int = 0
    unique_count: Optional[int] = None
    is_potential_id: bool = False  # Fields ending in _id
    is_potential_foreign_key: bool = False


class EntityMetadata(BaseModel):
    """Metadata for a single entity (file)."""
    
    file_path: str
    entity_name: str  # Derived from filename
    record_count: int
    sample_records: List[Dict[str, Any]]
    fields: Dict[str, FieldMetadata]
    potential_primary_key: Optional[str] = None
    potential_foreign_keys: List[str] = Field(default_factory=list)


class DatasetScanResult(BaseModel):
    """Result of scanning a dataset directory."""
    
    dataset_path: str
    entities: List[EntityMetadata]
    total_files: int
    total_records: int


class DatasetScanner:
    """Scanner for analyzing multi-file datasets."""
    
    def __init__(self, sample_size: int = 10):
        """Initialize scanner.
        
        Args:
            sample_size: Maximum number of records to sample per file.
        """
        self.sample_size = sample_size
    
    def scan_directory(self, directory: Path) -> DatasetScanResult:
        """Scan a directory for JSON data files.
        
        Args:
            directory: Path to directory containing JSON files.
            
        Returns:
            Scan results with entity metadata.
        """
        if not directory.exists() or not directory.is_dir():
            raise ValueError(f"Directory not found: {directory}")
        
        json_files = list(directory.glob("*.json"))
        if not json_files:
            raise ValueError(f"No JSON files found in {directory}")
        
        entities = []
        total_records = 0
        
        for json_file in json_files:
            entity = self._scan_file(json_file)
            entities.append(entity)
            total_records += entity.record_count
        
        return DatasetScanResult(
            dataset_path=str(directory),
            entities=entities,
            total_files=len(json_files),
            total_records=total_records,
        )
    
    def _scan_file(self, file_path: Path) -> EntityMetadata:
        """Scan a single JSON file.
        
        Args:
            file_path: Path to JSON file.
            
        Returns:
            Entity metadata.
        """
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Ensure data is a list
        if not isinstance(data, list):
            data = [data]
        
        # Sample records
        sample_records = data[:self.sample_size]
        
        # Extract entity name from filename
        entity_name = file_path.stem
        
        # Analyze fields
        fields = self._analyze_fields(data)
        
        # Detect potential keys
        potential_primary_key = self._detect_primary_key(fields, entity_name)
        potential_foreign_keys = self._detect_foreign_keys(fields)
        
        return EntityMetadata(
            file_path=str(file_path),
            entity_name=entity_name,
            record_count=len(data),
            sample_records=sample_records,
            fields=fields,
            potential_primary_key=potential_primary_key,
            potential_foreign_keys=potential_foreign_keys,
        )
    
    def _analyze_fields(self, records: List[Dict[str, Any]]) -> Dict[str, FieldMetadata]:
        """Analyze fields across all records.
        
        Args:
            records: List of data records.
            
        Returns:
            Field metadata dictionary.
        """
        field_stats: Dict[str, Dict[str, Any]] = {}
        
        # Collect field information
        for record in records:
            for field_name, value in record.items():
                if field_name not in field_stats:
                    field_stats[field_name] = {
                        "types": [],
                        "samples": [],
                        "null_count": 0,
                        "unique_values": set(),
                    }
                
                if value is None:
                    field_stats[field_name]["null_count"] += 1
                else:
                    field_type = self._get_type(value)
                    field_stats[field_name]["types"].append(field_type)
                    
                    # Sample first few values
                    if len(field_stats[field_name]["samples"]) < 5:
                        field_stats[field_name]["samples"].append(value)
                    
                    # Track unique values for potential IDs
                    if isinstance(value, (str, int)):
                        field_stats[field_name]["unique_values"].add(value)
        
        # Build field metadata
        fields = {}
        for field_name, stats in field_stats.items():
            # Determine dominant type
            type_counts = {}
            for t in stats["types"]:
                type_counts[t] = type_counts.get(t, 0) + 1
            detected_type = max(type_counts, key=type_counts.get) if type_counts else "unknown"
            
            # Check if potential ID field
            is_potential_id = (
                field_name.endswith("_id") or 
                field_name == "id" or
                field_name.endswith("_ID") or
                field_name.endswith("Id")
            )
            
            fields[field_name] = FieldMetadata(
                name=field_name,
                detected_type=detected_type,
                sample_values=stats["samples"][:5],
                null_count=stats["null_count"],
                unique_count=len(stats["unique_values"]),
                is_potential_id=is_potential_id,
            )
        
        return fields
    
    def _get_type(self, value: Any) -> str:
        """Get JSON type of a value.
        
        Args:
            value: Value to check.
            
        Returns:
            Type string.
        """
        if value is None:
            return "null"
        elif isinstance(value, bool):
            return "boolean"
        elif isinstance(value, int):
            return "integer"
        elif isinstance(value, float):
            return "number"
        elif isinstance(value, str):
            return "string"
        elif isinstance(value, list):
            return "array"
        elif isinstance(value, dict):
            return "object"
        return "unknown"
    
    def _detect_primary_key(
        self, 
        fields: Dict[str, FieldMetadata],
        entity_name: str,
    ) -> Optional[str]:
        """Detect potential primary key field.
        
        Args:
            fields: Field metadata dictionary.
            entity_name: Entity name (from filename).
            
        Returns:
            Primary key field name or None.
        """
        # Look for common primary key patterns
        candidates = []
        
        for field_name, metadata in fields.items():
            # Check naming patterns
            if field_name == f"{entity_name}_id":
                candidates.append((field_name, 3))  # High priority
            elif field_name == "id":
                candidates.append((field_name, 2))
            elif metadata.is_potential_id and entity_name.rstrip("s") in field_name:
                candidates.append((field_name, 1))
        
        # Return highest priority candidate
        if candidates:
            candidates.sort(key=lambda x: x[1], reverse=True)
            return candidates[0][0]
        
        return None
    
    def _detect_foreign_keys(
        self,
        fields: Dict[str, FieldMetadata],
    ) -> List[str]:
        """Detect potential foreign key fields.
        
        Args:
            fields: Field metadata dictionary.
            
        Returns:
            List of foreign key field names.
        """
        foreign_keys = []
        
        for field_name, metadata in fields.items():
            # Foreign key pattern: ends with _id but not the entity's own ID
            if metadata.is_potential_id:
                foreign_keys.append(field_name)
        
        return foreign_keys
