"""XDM Schema analyzer and generator."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from urllib.parse import quote

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

    # Standard XDM Profile fields that should not be in tenant namespace
    XDM_PROFILE_STANDARD_FIELDS = {
        "email", "emailAddress", "personalEmail",
        "firstName", "first_name", "lastName", "last_name",
        "phone", "phoneNumber", "mobilePhone",
        "birthDate", "birth_date", "gender",
        "homeAddress", "workAddress", "mailingAddress",
        "person", "personName"
    }

    @classmethod
    def from_sample_data(
        cls,
        data: List[Dict[str, Any]],
        schema_name: str,
        schema_description: Optional[str] = None,
        tenant_id: Optional[str] = None,
        class_id: Optional[str] = None,
    ) -> XDMSchema:
        """Generate XDM schema from sample data.

        Args:
            data: List of sample records.
            schema_name: Schema name/title.
            schema_description: Schema description.
            tenant_id: AEP tenant ID for schema namespace.
            class_id: XDM class ID (e.g., https://ns.adobe.com/xdm/context/profile).

        Returns:
            Generated XDM schema.
        """
        if not data:
            raise ValueError("Sample data cannot be empty")

        # Collect all field names
        all_fields = set()
        for record in data:
            all_fields.update(record.keys())

        # Separate standard XDM fields from custom fields
        custom_properties = {}
        standard_properties = {}
        
        for field_name in all_fields:
            sample_values = [record.get(field_name) for record in data]
            field = cls.analyze_field(field_name, sample_values)
            
            # Check if it's a standard XDM field
            if field_name.lower().replace("_", "") in {f.lower().replace("_", "") for f in cls.XDM_PROFILE_STANDARD_FIELDS}:
                # Map to XDM standard structure
                if "email" in field_name.lower():
                    # Don't add email to custom fields, it's handled by Profile class
                    continue
                elif "first" in field_name.lower() and "name" in field_name.lower():
                    # Don't add, handled by person.name.firstName
                    continue
                elif "last" in field_name.lower() and "name" in field_name.lower():
                    # Don't add, handled by person.name.lastName  
                    continue
                else:
                    standard_properties[field_name] = field
            else:
                custom_properties[field_name] = field

        # Create schema structure with tenant namespace
        schema_name_slug = schema_name.lower().replace(" ", "_")
        if tenant_id and custom_properties:
            schema_id = f"https://ns.adobe.com/{tenant_id}/schemas/{schema_name_slug}"
            # Custom fields must be nested under _<tenant_id>
            properties = {
                f"_{tenant_id}": XDMField(
                    title=f"{schema_name} Custom Fields",
                    description="Custom tenant-specific fields",
                    type=XDMDataType.OBJECT,
                    properties=custom_properties,
                )
            }
        else:
            schema_id = f"https://ns.adobe.com/{schema_name_slug}"
            properties = custom_properties if custom_properties else standard_properties

        # Use provided class_id or default to profile
        effective_class_id = class_id or "https://ns.adobe.com/xdm/context/profile"

        return XDMSchema(
            schema_id=schema_id,
            title=schema_name,
            description=schema_description or f"Auto-generated schema for {schema_name}",
            type=XDMDataType.OBJECT,
            properties=properties,
            meta_class=effective_class_id,
            all_of=[
                XDMSchemaRef(ref=effective_class_id),
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
        # URL encode schema_id to handle special characters (e.g., https://)
        encoded_id = quote(schema_id, safe="")
        path = f"{self.SCHEMA_REGISTRY_PATH}/tenant/schemas/{encoded_id}"

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
        # URL encode schema_id to handle special characters
        encoded_id = quote(schema_id, safe="")
        path = f"{self.SCHEMA_REGISTRY_PATH}/tenant/schemas/{encoded_id}"
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
        # URL encode schema_id to handle special characters
        encoded_id = quote(schema_id, safe="")
        path = f"{self.SCHEMA_REGISTRY_PATH}/tenant/schemas/{encoded_id}"

        return await self.client.delete(path)

    # Field Groups API
    async def list_field_groups(
        self,
        container_id: str = "tenant",
        limit: int = 50,
    ) -> Dict[str, Any]:
        """List field groups.

        Args:
            container_id: Container ID (tenant or global).
            limit: Maximum number of field groups to return.

        Returns:
            List of field groups.
        """
        path = f"{self.SCHEMA_REGISTRY_PATH}/{container_id}/fieldgroups"

        return await self.client.get(
            path,
            params={"limit": limit},
            headers={"Accept": "application/vnd.adobe.xed-id+json"},
        )

    async def get_field_group(
        self,
        field_group_id: str,
        container_id: str = "tenant",
    ) -> Dict[str, Any]:
        """Get field group by ID.

        Args:
            field_group_id: Field group ID.
            container_id: Container ID (tenant or global).

        Returns:
            Field group definition.
        """
        encoded_id = quote(field_group_id, safe="")
        path = f"{self.SCHEMA_REGISTRY_PATH}/{container_id}/fieldgroups/{encoded_id}"

        return await self.client.get(
            path,
            headers={"Accept": "application/vnd.adobe.xed-full+json; version=1"},
        )

    async def create_field_group(
        self,
        field_group: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Create a custom field group.

        Args:
            field_group: Field group definition.

        Returns:
            Created field group response.
        """
        path = f"{self.SCHEMA_REGISTRY_PATH}/tenant/fieldgroups"

        return await self.client.post(
            path,
            json=field_group,
            headers={"Accept": "application/vnd.adobe.xed-full+json; version=1"},
        )

    async def update_field_group(
        self,
        field_group_id: str,
        field_group: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Update a custom field group (full replacement).

        Args:
            field_group_id: Field group ID to update.
            field_group: Updated field group definition.

        Returns:
            Updated field group response.
        """
        encoded_id = quote(field_group_id, safe="")
        path = f"{self.SCHEMA_REGISTRY_PATH}/tenant/fieldgroups/{encoded_id}"

        return await self.client.put(
            path,
            json=field_group,
            headers={"Accept": "application/vnd.adobe.xed-full+json; version=1"},
        )

    async def patch_field_group(
        self,
        field_group_id: str,
        patch_operations: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Partially update a field group using JSON Patch.

        Args:
            field_group_id: Field group ID to update.
            patch_operations: JSON Patch operations (RFC 6902).

        Returns:
            Updated field group response.
        """
        encoded_id = quote(field_group_id, safe="")
        path = f"{self.SCHEMA_REGISTRY_PATH}/tenant/fieldgroups/{encoded_id}"

        return await self.client.patch(
            path,
            json=patch_operations,
            headers={
                "Accept": "application/vnd.adobe.xed-full+json; version=1",
                "Content-Type": "application/json-patch+json",
            },
        )

    async def delete_field_group(self, field_group_id: str) -> Dict[str, Any]:
        """Delete a custom field group.

        Args:
            field_group_id: Field group ID to delete.

        Returns:
            Delete response.
        """
        encoded_id = quote(field_group_id, safe="")
        path = f"{self.SCHEMA_REGISTRY_PATH}/tenant/fieldgroups/{encoded_id}"

        return await self.client.delete(path)

    # Descriptors API
    async def list_descriptors(
        self,
        container_id: str = "tenant",
        limit: int = 50,
    ) -> Dict[str, Any]:
        """List descriptors.

        Args:
            container_id: Container ID (tenant or global).
            limit: Maximum number of descriptors to return.

        Returns:
            List of descriptors.
        """
        path = f"{self.SCHEMA_REGISTRY_PATH}/{container_id}/descriptors"

        return await self.client.get(
            path,
            params={"limit": limit},
            headers={"Accept": "application/vnd.adobe.xed-id+json"},
        )

    async def get_descriptor(
        self,
        descriptor_id: str,
        container_id: str = "tenant",
    ) -> Dict[str, Any]:
        """Get descriptor by ID.

        Args:
            descriptor_id: Descriptor ID.
            container_id: Container ID (tenant or global).

        Returns:
            Descriptor definition.
        """
        encoded_id = quote(descriptor_id, safe="")
        path = f"{self.SCHEMA_REGISTRY_PATH}/{container_id}/descriptors/{encoded_id}"

        return await self.client.get(
            path,
            headers={"Accept": "application/vnd.adobe.xed-full+json; version=1"},
        )

    async def create_descriptor(
        self,
        descriptor: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Create a descriptor (e.g., identity, relationship, friendly name).

        Args:
            descriptor: Descriptor definition.

        Returns:
            Created descriptor response.
        """
        path = f"{self.SCHEMA_REGISTRY_PATH}/tenant/descriptors"

        return await self.client.post(
            path,
            json=descriptor,
            headers={"Accept": "application/vnd.adobe.xed-full+json; version=1"},
        )

    async def update_descriptor(
        self,
        descriptor_id: str,
        descriptor: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Update a descriptor (full replacement).

        Args:
            descriptor_id: Descriptor ID to update.
            descriptor: Updated descriptor definition.

        Returns:
            Updated descriptor response.
        """
        encoded_id = quote(descriptor_id, safe="")
        path = f"{self.SCHEMA_REGISTRY_PATH}/tenant/descriptors/{encoded_id}"

        return await self.client.put(
            path,
            json=descriptor,
            headers={"Accept": "application/vnd.adobe.xed-full+json; version=1"},
        )

    async def delete_descriptor(self, descriptor_id: str) -> Dict[str, Any]:
        """Delete a descriptor.

        Args:
            descriptor_id: Descriptor ID to delete.

        Returns:
            Delete response.
        """
        encoded_id = quote(descriptor_id, safe="")
        path = f"{self.SCHEMA_REGISTRY_PATH}/tenant/descriptors/{encoded_id}"

        return await self.client.delete(path)
