"""XDM Schema analyzer and generator."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from adobe_experience.aep.client import AEPClient
from adobe_experience.schema.models import (
    XDMDataType,
    XDMField,
    XDMFieldFormat,
    XDMIdentity,
    XDMSchema,
    XDMSchemaRef,
)


class XDMSchemaAnalyzer:
    """Analyze and generate XDM schemas from sample data."""

    @staticmethod
    def infer_xdm_type(value: Any) -> XDMDataType:
        """Infer XDM data type from Python value.

        Args:
            value: Sample value.

        Returns:
            Inferred XDM data type.
        """
        if isinstance(value, bool):
            return XDMDataType.BOOLEAN
        elif isinstance(value, int):
            return XDMDataType.INTEGER
        elif isinstance(value, float):
            return XDMDataType.NUMBER
        elif isinstance(value, str):
            return XDMDataType.STRING
        elif isinstance(value, dict):
            return XDMDataType.OBJECT
        elif isinstance(value, list):
            return XDMDataType.ARRAY
        else:
            return XDMDataType.STRING

    @staticmethod
    def detect_format(field_name: str, value: str) -> Optional[XDMFieldFormat]:
        """Detect field format from name and value patterns.

        Args:
            field_name: Field name.
            value: Sample string value.

        Returns:
            Detected format or None.
        """
        field_lower = field_name.lower()

        # Email detection
        if "email" in field_lower or "@" in value:
            return XDMFieldFormat.EMAIL

        # URI detection
        if "url" in field_lower or "uri" in field_lower or value.startswith(("http://", "https://")):
            return XDMFieldFormat.URI

        # Date/DateTime detection
        if "date" in field_lower or "time" in field_lower or "timestamp" in field_lower:
            if "T" in value or " " in value:
                return XDMFieldFormat.DATE_TIME
            return XDMFieldFormat.DATE

        return None

    @classmethod
    def analyze_field(
        cls,
        field_name: str,
        sample_values: List[Any],
    ) -> XDMField:
        """Analyze a field from sample values.

        Args:
            field_name: Field name.
            sample_values: List of sample values.

        Returns:
            XDM field definition.
        """
        # Filter out None values
        non_null_values = [v for v in sample_values if v is not None]

        if not non_null_values:
            return XDMField(
                title=field_name.replace("_", " ").title(),
                description=f"Field: {field_name}",
                type=XDMDataType.STRING,
            )

        # Infer type from first non-null value
        sample = non_null_values[0]
        xdm_type = cls.infer_xdm_type(sample)

        field = XDMField(
            title=field_name.replace("_", " ").title(),
            description=f"Field: {field_name}",
            type=xdm_type,
        )

        # Add format for strings
        if xdm_type == XDMDataType.STRING and isinstance(sample, str):
            field.format = cls.detect_format(field_name, sample)

        # Handle arrays
        if xdm_type == XDMDataType.ARRAY and isinstance(sample, list) and sample:
            item_type = cls.infer_xdm_type(sample[0])
            field.items = XDMField(
                title="Item",
                description="Array item",
                type=item_type,
            )

        # Handle objects (nested)
        if xdm_type == XDMDataType.OBJECT and isinstance(sample, dict):
            field.properties = {}
            for key, value in sample.items():
                field.properties[key] = cls.analyze_field(key, [value])

        # Detect numeric ranges
        if xdm_type in (XDMDataType.INTEGER, XDMDataType.NUMBER):
            numeric_values = [v for v in non_null_values if isinstance(v, (int, float))]
            if numeric_values:
                field.minimum = min(numeric_values)
                field.maximum = max(numeric_values)

        # Enum detection disabled for now - AEP requires meta:enum for enum fields
        # TODO: Add meta:enum support when enum detection is re-enabled
        # if xdm_type == XDMDataType.STRING:
        #     unique_values = set(str(v) for v in non_null_values)
        #     unique_ratio = len(unique_values) / len(non_null_values) if non_null_values else 1
        #     if len(unique_values) <= 5 and len(non_null_values) >= 5 and unique_ratio < 0.5:
        #         field.enum = sorted(unique_values)

        return field

    @classmethod
    def from_sample_data(
        cls,
        data: List[Dict[str, Any]],
        schema_name: str,
        schema_description: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> XDMSchema:
        """Generate XDM schema from sample data.

        Args:
            data: List of sample records.
            schema_name: Schema name/title.
            schema_description: Schema description.
            tenant_id: AEP tenant ID for schema namespace.

        Returns:
            Generated XDM schema.
        """
        if not data:
            raise ValueError("Sample data cannot be empty")

        # Collect all field names
        all_fields = set()
        for record in data:
            all_fields.update(record.keys())

        # Analyze each field with tenant prefix
        properties = {}
        for field_name in all_fields:
            sample_values = [record.get(field_name) for record in data]
            field = cls.analyze_field(field_name, sample_values)
            # Prefix field name with tenant ID if provided
            prefixed_name = f"{tenant_id}:{field_name}" if tenant_id else field_name
            properties[prefixed_name] = field

        # Create schema with proper tenant namespace
        schema_name_slug = schema_name.lower().replace(" ", "_")
        if tenant_id:
            schema_id = f"https://ns.adobe.com/{tenant_id}/schemas/{schema_name_slug}"
        else:
            schema_id = f"https://ns.adobe.com/{schema_name_slug}"

        return XDMSchema(
            schema_id=schema_id,
            title=schema_name,
            description=schema_description or f"Auto-generated schema for {schema_name}",
            type=XDMDataType.OBJECT,
            properties=properties,
            all_of=[
                XDMSchemaRef(ref="https://ns.adobe.com/xdm/context/profile"),
            ],
        )

    @classmethod
    def from_json_file(
        cls,
        file_path: Union[str, Path],
        schema_name: str,
        schema_description: Optional[str] = None,
    ) -> XDMSchema:
        """Generate XDM schema from JSON file.

        Args:
            file_path: Path to JSON file.
            schema_name: Schema name/title.
            schema_description: Schema description.

        Returns:
            Generated XDM schema.
        """
        path = Path(file_path)
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list):
            data = [data]

        return cls.from_sample_data(data, schema_name, schema_description)


class XDMSchemaRegistry:
    """Interface to AEP Schema Registry API."""

    SCHEMA_REGISTRY_PATH = "/data/foundation/schemaregistry"

    def __init__(self, client: AEPClient) -> None:
        """Initialize schema registry.

        Args:
            client: AEP API client.
        """
        self.client = client

    async def create_schema(self, schema: XDMSchema) -> Dict[str, Any]:
        """Create schema in AEP Schema Registry.

        Args:
            schema: XDM schema to create.

        Returns:
            Created schema response.
        """
        path = f"{self.SCHEMA_REGISTRY_PATH}/tenant/schemas"
        schema_data = schema.model_dump(by_alias=True, exclude_none=True)

        return await self.client.post(
            path,
            json=schema_data,
            headers={"Accept": "application/vnd.adobe.xed-full+json; version=1"},
        )

    async def get_schema(self, schema_id: str) -> Dict[str, Any]:
        """Get schema by ID.

        Args:
            schema_id: Schema ID or name.

        Returns:
            Schema definition.
        """
        path = f"{self.SCHEMA_REGISTRY_PATH}/tenant/schemas/{schema_id}"

        return await self.client.get(
            path,
            headers={"Accept": "application/vnd.adobe.xed-full+json; version=1"},
        )

    async def list_schemas(self, limit: int = 50) -> Dict[str, Any]:
        """List all schemas.

        Args:
            limit: Maximum number of schemas to return.

        Returns:
            List of schemas.
        """
        path = f"{self.SCHEMA_REGISTRY_PATH}/tenant/schemas"

        return await self.client.get(
            path,
            params={"limit": limit},
            headers={"Accept": "application/vnd.adobe.xed-id+json"},
        )

    async def update_schema(self, schema_id: str, schema: XDMSchema) -> Dict[str, Any]:
        """Update existing schema.

        Args:
            schema_id: Schema ID to update.
            schema: Updated schema definition.

        Returns:
            Updated schema response.
        """
        path = f"{self.SCHEMA_REGISTRY_PATH}/tenant/schemas/{schema_id}"
        schema_data = schema.model_dump(by_alias=True, exclude_none=True)

        return await self.client.put(
            path,
            json=schema_data,
            headers={"Accept": "application/vnd.adobe.xed-full+json; version=1"},
        )

    async def delete_schema(self, schema_id: str) -> Dict[str, Any]:
        """Delete schema.

        Args:
            schema_id: Schema ID to delete.

        Returns:
            Delete response.
        """
        path = f"{self.SCHEMA_REGISTRY_PATH}/tenant/schemas/{schema_id}"

        return await self.client.delete(path)
