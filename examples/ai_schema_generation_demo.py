"""Demo: AI-Powered Schema Generation with Structured Output

This demo shows the enhanced AI schema generation using Anthropic tool calling
for structured, reliable output with confidence scores and detailed recommendations.
"""

import asyncio
import json
from pathlib import Path

from adobe_experience.agent.inference import (
    AIInferenceEngine,
    SchemaGenerationRequest,
)
from adobe_experience.core.config import get_config


async def demo_b2c_customer_profile():
    """Demo: B2C Customer Profile schema generation."""
    print("\n" + "=" * 80)
    print("Demo 1: B2C Customer Profile (Email-Based Identity)")
    print("=" * 80)
    
    # Sample B2C customer data
    sample_data = [
        {
            "email": "john.doe@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "age": 35,
            "loyalty_tier": "gold",
            "signup_date": "2023-01-15",
            "total_purchases": 1250.50,
            "city": "San Francisco",
            "state": "CA",
        },
        {
            "email": "jane.smith@example.com",
            "first_name": "Jane",
            "last_name": "Smith",
            "age": 28,
            "loyalty_tier": "silver",
            "signup_date": "2023-03-22",
            "total_purchases": 850.00,
            "city": "New York",
            "state": "NY",
        },
        {
            "email": "bob.wilson@example.com",
            "first_name": "Bob",
            "last_name": "Wilson",
            "age": 42,
            "loyalty_tier": "platinum",
            "signup_date": "2022-11-10",
            "total_purchases": 3500.75,
            "city": "Boston",
            "state": "MA",
        },
    ]
    
    print(f"\nSample Data: {len(sample_data)} records")
    print(json.dumps(sample_data[0], indent=2))
    
    # Generate schema with AI
    engine = AIInferenceEngine()
    
    request = SchemaGenerationRequest(
        sample_data=sample_data,
        schema_name="Customer Profile",
        schema_description="B2C customer profile with loyalty program data",
        class_id="https://ns.adobe.com/xdm/context/profile",
    )
    
    print("\n🤖 Generating schema with AI (using structured output)...")
    result = await engine.generate_schema_with_ai(request)
    
    print("\n✅ Schema Generated Successfully!")
    print(f"\nTitle: {result.xdm_schema.title}")
    print(f"Class: {result.xdm_schema.meta_class}")
    print(f"\n📊 AI Reasoning:\n{result.reasoning}")
    
    print(f"\n🔑 Identity Recommendations:")
    for field, reason in result.identity_recommendations.items():
        print(f"  - {field}: {reason}")
    
    if result.data_quality_issues:
        print(f"\n⚠️  Data Quality Issues:")
        for issue in result.data_quality_issues:
            print(f"  - {issue}")
    
    # Show field count
    if result.xdm_schema.properties:
        print(f"\n📋 Generated {len(result.xdm_schema.properties)} fields")
    
    return result


async def demo_ecommerce_event():
    """Demo: E-commerce Purchase Event schema generation."""
    print("\n" + "=" * 80)
    print("Demo 2: E-commerce Purchase Event (ExperienceEvent)")
    print("=" * 80)
    
    # Sample e-commerce event data
    sample_data = [
        {
            "event_id": "evt_001",
            "timestamp": "2024-01-15T10:30:00Z",
            "event_type": "purchase",
            "user_email": "user@example.com",
            "product_id": "SKU-123",
            "product_name": "Wireless Headphones",
            "price": 99.99,
            "quantity": 1,
            "currency": "USD",
            "payment_method": "credit_card",
        },
        {
            "event_id": "evt_002",
            "timestamp": "2024-01-15T11:15:00Z",
            "event_type": "add_to_cart",
            "user_email": "user2@example.com",
            "product_id": "SKU-456",
            "product_name": "Smart Watch",
            "price": 299.99,
            "quantity": 1,
            "currency": "USD",
        },
        {
            "event_id": "evt_003",
            "timestamp": "2024-01-15T12:00:00Z",
            "event_type": "purchase",
            "user_email": "user3@example.com",
            "product_id": "SKU-789",
            "product_name": "Laptop Stand",
            "price": 49.95,
            "quantity": 2,
            "currency": "USD",
            "payment_method": "paypal",
        },
    ]
    
    print(f"\nSample Data: {len(sample_data)} records")
    print(json.dumps(sample_data[0], indent=2))
    
    # Generate schema with AI
    engine = AIInferenceEngine()
    
    request = SchemaGenerationRequest(
        sample_data=sample_data,
        schema_name="Purchase Events",
        schema_description="E-commerce purchase and cart events",
        class_id="https://ns.adobe.com/xdm/context/experienceevent",
    )
    
    print("\n🤖 Generating schema with AI...")
    result = await engine.generate_schema_with_ai(request)
    
    print("\n✅ Schema Generated Successfully!")
    print(f"\nTitle: {result.xdm_schema.title}")
    print(f"Class: {result.xdm_schema.meta_class}")
    print(f"\n📊 AI Reasoning:\n{result.reasoning}")
    
    print(f"\n🔑 Identity Recommendations:")
    for field, reason in result.identity_recommendations.items():
        print(f"  - {field}: {reason}")
    
    if result.data_quality_issues:
        print(f"\n⚠️  Data Quality Issues:")
        for issue in result.data_quality_issues:
            print(f"  - {issue}")
    
    return result


async def demo_from_test_data():
    """Demo: Generate schema from test data files."""
    print("\n" + "=" * 80)
    print("Demo 3: Generate Schema from test-data/ecommerce/customers.json")
    print("=" * 80)
    
    # Load test data
    test_file = Path("test-data/ecommerce/customers.json")
    if not test_file.exists():
        print(f"⚠️  Test file not found: {test_file}")
        print("Skipping this demo.")
        return
    
    with open(test_file) as f:
        sample_data = json.load(f)
    
    print(f"\nLoaded {len(sample_data)} records from {test_file}")
    print(f"First record:\n{json.dumps(sample_data[0], indent=2)}")
    
    # Generate schema with AI
    engine = AIInferenceEngine()
    
    request = SchemaGenerationRequest(
        sample_data=sample_data[:10],  # Use first 10 for demo
        schema_name="Customer Data",
        schema_description="E-commerce customer data from test dataset",
        class_id="https://ns.adobe.com/xdm/context/profile",
    )
    
    print("\n🤖 Analyzing data with AI...")
    result = await engine.generate_schema_with_ai(request)
    
    print("\n✅ Schema Generated!")
    print(f"\n📊 AI Reasoning:\n{result.reasoning}")
    
    print(f"\n🔑 Identity Recommendations:")
    for field, reason in result.identity_recommendations.items():
        print(f"  - {field}: {reason}")
    
    if result.data_quality_issues:
        print(f"\n⚠️  Data Quality Issues Found:")
        for issue in result.data_quality_issues:
            print(f"  - {issue}")
    
    return result


async def main():
    """Run all demos."""
    print("\n" + "=" * 80)
    print("🚀 AI-Powered Schema Generation Demo")
    print("=" * 80)
    print("\nThis demo showcases enhanced AI schema generation with:")
    print("  ✓ Anthropic tool calling for structured output")
    print("  ✓ XDM expertise system prompts")
    print("  ✓ Field-level confidence scores")
    print("  ✓ Identity strategy recommendations")
    print("  ✓ Data quality issue detection")
    print("  ✓ Few-shot learning examples")
    
    # Check if AI is configured
    try:
        config = get_config()
        if not config.anthropic_api_key and not config.openai_api_key:
            print("\n⚠️  No AI API key configured!")
            print("Run: adobe ai set-key anthropic")
            print("Or set ANTHROPIC_API_KEY environment variable")
            return
    except Exception as e:
        print(f"\n⚠️  Configuration error: {e}")
        return
    
    try:
        # Run demos
        await demo_b2c_customer_profile()
        await demo_ecommerce_event()
        await demo_from_test_data()
        
        print("\n" + "=" * 80)
        print("✅ All demos completed!")
        print("=" * 80)
        print("\nKey Improvements:")
        print("  • Structured output eliminates JSON parsing errors")
        print("  • Confidence scores help prioritize recommendations")
        print("  • XDM-aware prompts ensure best practices")
        print("  • Data quality checks catch issues early")
        print("  • Identity strategy aligns with AEP patterns")
        
    except ValueError as e:
        if "No AI provider configured" in str(e):
            print(f"\n⚠️  {e}")
            print("\nTo configure:")
            print("  1. Get API key from https://console.anthropic.com")
            print("  2. Run: adobe ai set-key anthropic")
            print("  3. Or set ANTHROPIC_API_KEY environment variable")
        else:
            raise
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
