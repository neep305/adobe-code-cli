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

    @staticmethod
    def detect_boolean_variant(sample_values: List[Any]) -> Optional[Dict[str, Any]]:
        """Detect boolean-like values in various formats.

        Args:
            sample_values: Sample values to analyze.

        Returns:
            Detection result with conversion info, or None if not boolean variant.
        """
        non_null = [v for v in sample_values if v is not None]
        if not non_null:
            return None

        # Convert to strings for pattern matching
        str_values = [str(v).lower().strip() for v in non_null]
        unique_values = set(str_values)

        # Check for boolean variants
        boolean_patterns = {
            "numeric_01": ({"0", "1"}, {"1"}, {"0"}),
            "yes_no": ({"yes", "no", "y", "n"}, {"yes", "y"}, {"no", "n"}),
            "true_false": ({"true", "false", "t", "f"}, {"true", "t"}, {"false", "f"}),
            "on_off": ({"on", "off"}, {"on"}, {"off"}),
            "enabled_disabled": ({"enabled", "disabled"}, {"enabled"}, {"disabled"}),
        }

        for variant_type, (all_values, true_vals, false_vals) in boolean_patterns.items():
            if unique_values.issubset(all_values):
                return {
                    "is_boolean_variant": True,
                    "variant_type": variant_type,
                    "true_values": list(true_vals),
                    "false_values": list(false_vals),
                    "confidence": 0.95,
                }

        return None

    @staticmethod
    def detect_date_format(field_name: str, sample_values: List[Any]) -> Optional[Dict[str, Any]]:
        """Detect date/datetime formats.

        Args:
            field_name: Field name for semantic hints.
            sample_values: Sample values to analyze.

        Returns:
            Detection result with format info, or None if not a date field.
        """
        import re

        non_null = [v for v in sample_values if v is not None]
        if not non_null:
            return None

        # Check field name for date-related keywords
        field_lower = field_name.lower()
        has_date_name = any(
            keyword in field_lower
            for keyword in ["date", "time", "timestamp", "created", "updated", "modified"]
        )

        sample_str = str(non_null[0])

        # ISO 8601 detection
        iso8601_pattern = r"^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})?)?$"
        if re.match(iso8601_pattern, sample_str):
            is_datetime = "T" in sample_str
            return {
                "is_date_field": True,
                "detected_format": "iso8601",
                "is_datetime": is_datetime,
                "confidence": 0.98,
            }

        # Epoch timestamp (numeric)
        if isinstance(non_null[0], (int, float)):
            val = float(non_null[0])
            # Unix timestamp in seconds (10 digits)
            if 1000000000 <= val < 10000000000:
                return {
                    "is_date_field": True,
                    "detected_format": "epoch_seconds",
                    "is_datetime": True,
                    "confidence": 0.85,
                }
            # Unix timestamp in milliseconds (13 digits)
            elif 1000000000000 <= val < 10000000000000:
                return {
                    "is_date_field": True,
                    "detected_format": "epoch_millis",
                    "is_datetime": True,
                    "confidence": 0.85,
                }

        # Custom date formats (only if field name suggests it's a date)
        if has_date_name and isinstance(non_null[0], str):
            # Common patterns
            patterns = [
                (r"^\d{2}/\d{2}/\d{4}$", "MM/DD/YYYY"),
                (r"^\d{4}/\d{2}/\d{2}$", "YYYY/MM/DD"),
                (r"^\d{2}-\d{2}-\d{4}$", "DD-MM-YYYY"),
            ]
            for pattern, format_str in patterns:
                if re.match(pattern, sample_str):
                    return {
                        "is_date_field": True,
                        "detected_format": "custom",
                        "format_pattern": format_str,
                        "is_datetime": False,
                        "confidence": 0.75,
                    }

        return None

    @staticmethod
    def detect_phone_number(field_name: str, sample_values: List[Any]) -> Optional[Dict[str, Any]]:
        """Detect phone number fields.

        Args:
            field_name: Field name for semantic hints.
            sample_values: Sample values to analyze.

        Returns:
            Detection result, or None if not a phone number field.
        """
        import re

        # Check field name
        field_lower = field_name.lower()
        has_phone_name = any(
            keyword in field_lower for keyword in ["phone", "tel", "mobile", "cell", "fax"]
        )

        if not has_phone_name:
            return None

        non_null = [v for v in sample_values if v is not None]
        if not non_null:
            return None

        sample_str = str(non_null[0])

        # Phone number patterns
        # International: +1-555-123-4567, +44 20 1234 5678
        # National: (555) 123-4567, 555-123-4567
        # E.164: +15551234567
        phone_patterns = [
            r"^\+\d{1,3}[\s\-]?\(?\d{1,4}\)?[\s\-]?\d{1,4}[\s\-]?\d{1,9}$",  # International
            r"^\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{4}$",  # US format
            r"^\+?\d{10,15}$",  # E.164 or plain digits
        ]

        for pattern in phone_patterns:
            if re.match(pattern, sample_str):
                has_country_code = sample_str.startswith("+")
                return {
                    "is_phone_number": True,
                    "country_code_present": has_country_code,
                    "confidence": 0.90,
                }

        return None

    @staticmethod
    def detect_currency(field_name: str, sample_values: List[Any]) -> Optional[Dict[str, Any]]:
        """Detect currency/monetary fields.

        Args:
            field_name: Field name for semantic hints.
            sample_values: Sample values to analyze.

        Returns:
            Detection result, or None if not a currency field.
        """
        import re

        # Check field name
        field_lower = field_name.lower()
        has_currency_name = any(
            keyword in field_lower
            for keyword in ["price", "cost", "amount", "amt", "total", "subtotal", "tax", "fee", "revenue", "salary"]
        )

        non_null = [v for v in sample_values if v is not None]
        if not non_null:
            return None

        sample = non_null[0]

        # Check if string with currency symbols
        if isinstance(sample, str):
            currency_pattern = r"^[\$€£¥₹]?\s?[\d,]+\.?\d*$"
            if re.match(currency_pattern, sample):
                return {
                    "is_currency": True,
                    "has_currency_symbols": "$" in sample or "€" in sample or "£" in sample,
                    "confidence": 0.92,
                }

        # Numeric value with currency-suggestive field name
        elif isinstance(sample, (int, float)) and has_currency_name:
            return {
                "is_currency": True,
                "has_currency_symbols": False,
                "confidence": 0.80,
            }

        return None

    @classmethod
    def analyze_field(
        cls,
        field_name: str,
        sample_values: List[Any],
        use_ai: bool = False,
    ) -> XDMField:
        """Analyze a field from sample values with optional AI enhancement.

        Args:
            field_name: Field name.
            sample_values: List of sample values.
            use_ai: Whether to use AI for ambiguous cases (async required).

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

        # Check for edge cases first
        # Boolean variants
        bool_detect = cls.detect_boolean_variant(non_null_values)
        if bool_detect and bool_detect["is_boolean_variant"]:
            field = XDMField(
                title=field_name.replace("_", " ").title(),
                description=f"Field: {field_name} (detected as {bool_detect['variant_type']})",
                type=XDMDataType.BOOLEAN,
            )
            # Add enum to show original values in description
            field.description += f" - Original values: {bool_detect['true_values']} (true), {bool_detect['false_values']} (false)"
            return field

        # Date format detection
        date_detect = cls.detect_date_format(field_name, non_null_values)
        if date_detect and date_detect["is_date_field"]:
            xdm_type = XDMDataType.DATE_TIME if date_detect["is_datetime"] else XDMDataType.DATE
            xdm_format = XDMFieldFormat.DATE_TIME if date_detect["is_datetime"] else XDMFieldFormat.DATE
            field = XDMField(
                title=field_name.replace("_", " ").title(),
                description=f"Field: {field_name} (detected format: {date_detect['detected_format']})",
                type=XDMDataType.STRING,
                format=xdm_format,
            )
            return field

        # Phone number detection
        phone_detect = cls.detect_phone_number(field_name, non_null_values)
        if phone_detect and phone_detect["is_phone_number"]:
            field = XDMField(
                title=field_name.replace("_", " ").title(),
                description=f"Field: {field_name} (phone number)",
                type=XDMDataType.STRING,
            )
            # Could add custom format or meta field for phone
            return field

        # Currency detection
        currency_detect = cls.detect_currency(field_name, non_null_values)
        if currency_detect and currency_detect["is_currency"]:
            field = XDMField(
                title=field_name.replace("_", " ").title(),
                description=f"Field: {field_name} (currency/monetary value)",
                type=XDMDataType.NUMBER,
            )
            numeric_values = []
            for v in non_null_values:
                if isinstance(v, (int, float)):
                    numeric_values.append(float(v))
                elif isinstance(v, str):
                    # Strip currency symbols and convert
                    import re
                    cleaned = re.sub(r"[^\d.]", "", v)
                    if cleaned:
                        try:
                            numeric_values.append(float(cleaned))
                        except ValueError:
                            pass
            if numeric_values:
                field.minimum = min(numeric_values)
                field.maximum = max(numeric_values)
            return field

        # Standard type inference
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
            # Check for mixed types
            item_types = set()
            for item in sample[:10]:  # Check first 10 items
                if item is not None:
                    item_types.add(type(item).__name__)
            
            if len(item_types) > 1:
                # Mixed array - use string as safe fallback
                field.items = XDMField(
                    title="Item",
                    description=f"Array item (mixed types detected: {', '.join(item_types)})",
                    type=XDMDataType.STRING,
                )
            else:
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
                field.properties[key] = cls.analyze_field(key, [value], use_ai=use_ai)

        # Detect numeric ranges
        if xdm_type in (XDMDataType.INTEGER, XDMDataType.NUMBER):
            numeric_values = [v for v in non_null_values if isinstance(v, (int, float))]
            if numeric_values:
                field.minimum = min(numeric_values)
                field.maximum = max(numeric_values)

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
