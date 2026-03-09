"""Convert ERD definitions to XDM schemas."""

import logging
from typing import Dict

from adobe_experience.generators.models import DomainERD, EntityDefinition
from adobe_experience.schema.models import (
    XDMDataType,
    XDMField,
    XDMSchema,
    XDMSchemaRef,
)

logger = logging.getLogger(__name__)


class ERDToSchemaConverter:
    """Convert DomainERD to XDM schemas."""

    def __init__(self, tenant_id: str):
        """Initialize converter.

        Args:
            tenant_id: AEP tenant ID
        """
        self.tenant_id = tenant_id

    async def generate_schemas_from_erd(
        self,
        erd: DomainERD,
    ) -> Dict[str, XDMSchema]:
        """Generate XDM schemas from ERD.

        Args:
            erd: Domain ERD

        Returns:
            Dictionary mapping entity names to XDM schemas

        Examples:
            >>> converter = ERDToSchemaConverter("mytenant")
            >>> erd = DomainERD(...)
            >>> schemas = await converter.generate_schemas_from_erd(erd)
            >>> print(schemas.keys())  # ['Customer', 'Order', ...]
        """
        logger.info(f"Generating XDM schemas for domain: {erd.domain}")

        schemas = {}
        for entity in erd.entities:
            schema = self._entity_to_xdm_schema(entity)
            schemas[entity.name] = schema

        logger.info(f"Generated {len(schemas)} XDM schemas")
        return schemas

    def _entity_to_xdm_schema(self, entity: EntityDefinition) -> XDMSchema:
        """Convert EntityDefinition to XDMSchema.

        Args:
            entity: Entity definition

        Returns:
            XDM schema
        """
        # Convert fields
        properties = {}
        for field_def in entity.fields:
            xdm_field = XDMField(
                title=field_def.name.replace("_", " ").title(),
                description=field_def.description or f"Field: {field_def.name}",
                type=field_def.xdm_type,
                format=field_def.format,
                enum=field_def.enum_values,
                minimum=field_def.constraints.min_value,
                maximum=field_def.constraints.max_value,
            )
            properties[field_def.name] = xdm_field

        # Infer XDM class
        xdm_class = self._infer_xdm_class(entity)

        # Generate schema ID
        schema_id = (
            f"https://ns.adobe.com/{self.tenant_id}/schemas/{entity.name.lower()}_schema"
        )

        schema = XDMSchema(
            schema_id=schema_id,
            title=f"{entity.name} Schema",
            description=entity.description,
            type=XDMDataType.OBJECT,
            properties=properties,
            meta_class=xdm_class,
            all_of=[XDMSchemaRef(ref=xdm_class)],
        )

        return schema

    def _infer_xdm_class(self, entity: EntityDefinition) -> str:
        """Infer XDM class from entity name and fields.

        Args:
            entity: Entity definition

        Returns:
            XDM class URI
        """
        entity_lower = entity.name.lower()
        field_names = {f.name.lower() for f in entity.fields}

        # Profile class indicators
        profile_indicators = {
            "customer",
            "user",
            "person",
            "profile",
            "contact",
            "member",
            "account",
        }
        profile_fields = {"email", "first_name", "last_name", "phone", "address"}

        # Experience Event indicators
        event_indicators = {
            "event",
            "activity",
            "interaction",
            "action",
            "transaction",
            "click",
            "view",
        }
        event_fields = {"timestamp", "event_type", "event_id"}

        # Check entity name
        if any(indicator in entity_lower for indicator in profile_indicators):
            return "https://ns.adobe.com/xdm/context/profile"

        if any(indicator in entity_lower for indicator in event_indicators):
            return "https://ns.adobe.com/xdm/context/experienceevent"

        # Check field patterns
        if field_names.intersection(profile_fields):
            return "https://ns.adobe.com/xdm/context/profile"

        if field_names.intersection(event_fields):
            return "https://ns.adobe.com/xdm/context/experienceevent"

        # Default to custom class (will be treated as Profile)
        logger.warning(
            f"Could not determine XDM class for '{entity.name}', defaulting to Profile"
        )
        return "https://ns.adobe.com/xdm/context/profile"
