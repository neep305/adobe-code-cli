"""Data generation engine."""

import logging
import random
import time
from typing import Any, Dict, List, Optional, Set

from adobe_experience.core.config import AEPConfig
from adobe_experience.generators.faker_strategy import FakerFactory, FakerStrategy
from adobe_experience.generators.models import (
    DomainERD,
    EntityDefinition,
    FieldDefinition,
    GenerationConfig,
    GenerationResult,
)
from adobe_experience.schema.models import XDMDataType

logger = logging.getLogger(__name__)


class DataGenerationEngine:
    """Engine for generating test data from ERD definitions."""

    def __init__(self, config: Optional[AEPConfig] = None):
        """Initialize data generation engine.

        Args:
            config: Optional AEP configuration
        """
        self.config = config
        self.faker_factory = FakerFactory()
        self.generated_data: Dict[str, List[Dict[str, Any]]] = {}
        self._primary_key_counters: Dict[str, int] = {}

    async def generate_from_erd(
        self,
        erd: DomainERD,
        generation_config: GenerationConfig,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Generate test data from ERD definition.

        Args:
            erd: Domain ERD with entity definitions
            generation_config: Generation configuration

        Returns:
            Dictionary mapping entity names to list of generated records

        Examples:
            >>> engine = DataGenerationEngine()
            >>> erd = DomainERD(...)
            >>> config = GenerationConfig(record_count=100, locale="ko_KR")
            >>> data = await engine.generate_from_erd(erd, config)
            >>> print(data.keys())  # ['customers', 'orders', ...]
        """
        start_time = time.time()
        logger.info(f"Generating data for domain: {erd.domain}")

        # Set random seed for reproducibility
        if generation_config.seed is not None:
            random.seed(generation_config.seed)

        # Clear previous data
        self.generated_data = {}
        self._primary_key_counters = {}

        # Generate entities in specified order
        for entity_name in erd.generation_order:
            entity = erd.get_entity(entity_name)
            if not entity:
                logger.warning(f"Entity '{entity_name}' not found in ERD, skipping")
                continue

            logger.info(f"Generating data for entity: {entity_name}")
            records = await self._generate_entity_records(entity, generation_config)
            self.generated_data[entity_name.lower()] = records

        generation_time = time.time() - start_time
        logger.info(
            f"Generated {sum(len(r) for r in self.generated_data.values())} total records in {generation_time:.2f}s"
        )

        return self.generated_data

    async def _generate_entity_records(
        self,
        entity: EntityDefinition,
        config: GenerationConfig,
    ) -> List[Dict[str, Any]]:
        """Generate records for a single entity.

        Args:
            entity: Entity definition
            config: Generation configuration

        Returns:
            List of generated records
        """
        record_count = config.record_count or entity.estimated_record_count
        records = []

        for i in range(record_count):
            record = {}

            # Generate each field
            for field in entity.fields:
                value = self._generate_field_value(
                    field,
                    entity=entity,
                    record_index=i,
                    config=config,
                )
                record[field.name] = value

            # Handle relationships (foreign keys)
            if config.preserve_relationships:
                for relationship in entity.relationships:
                    if relationship.from_entity == entity.name:
                        # This entity has a FK to another entity
                        fk_value = self._get_random_parent_key(
                            relationship.to_entity,
                            relationship.reference_field,
                        )
                        if fk_value is not None:
                            record[relationship.foreign_key] = fk_value

            records.append(record)

        return records

    def _generate_field_value(
        self,
        field: FieldDefinition,
        entity: EntityDefinition,
        record_index: int,
        config: GenerationConfig,
    ) -> Any:
        """Generate value for a single field.

        Args:
            field: Field definition
            entity: Parent entity
            record_index: Current record index
            config: Generation configuration

        Returns:
            Generated value
        """
        # Check for NULL values
        if config.include_null_values and field.constraints.nullable:
            if random.random() < field.constraints.null_probability:
                return None

        # Primary key: Sequential with entity prefix
        if field.name == entity.primary_key:
            counter = self._primary_key_counters.get(entity.name, 0)
            self._primary_key_counters[entity.name] = counter + 1
            prefix = entity.name.upper()[:4]
            return f"{prefix}{counter:06d}"

        # Enum values: Random choice
        if field.enum_values:
            return random.choice(field.enum_values)

        # Default value
        if field.default_value is not None:
            return field.default_value

        # Use Faker strategy
        if field.faker_provider:
            return self.faker_factory.generate_value(
                field.faker_provider,
                locale=config.locale,
                xdm_type=field.xdm_type,
            )

        # Infer Faker provider from field name/type
        inferred_provider = FakerStrategy.infer_faker_provider(
            field.name,
            field.xdm_type,
            field.format,
        )

        value = self.faker_factory.generate_value(
            inferred_provider,
            locale=config.locale,
            xdm_type=field.xdm_type,
        )

        # Apply constraints
        value = self._apply_constraints(value, field)

        return value

    def _apply_constraints(self, value: Any, field: FieldDefinition) -> Any:
        """Apply field constraints to generated value.

        Args:
            value: Generated value
            field: Field definition with constraints

        Returns:
            Constrained value
        """
        constraints = field.constraints

        # Numeric constraints
        if isinstance(value, (int, float)):
            if constraints.min_value is not None:
                value = max(value, constraints.min_value)
            if constraints.max_value is not None:
                value = min(value, constraints.max_value)

        # String constraints
        if isinstance(value, str):
            if constraints.min_length is not None:
                while len(value) < constraints.min_length:
                    value += " " + self.faker_factory.get_faker().word()
            if constraints.max_length is not None:
                value = value[: constraints.max_length]

        return value

    def _get_random_parent_key(
        self,
        parent_entity: str,
        reference_field: str = "id",
    ) -> Optional[Any]:
        """Get random primary key from parent entity for FK relationship.

        Args:
            parent_entity: Parent entity name
            reference_field: Field to reference (default: "id")

        Returns:
            Random key value or None if parent not generated yet
        """
        parent_data = self.generated_data.get(parent_entity.lower())
        if not parent_data:
            logger.warning(
                f"Parent entity '{parent_entity}' not generated yet, cannot create FK"
            )
            return None

        if not parent_data:
            return None

        # Get random record and extract reference field
        random_record = random.choice(parent_data)
        return random_record.get(reference_field)

    def _compute_generation_order(self, erd: DomainERD) -> List[str]:
        """Compute entity generation order using topological sort.

        Ensures entities without dependencies are generated first.

        Args:
            erd: Domain ERD

        Returns:
            Ordered list of entity names
        """
        # If explicitly specified, use that order
        if erd.generation_order:
            return erd.generation_order

        # Build dependency graph
        dependencies: Dict[str, Set[str]] = {}
        for entity in erd.entities:
            dependencies[entity.name] = set()
            for relationship in entity.relationships:
                if relationship.from_entity == entity.name:
                    # This entity depends on the target entity
                    dependencies[entity.name].add(relationship.to_entity)

        # Topological sort
        ordered = []
        visited = set()

        def visit(entity_name: str):
            if entity_name in visited:
                return
            visited.add(entity_name)
            for dependency in dependencies.get(entity_name, []):
                visit(dependency)
            ordered.append(entity_name)

        for entity in erd.entities:
            visit(entity.name)

        logger.info(f"Computed generation order: {ordered}")
        return ordered
