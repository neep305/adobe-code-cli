# Schema Generation Example

This example demonstrates how to generate XDM-compliant schemas from sample data using the aep Agent.

## Basic Schema Generation

```python
from adobe_aep.schema.xdm import XDMSchemaAnalyzer

# Sample data
sample_data = [
    {"name": "John", "email": "john@example.com", "age": 30},
    {"name": "Jane", "email": "jane@example.com", "age": 25},
]

# Generate schema
schema = XDMSchemaAnalyzer.from_sample_data(
    data=sample_data,
    schema_name="Customer Profile",
    schema_description="Basic customer information",
)

# Export as JSON
schema_json = schema.model_dump_json(by_alias=True, exclude_none=True, indent=2)
print(schema_json)
```

## Using CLI

```bash
# Generate schema from JSON file
aep schema create \
  --name "Customer Profile" \
  --from-sample customers.json \
  --description "Customer data schema"

# Use AI inference for enhanced generation
aep schema create \
  --name "Customer Events" \
  --from-sample events.json \
  --use-ai \
  --upload
```

## AI-Enhanced Generation

The AI engine analyzes your data and provides:

1. **Identity field recommendations** - Suggests which fields should be identity fields
2. **Data quality insights** - Identifies potential data issues
3. **XDM best practices** - Applies AEP-specific optimizations
4. **Namespace suggestions** - Recommends appropriate identity namespaces

```python
from adobe_aep.agent.inference import AIInferenceEngine, SchemaGenerationRequest

engine = AIInferenceEngine()

request = SchemaGenerationRequest(
    sample_data=sample_data,
    schema_name="Customer Profile",
    schema_description="Enhanced customer schema",
)

result = await engine.generate_schema_with_ai(request)

# Access AI insights
print(result.reasoning)
print(result.identity_recommendations)
print(result.data_quality_issues)
```

## Example Output

The generated schema will include:

- **Type inference**: Automatically detects string, number, boolean, object, array types
- **Format detection**: Recognizes email, URI, date, date-time formats
- **Enum detection**: Identifies fields with limited unique values
- **Nested structures**: Handles complex nested objects and arrays
- **XDM compliance**: Generates schemas that conform to Adobe XDM standards

## Next Steps

1. Review the generated schema
2. Customize identity fields if needed
3. Upload to AEP Schema Registry
4. Create datasets based on the schema
5. Begin data ingestion

See the main README for complete documentation.
