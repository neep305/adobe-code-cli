"""Domain analyzer using AI to generate ERDs."""

import json
import logging
from typing import Optional

from adobe_experience.agent.inference import AIInferenceEngine
from adobe_experience.generators.models import DomainERD
from adobe_experience.schema.models import XDMDataType, XDMFieldFormat

logger = logging.getLogger(__name__)


class DomainAnalyzer:
    """Analyze domain descriptions and generate ERDs using AI."""

    def __init__(self, ai_engine: AIInferenceEngine):
        """Initialize domain analyzer.

        Args:
            ai_engine: AI inference engine instance
        """
        self.ai_engine = ai_engine

    async def generate_erd_from_domain(
        self,
        domain: str,
        additional_context: Optional[str] = None,
        entity_count: int = 5,
    ) -> DomainERD:
        """Generate ERD from domain description using AI.

        Args:
            domain: Domain name or description (e.g., "ecommerce", "healthcare")
            additional_context: Additional context or requirements
            entity_count: Suggested number of entities (3-7)

        Returns:
            DomainERD with entities, relationships, and field definitions

        Examples:
            >>> analyzer = DomainAnalyzer(ai_engine)
            >>> erd = await analyzer.generate_erd_from_domain("ecommerce")
            >>> print(erd.entities)  # [Customer, Product, Order, ...]
        """
        logger.info(f"Generating ERD for domain: {domain}")

        system_prompt = """You are an expert data architect specializing in:
- Entity-Relationship Diagram (ERD) design
- Adobe Experience Platform (AEP) XDM schemas
- Database normalization and relational design
- Test data generation strategies

Your task is to design a comprehensive data model for a given domain."""

        user_prompt = f"""Design a complete data model (ERD) for the following domain:

Domain: {domain}
Additional Context: {additional_context or "Standard business application"}
Target Entity Count: {entity_count} core entities

Requirements:
1. Identify {entity_count} core entities that represent the domain
2. For each entity:
   - Define 5-15 fields with appropriate data types
   - Specify primary key (typically "id" or "{domain}_id")
   - Include common fields: created_at, updated_at, status
   - Use realistic field names following snake_case convention
   
3. Define relationships between entities:
   - Identify foreign keys
   - Specify relationship type (1:1, 1:N, N:M)
   - Maintain referential integrity
   
4. For each field, suggest:
   - XDM data type: {list(XDMDataType)}
   - Optional format: {list(XDMFieldFormat)}
   - Faker provider for realistic data (e.g., "name", "email", "phone_number")
   - Enum values if applicable
   - Constraints (min/max, nullable, unique)
   
5. Specify generation order (topological sort based on FK dependencies)
6. Recommend record counts for balanced test data

Return a JSON object matching this schema:
{{
  "domain": "string",
  "description": "string",
  "entities": [
    {{
      "name": "string",
      "description": "string",
      "primary_key": "string",
      "estimated_record_count": number,
      "fields": [
        {{
          "name": "string",
          "description": "string",
          "xdm_type": "string|number|integer|boolean|object|array|date|date-time",
          "format": "email|uri|date|date-time|uuid",
          "faker_provider": "string (e.g., 'name', 'email', 'company')",
          "enum_values": ["value1", "value2"],
          "constraints": {{
            "min_value": number,
            "max_value": number,
            "unique": boolean,
            "nullable": boolean
          }}
        }}
      ],
      "relationships": [
        {{
          "from_entity": "string",
          "to_entity": "string",
          "type": "1:1|1:N|N:1|N:M",
          "foreign_key": "string",
          "reference_field": "string",
          "cardinality": "string"
        }}
      ]
    }}
  ],
  "generation_order": ["Entity1", "Entity2", ...]
}}

Design a realistic, well-normalized data model suitable for test data generation."""

        try:
            # Check if any AI client is available
            if not self.ai_engine.active_client:
                raise ValueError(
                    "No AI provider configured. "
                    "Run 'aep init' or set ANTHROPIC_API_KEY or OPENAI_API_KEY environment variable."
                )

            # Use Anthropic with tool calling (structured output)
            if self.ai_engine.active_client == "anthropic" and self.ai_engine.anthropic:
                # Define tool for structured output
                tools = [{
                    "name": "generate_domain_erd",
                    "description": "Generate ERD (Entity-Relationship Diagram) for a domain with entities, fields, and relationships",
                    "input_schema": DomainERD.model_json_schema()
                }]

                # Call Anthropic API with tool calling
                response = self.ai_engine.anthropic.messages.create(
                    model=self.ai_engine.config.ai_model,
                    max_tokens=8192,
                    system=system_prompt,
                    messages=[
                        {
                            "role": "user",
                            "content": user_prompt,
                        }
                    ],
                    tools=tools,
                    tool_choice={"type": "tool", "name": "generate_domain_erd"}
                )

                # Extract tool use from response
                tool_use = None
                for block in response.content:
                    if block.type == "tool_use" and block.name == "generate_domain_erd":
                        tool_use = block
                        break

                if not tool_use:
                    raise ValueError("AI did not return structured ERD data")

                # Parse response
                erd_data = tool_use.input
                erd = DomainERD.model_validate(erd_data)

            # Use OpenAI with function calling (structured output)
            elif self.ai_engine.active_client == "openai" and self.ai_engine.openai:
                # Define function for structured output
                functions = [{
                    "name": "generate_domain_erd",
                    "description": "Generate ERD (Entity-Relationship Diagram) for a domain with entities, fields, and relationships",
                    "parameters": DomainERD.model_json_schema()
                }]

                # Call OpenAI API with function calling
                response = self.ai_engine.openai.chat.completions.create(
                    model=self.ai_engine.config.ai_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    functions=functions,
                    function_call={"name": "generate_domain_erd"}
                )

                # Parse function call response
                function_call = response.choices[0].message.function_call
                if not function_call:
                    raise ValueError("OpenAI did not return function call data")

                erd_data = json.loads(function_call.arguments)
                erd = DomainERD.model_validate(erd_data)

            else:
                raise ValueError(f"AI client '{self.ai_engine.active_client}' not properly initialized")

            logger.info(
                f"Generated ERD with {len(erd.entities)} entities: {[e.name for e in erd.entities]}"
            )

            return erd

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            # Fallback to simple ERD
            return self._create_fallback_erd(domain)

        except Exception as e:
            logger.error(f"Error generating ERD: {e}")
            raise

    def _create_fallback_erd(self, domain: str) -> DomainERD:
        """Create a simple fallback ERD if AI fails.

        Args:
            domain: Domain name

        Returns:
            Simple ERD with basic entities
        """
        logger.warning(f"Using fallback ERD for domain: {domain}")

        # Create simple entity structure
        from adobe_experience.generators.models import EntityDefinition, FieldDefinition

        base_entity = EntityDefinition(
            name=domain.title(),
            description=f"Main {domain} entity",
            primary_key="id",
            estimated_record_count=10,
            fields=[
                FieldDefinition(
                    name="id",
                    description="Primary key",
                    xdm_type=XDMDataType.STRING,
                    generation_strategy="sequential",
                    constraints={"unique": True, "nullable": False},
                ),
                FieldDefinition(
                    name="name",
                    description="Name",
                    xdm_type=XDMDataType.STRING,
                    faker_provider="name",
                ),
                FieldDefinition(
                    name="created_at",
                    description="Creation timestamp",
                    xdm_type=XDMDataType.STRING,
                    format=XDMFieldFormat.DATE_TIME,
                    faker_provider="date_time_between:start_date=-1y",
                ),
            ],
        )

        return DomainERD(
            domain=domain,
            description=f"Fallback ERD for {domain}",
            entities=[base_entity],
            generation_order=[base_entity.name],
        )
