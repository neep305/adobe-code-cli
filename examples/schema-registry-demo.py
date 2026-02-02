"""Demo script for Schema Registry API features."""

import asyncio
import json
from adobe_experience.aep.client import AEPClient
from adobe_experience.core.config import get_config
from adobe_experience.schema.xdm import XDMSchemaRegistry


async def demo_schema_registry():
    """Demonstrate Schema Registry API capabilities."""
    
    config = get_config()
    
    async with AEPClient(config) as client:
        registry = XDMSchemaRegistry(client)
        
        print("=" * 60)
        print("Schema Registry API Demo")
        print("=" * 60)
        
        # 1. List Schemas
        print("\n1. Listing schemas...")
        schemas = await registry.list_schemas(limit=5)
        print(f"   Found {len(schemas.get('results', []))} schemas")
        for schema in schemas.get('results', [])[:3]:
            print(f"   - {schema.get('title', 'N/A')}")
        
        # 2. List Field Groups
        print("\n2. Listing field groups...")
        field_groups = await registry.list_field_groups(limit=5)
        print(f"   Found {len(field_groups.get('results', []))} field groups")
        for fg in field_groups.get('results', [])[:3]:
            print(f"   - {fg.get('title', 'N/A')}")
        
        # 3. List Descriptors
        print("\n3. Listing descriptors...")
        descriptors = await registry.list_descriptors(limit=5)
        print(f"   Found {len(descriptors.get('results', []))} descriptors")
        for desc in descriptors.get('results', [])[:3]:
            print(f"   - {desc.get('@type', 'N/A')}: {desc.get('xdm:sourceProperty', 'N/A')}")
        
        # 4. Create Identity Descriptor Example
        print("\n4. Example identity descriptor structure:")
        identity_descriptor = {
            "@type": "xdm:descriptorIdentity",
            "xdm:sourceSchema": "https://ns.adobe.com/{TENANT_ID}/schemas/customer_schema",
            "xdm:sourceVersion": 1,
            "xdm:sourceProperty": "/_{TENANT_ID}/email",
            "xdm:namespace": "Email",
            "xdm:property": "xdm:code",
            "xdm:isPrimary": True
        }
        print(json.dumps(identity_descriptor, indent=2))
        
        # 5. Create Field Group Example
        print("\n5. Example field group structure:")
        field_group = {
            "$id": "https://ns.adobe.com/{TENANT_ID}/mixins/custom_contact_info",
            "$schema": "http://json-schema.org/draft-06/schema#",
            "title": "Custom Contact Information",
            "description": "Custom fields for contact information",
            "type": "object",
            "meta:intendedToExtend": [
                "https://ns.adobe.com/xdm/context/profile"
            ],
            "definitions": {
                "customContactInfo": {
                    "properties": {
                        "_{TENANT_ID}": {
                            "type": "object",
                            "properties": {
                                "phone": {
                                    "title": "Phone Number",
                                    "type": "string"
                                },
                                "alternateEmail": {
                                    "title": "Alternate Email",
                                    "type": "string",
                                    "format": "email"
                                }
                            }
                        }
                    }
                }
            },
            "allOf": [
                {
                    "$ref": "#/definitions/customContactInfo"
                }
            ]
        }
        print(json.dumps(field_group, indent=2))
        
        print("\n" + "=" * 60)
        print("Demo completed!")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(demo_schema_registry())
