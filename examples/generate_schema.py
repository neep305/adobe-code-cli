"""Example: Generate XDM schema from sample data."""

import json

from adobe_experience.schema.xdm import XDMSchemaAnalyzer

# Sample customer data
sample_data = [
    {
        "customer_id": "CUST001",
        "email": "john.doe@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "age": 35,
        "status": "active",
        "total_purchases": 12,
        "lifetime_value": 1250.50,
        "registration_date": "2024-01-15T10:30:00Z",
        "preferences": {
            "newsletter": True,
            "notifications": False,
            "language": "en",
        },
        "tags": ["premium", "loyal", "frequent_buyer"],
    },
    {
        "customer_id": "CUST002",
        "email": "jane.smith@example.com",
        "first_name": "Jane",
        "last_name": "Smith",
        "age": 28,
        "status": "active",
        "total_purchases": 3,
        "lifetime_value": 450.00,
        "registration_date": "2024-02-20T14:45:00Z",
        "preferences": {
            "newsletter": False,
            "notifications": True,
            "language": "en",
        },
        "tags": ["new", "mobile_user"],
    },
]

# Generate XDM schema
schema = XDMSchemaAnalyzer.from_sample_data(
    data=sample_data,
    schema_name="Customer Profile Schema",
    schema_description="XDM schema for customer profile data with preferences and behavior tracking",
)

# Print schema as JSON
schema_json = schema.model_dump_json(by_alias=True, exclude_none=True, indent=2)
print(schema_json)

# Save to file
with open("customer_profile_schema.json", "w", encoding="utf-8") as f:
    f.write(schema_json)

print("\n✓ Schema generated and saved to customer_profile_schema.json")
