"""Mermaid ERD diagram parser for XDM schema generation."""

import re
from typing import Dict, List, Optional, Tuple

from adobe_experience.generators.models import (
    EntityDefinition,
    FieldConstraints,
    FieldDefinition,
    Relationship,
    RelationType,
)
from adobe_experience.schema.models import (
    XDMDataType,
    XDMField,
    XDMFieldFormat,
    XDMFieldGroup,
    XDMSchema,
    XDMSchemaRef,
)


class MermaidERDParser:
    """Parse Mermaid ERD diagrams to entity and schema definitions."""

    # Mermaid type to XDM type mapping
    TYPE_MAPPING = {
        "string": XDMDataType.STRING,
        "number": XDMDataType.NUMBER,
        "integer": XDMDataType.INTEGER,
        "boolean": XDMDataType.BOOLEAN,
        "object": XDMDataType.OBJECT,
        "array": XDMDataType.ARRAY,
        "date": XDMDataType.STRING,  # Will set format to date
        "datetime": XDMDataType.STRING,  # Will set format to date-time
    }

    # Relationship cardinality mapping
    RELATIONSHIP_MAPPING = {
        "}o--||": RelationType.MANY_TO_ONE,  # Many to one
        "||--o{": RelationType.ONE_TO_MANY,  # One to many
        "}o--o{": RelationType.MANY_TO_MANY,  # Many to many
        "||--||": RelationType.ONE_TO_ONE,  # One to one
    }

    def parse_erd(self, erd_content: str) -> List[EntityDefinition]:
        """Parse Mermaid ERD diagram to entity definitions.

        Args:
            erd_content: Mermaid erDiagram content

        Returns:
            List of entity definitions

        Examples:
            >>> parser = MermaidERDParser()
            >>> entities = parser.parse_erd(erd_text)
            >>> print(entities[0].name)  # "CUSTOMERS"
        """
        entities = []
        relationships = []

        # Extract entity blocks
        # Pattern: ENTITY_NAME { field definitions }
        entity_pattern = r"(\w+)\s*\{([^}]+)\}"
        entity_matches = re.finditer(entity_pattern, erd_content, re.MULTILINE)

        for match in entity_matches:
            entity_name = match.group(1).strip()
            fields_block = match.group(2).strip()

            # Parse fields
            fields = self._parse_fields(fields_block)

            # Determine primary key
            primary_key = next(
                (f.name for f in fields if "PK" in fields_block and f.name in fields_block),
                fields[0].name if fields else "id",
            )

            entity = EntityDefinition(
                name=entity_name.lower(),
                description=f"{entity_name.title()} entity from ERD",
                primary_key=primary_key,
                fields=fields,
                relationships=[],  # Will be populated later
                estimated_record_count=100,
            )
            entities.append(entity)

        # Extract relationships
        # Pattern: ENTITY1 }o--|| ENTITY2 : "relationship_name"
        relationship_pattern = r'(\w+)\s+([\}\|\]o\-\{]+)\s+(\w+)\s*:\s*"([^"]+)"'
        rel_matches = re.finditer(relationship_pattern, erd_content)

        for match in rel_matches:
            from_entity = match.group(1).strip().lower()
            cardinality = match.group(2).strip()
            to_entity = match.group(3).strip().lower()
            rel_name = match.group(4).strip()

            # Determine relationship type
            rel_type = self._parse_relationship_type(cardinality)

            # Find FK field (usually named {to_entity}_id)
            fk_field = f"{to_entity}_id"

            relationship = Relationship(
                from_entity=from_entity,
                to_entity=to_entity,
                type=rel_type,
                foreign_key=fk_field,
                reference_field=self._find_primary_key(entities, to_entity),
                cardinality=cardinality,  # Store original Mermaid notation
                description=rel_name,
            )
            relationships.append(relationship)

        # Assign relationships to entities
        for entity in entities:
            entity.relationships = [
                r for r in relationships if r.from_entity == entity.name
            ]

        return entities

    def _parse_fields(self, fields_block: str) -> List[FieldDefinition]:
        """Parse field definitions from entity block.

        Args:
            fields_block: Field definitions text

        Returns:
            List of field definitions
        """
        fields = []
        # Pattern: type field_name [PK|FK]
        field_pattern = r"(\w+)\s+(\w+)(?:\s+(PK|FK))?"

        for line in fields_block.split("\n"):
            line = line.strip()
            if not line:
                continue

            match = re.match(field_pattern, line)
            if match:
                field_type = match.group(1).lower()
                field_name = match.group(2)
                modifier = match.group(3)  # PK or FK

                xdm_type = self.TYPE_MAPPING.get(field_type, XDMDataType.STRING)
                xdm_format = self._infer_format(field_type, field_name)

                # Detect if it's a FK
                is_foreign_key = modifier == "FK" or field_name.endswith("_id")

                field = FieldDefinition(
                    name=field_name,
                    xdm_type=xdm_type,
                    format=xdm_format,
                    description=f"{field_name.replace('_', ' ').title()}",
                    constraints=FieldConstraints(
                        nullable=modifier != "PK",  # PK cannot be null
                        unique=modifier == "PK",  # PK must be unique
                    ),
                )
                fields.append(field)

        return fields

    def _infer_format(
        self, field_type: str, field_name: str
    ) -> Optional[XDMFieldFormat]:
        """Infer XDM field format from type and name.

        Args:
            field_type: Mermaid field type
            field_name: Field name

        Returns:
            XDM field format or None
        """
        field_lower = field_name.lower()

        # Date/time detection
        if field_type in ["date", "datetime"]:
            return XDMFieldFormat.DATE_TIME if field_type == "datetime" else XDMFieldFormat.DATE

        if any(keyword in field_lower for keyword in ["timestamp", "created", "updated", "date"]):
            return XDMFieldFormat.DATE_TIME

        # Email detection
        if "email" in field_lower:
            return XDMFieldFormat.EMAIL

        # URI detection
        if any(keyword in field_lower for keyword in ["url", "uri", "link"]):
            return XDMFieldFormat.URI

        # UUID detection
        if "uuid" in field_lower or "guid" in field_lower:
            return XDMFieldFormat.UUID

        return None

    def _parse_relationship_type(self, cardinality: str) -> RelationType:
        """Parse Mermaid relationship cardinality to RelationType.

        Args:
            cardinality: Mermaid cardinality notation

        Returns:
            Relationship type
        """
        for pattern, rel_type in self.RELATIONSHIP_MAPPING.items():
            if pattern in cardinality:
                return rel_type

        # Default to many-to-one if uncertain
        return RelationType.MANY_TO_ONE

    def _find_primary_key(
        self, entities: List[EntityDefinition], entity_name: str
    ) -> str:
        """Find primary key field for an entity.

        Args:
            entities: List of entities
            entity_name: Entity name to find

        Returns:
            Primary key field name
        """
        entity = next((e for e in entities if e.name == entity_name), None)
        return entity.primary_key if entity else "id"

    def entity_to_xdm_schema(
        self,
        entity: EntityDefinition,
        tenant_id: str,
        xdm_class: str = "https://ns.adobe.com/xdm/context/profile",
    ) -> XDMSchema:
        """Convert ERD entity to XDM schema.

        Args:
            entity: Entity definition from ERD
            tenant_id: AEP tenant ID
            xdm_class: XDM class to use

        Returns:
            XDM schema definition

        Examples:
            >>> parser = MermaidERDParser()
            >>> schema = parser.entity_to_xdm_schema(entity, "tenant123")
            >>> print(schema.title)  # "Products Schema"
        """
        # Convert fields to XDM fields (as Dict[str, XDMField])
        xdm_properties = {}
        for field in entity.fields:
            xdm_field = XDMField(
                title=field.name.replace("_", " ").title(),
                type=field.xdm_type,
                format=field.format,
                description=field.description,
            )
            xdm_properties[field.name] = xdm_field

        # Generate schema ID
        schema_id = f"https://ns.adobe.com/{tenant_id}/schemas/{entity.name}_schema"

        # Nest custom fields under tenant namespace (AEP requirement)
        properties = {
            f"_{tenant_id}": XDMField(
                title=f"{entity.name.title()} Custom Fields",
                description="Custom tenant-specific fields from ERD",
                type=XDMDataType.OBJECT,
                properties=xdm_properties,
            )
        }

        # Create schema with proper AEP structure
        schema = XDMSchema(
            schema_id=schema_id,
            title=f"{entity.name.title()} Schema",
            description=entity.description or f"Schema for {entity.name} entity",
            type=XDMDataType.OBJECT,
            version="1.0",
            meta_class=xdm_class,
            properties=properties,
            # allOf must contain base class reference (AEP requirement)
            all_of=[
                XDMSchemaRef(ref=xdm_class),
            ],
            # meta:extends should list extended classes (recommended)
            meta_extends=[xdm_class],
        )

        return schema

    def entity_to_field_group(
        self,
        entity: EntityDefinition,
        tenant_id: str,
        xdm_class: str = "https://ns.adobe.com/xdm/context/profile",
    ) -> XDMFieldGroup:
        """Convert ERD entity to XDM field group.

        Args:
            entity: Entity definition from ERD
            tenant_id: AEP tenant ID
            xdm_class: XDM class this field group is compatible with

        Returns:
            XDM field group definition

        Examples:
            >>> parser = MermaidERDParser()
            >>> fieldgroup = parser.entity_to_field_group(entity, "tenant123")
            >>> print(fieldgroup.title)  # "Orders Field Group"
        """
        # Convert fields to XDM field structure
        xdm_properties = {}
        for field in entity.fields:
            # Object types without nested properties should be strings (JSON strings)
            field_type = field.xdm_type.value
            if field.xdm_type == XDMDataType.OBJECT:
                field_type = "string"  # Treat as JSON string
            
            field_def = {
                "title": field.name.replace("_", " ").title(),
                "type": field_type,
                "description": field.description or field.name.replace("_", " ").title(),
            }
            if field.format:
                field_def["format"] = field.format.value
            
            # Array types must have items
            if field.xdm_type == XDMDataType.ARRAY:
                field_def["items"] = {"type": "string"}  # Default to string items
            
            xdm_properties[field.name] = field_def

        # Generate field group ID
        field_group_id = f"https://ns.adobe.com/{tenant_id}/fieldgroups/{entity.name}_fieldgroup"

        # Create definitions structure (custom fields under _{TENANT_ID})
        definitions = {
            "customFields": {
                "properties": {
                    f"_{tenant_id}": {
                        "type": "object",
                        "properties": xdm_properties,
                    }
                }
            }
        }

        # Create field group
        field_group = XDMFieldGroup(
            field_group_id=field_group_id,
            title=f"{entity.name.title()} Field Group",
            description=entity.description or f"Custom fields for {entity.name} from ERD",
            type=XDMDataType.OBJECT,
            meta_intended_to_extend=[xdm_class],
            definitions=definitions,
            all_of=[
                XDMSchemaRef(ref="#/definitions/customFields"),
            ],
        )

        return field_group

    def entity_to_xdm_schema_with_fieldgroup(
        self,
        entity: EntityDefinition,
        tenant_id: str,
        field_group_id: str,
        xdm_class: str = "https://ns.adobe.com/xdm/context/profile",
    ) -> XDMSchema:
        """Convert ERD entity to XDM schema using a field group reference.

        Args:
            entity: Entity definition from ERD
            tenant_id: AEP tenant ID
            field_group_id: Field group $id to reference
            xdm_class: XDM class to use

        Returns:
            XDM schema definition

        Examples:
            >>> parser = MermaidERDParser()
            >>> schema = parser.entity_to_xdm_schema_with_fieldgroup(
            ...     entity, "tenant123", "https://ns.adobe.com/tenant123/fieldgroups/orders_fieldgroup"
            ... )
            >>> print(schema.title)  # "Orders Schema"
        """
        # Generate schema ID
        schema_id = f"https://ns.adobe.com/{tenant_id}/schemas/{entity.name}_schema"

        # Create schema with references only (no direct properties)
        schema = XDMSchema(
            schema_id=schema_id,
            title=f"{entity.name.title()} Schema",
            description=entity.description or f"Schema for {entity.name} entity",
            type=XDMDataType.OBJECT,
            version="1.0",
            meta_class=xdm_class,
            # allOf contains class + field group references (AEP requirement)
            all_of=[
                XDMSchemaRef(ref=xdm_class),
                XDMSchemaRef(ref=field_group_id),
            ],
            # meta:extends lists all extended schemas
            meta_extends=[xdm_class],
        )

        return schema


def parse_erd_file(file_path: str) -> List[EntityDefinition]:
    """Parse Mermaid ERD file to entity definitions.

    Args:
        file_path: Path to Mermaid ERD file

    Returns:
        List of entity definitions
    """
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    parser = MermaidERDParser()
    return parser.parse_erd(content)
