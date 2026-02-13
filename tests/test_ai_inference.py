"""Tests for AI-powered schema generation with structured output."""

import json
from unittest.mock import MagicMock, patch

import pytest

from adobe_experience.agent.inference import (
    AIInferenceEngine,
    SchemaGenerationRequest,
    SchemaGenerationResponse,
)
from adobe_experience.schema.models import (
    AIDataQualityIssue,
    AIFieldGroupSuggestion,
    AIFieldRecommendation,
    AIIdentityStrategy,
    AISchemaAnalysis,
)


@pytest.fixture
def sample_b2c_data():
    """Sample B2C customer data."""
    return [
        {
            "email": "john.doe@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "age": 35,
            "loyalty_tier": "gold",
            "signup_date": "2023-01-15",
        },
        {
            "email": "jane.smith@example.com",
            "first_name": "Jane",
            "last_name": "Smith",
            "age": 28,
            "loyalty_tier": "silver",
            "signup_date": "2023-03-22",
        },
    ]


@pytest.fixture
def mock_ai_analysis():
    """Mock AI analysis result with structured output."""
    return AISchemaAnalysis(
        field_recommendations={
            "email": AIFieldRecommendation(
                field_name="email",
                xdm_type="string",
                xdm_format="email",
                is_identity=True,
                identity_namespace="Email",
                is_required=True,
                is_primary_identity=True,
                confidence=0.95,
                reasoning="Email is the standard primary identity for B2C profiles",
                enum_values=None,
                field_group_match="Email Address",
            ),
            "age": AIFieldRecommendation(
                field_name="age",
                xdm_type="integer",
                xdm_format=None,
                is_identity=False,
                identity_namespace=None,
                is_required=False,
                is_primary_identity=False,
                confidence=0.98,
                reasoning="Numeric age values detected, integer type recommended",
                enum_values=None,
                field_group_match=None,
            ),
            "loyalty_tier": AIFieldRecommendation(
                field_name="loyalty_tier",
                xdm_type="string",
                xdm_format=None,
                is_identity=False,
                identity_namespace=None,
                is_required=False,
                is_primary_identity=False,
                confidence=0.90,
                reasoning="Limited categorical values suggest enum type",
                enum_values=["gold", "silver", "platinum"],
                field_group_match="Loyalty",
            ),
        },
        identity_strategy=AIIdentityStrategy(
            primary_identity_field="email",
            primary_namespace="Email",
            secondary_identities=[],
            identity_graph_strategy="email-based",
            profile_merge_policy="timestamp-ordered",
            reasoning="Email-based identity is standard for B2C customer profiles",
            aep_best_practice_compliance="Fully compliant with AEP B2C patterns",
        ),
        data_quality_issues=[
            AIDataQualityIssue(
                severity="warning",
                issue_type="missing_values",
                field_name="loyalty_tier",
                description="Some records have null loyalty_tier values",
                impact="Profile activation will work, but segmentation may be incomplete",
                recommendation="Set default value or mark as optional",
                affected_percentage=10.0,
            )
        ],
        xdm_class_recommendation="https://ns.adobe.com/xdm/context/profile",
        xdm_class_reasoning="Data contains customer attributes, Profile class is appropriate",
        field_group_suggestions=[
            AIFieldGroupSuggestion(
                field_group_name="Email Address",
                field_group_id="https://ns.adobe.com/xdm/context/profile-person-details",
                matched_fields=["email"],
                confidence=0.95,
                reasoning="Standard email field matches Adobe Email Address field group",
            )
        ],
        overall_reasoning="This is a standard B2C customer profile with email-based identity. "
        "Use Profile class with Email Address field group.",
        schema_version="1.0",
        complexity_score=3.5,
    )


def test_ai_field_recommendation_model():
    """Test AIFieldRecommendation Pydantic model."""
    rec = AIFieldRecommendation(
        field_name="email",
        xdm_type="string",
        xdm_format="email",
        is_identity=True,
        identity_namespace="Email",
        is_required=True,
        is_primary_identity=True,
        confidence=0.95,
        reasoning="Email field detected",
    )
    
    assert rec.field_name == "email"
    assert rec.xdm_type == "string"
    assert rec.xdm_format == "email"
    assert rec.is_identity is True
    assert rec.confidence == 0.95
    assert rec.is_primary_identity is True


def test_ai_identity_strategy_model():
    """Test AIIdentityStrategy Pydantic model."""
    strategy = AIIdentityStrategy(
        primary_identity_field="email",
        primary_namespace="Email",
        secondary_identities=[{"field": "phone", "namespace": "Phone"}],
        identity_graph_strategy="email-based",
        profile_merge_policy="timestamp-ordered",
        reasoning="Email is best for B2C",
        aep_best_practice_compliance="Compliant",
    )
    
    assert strategy.primary_identity_field == "email"
    assert strategy.primary_namespace == "Email"
    assert len(strategy.secondary_identities) == 1
    assert strategy.identity_graph_strategy == "email-based"


def test_ai_data_quality_issue_model():
    """Test AIDataQualityIssue Pydantic model."""
    issue = AIDataQualityIssue(
        severity="critical",
        issue_type="data_type_mismatch",
        field_name="age",
        description="Age field contains string values",
        impact="Ingestion will fail",
        recommendation="Convert to integer",
        affected_percentage=15.5,
    )
    
    assert issue.severity == "critical"
    assert issue.issue_type == "data_type_mismatch"
    assert issue.affected_percentage == 15.5


def test_ai_schema_analysis_model(mock_ai_analysis):
    """Test AISchemaAnalysis Pydantic model with all fields."""
    assert len(mock_ai_analysis.field_recommendations) == 3
    assert "email" in mock_ai_analysis.field_recommendations
    assert mock_ai_analysis.identity_strategy.primary_identity_field == "email"
    assert len(mock_ai_analysis.data_quality_issues) == 1
    assert mock_ai_analysis.complexity_score == 3.5


def test_ai_schema_analysis_json_schema():
    """Test that AISchemaAnalysis can generate JSON schema for tool calling."""
    json_schema = AISchemaAnalysis.model_json_schema()
    
    assert "properties" in json_schema
    assert "field_recommendations" in json_schema["properties"]
    assert "identity_strategy" in json_schema["properties"]
    assert "data_quality_issues" in json_schema["properties"]
    assert "title" in json_schema
    
    # Verify it's valid JSON
    json_str = json.dumps(json_schema)
    assert len(json_str) > 0


@pytest.mark.asyncio
async def test_generate_schema_with_structured_output(sample_b2c_data, mock_ai_analysis):
    """Test schema generation with Anthropic tool calling (structured output)."""
    
    # Mock Anthropic response with tool use
    mock_content_block = MagicMock()
    mock_content_block.type = "tool_use"
    mock_content_block.name = "analyze_xdm_schema"
    mock_content_block.input = mock_ai_analysis.model_dump()
    
    mock_response = MagicMock()
    mock_response.content = [mock_content_block]
    
    with patch("adobe_experience.agent.inference.Anthropic") as mock_anthropic_class:
        mock_anthropic_instance = MagicMock()
        mock_anthropic_instance.messages.create = MagicMock(return_value=mock_response)
        mock_anthropic_class.return_value = mock_anthropic_instance
        
        # Create engine with mocked Anthropic
        engine = AIInferenceEngine()
        engine.anthropic = mock_anthropic_instance
        engine.active_client = "anthropic"
        
        request = SchemaGenerationRequest(
            sample_data=sample_b2c_data,
            schema_name="Customer Profile",
            schema_description="B2C customer profiles",
            class_id="https://ns.adobe.com/xdm/context/profile",
        )
        
        result = await engine.generate_schema_with_ai(request)
        
        # Verify result structure
        assert isinstance(result, SchemaGenerationResponse)
        assert result.xdm_schema.title == "Customer Profile"
        assert result.reasoning == mock_ai_analysis.overall_reasoning
        assert len(result.identity_recommendations) > 0
        assert "email" in result.identity_recommendations
        
        # Verify Anthropic was called with tools
        mock_anthropic_instance.messages.create.assert_called_once()
        call_kwargs = mock_anthropic_instance.messages.create.call_args.kwargs
        assert "tools" in call_kwargs
        assert "tool_choice" in call_kwargs
        assert call_kwargs["tool_choice"]["name"] == "analyze_xdm_schema"


@pytest.mark.asyncio
async def test_generate_schema_fallback_to_text_parsing(sample_b2c_data):
    """Test fallback to text-based parsing when structured output fails."""
    
    # Mock Anthropic response without tool use (text response)
    mock_text_block = MagicMock()
    mock_text_block.type = "text"
    mock_text_block.text = """```json
{
    "recommended_identity_fields": {"email": "Best for B2C"},
    "primary_identity_field": "email",
    "data_quality_issues": [],
    "field_recommendations": {
        "email": {
            "xdm_type": "string",
            "format": "email",
            "is_identity": true,
            "identity_namespace": "Email",
            "reasoning": "Email field"
        }
    },
    "xdm_mixins": [],
    "reasoning": "B2C profile"
}
```"""
    
    mock_response = MagicMock()
    mock_response.content = [mock_text_block]
    
    with patch("adobe_experience.agent.inference.Anthropic") as mock_anthropic_class:
        mock_anthropic_instance = MagicMock()
        mock_anthropic_instance.messages.create = MagicMock(return_value=mock_response)
        mock_anthropic_class.return_value = mock_anthropic_instance
        
        engine = AIInferenceEngine()
        engine.anthropic = mock_anthropic_instance
        engine.active_client = "anthropic"
        
        request = SchemaGenerationRequest(
            sample_data=sample_b2c_data,
            schema_name="Customer Profile",
            class_id="https://ns.adobe.com/xdm/context/profile",
        )
        
        result = await engine.generate_schema_with_ai(request)
        
        # Should still work with text-based fallback
        assert isinstance(result, SchemaGenerationResponse)
        assert result.xdm_schema.title == "Customer Profile"
        assert result.reasoning == "B2C profile"


@pytest.mark.asyncio
async def test_generate_schema_handles_json_parse_error(sample_b2c_data):
    """Test graceful handling of JSON parse errors."""
    
    # Mock Anthropic response with invalid JSON
    mock_text_block = MagicMock()
    mock_text_block.type = "text"
    mock_text_block.text = "This is not valid JSON {invalid"
    
    mock_response = MagicMock()
    mock_response.content = [mock_text_block]
    
    with patch("adobe_experience.agent.inference.Anthropic") as mock_anthropic_class:
        mock_anthropic_instance = MagicMock()
        mock_anthropic_instance.messages.create = MagicMock(return_value=mock_response)
        mock_anthropic_class.return_value = mock_anthropic_instance
        
        engine = AIInferenceEngine()
        engine.anthropic = mock_anthropic_instance
        engine.active_client = "anthropic"
        
        request = SchemaGenerationRequest(
            sample_data=sample_b2c_data,
            schema_name="Customer Profile",
        )
        
        result = await engine.generate_schema_with_ai(request)
        
        # Should return basic schema without AI enhancements
        assert isinstance(result, SchemaGenerationResponse)
        assert result.xdm_schema.title == "Customer Profile"
        assert "parsing failed" in result.reasoning.lower()
        assert len(result.data_quality_issues) > 0
        assert "parsing error" in result.data_quality_issues[0].lower()


def test_ai_inference_engine_system_prompt():
    """Test that system prompt includes XDM expertise."""
    engine = AIInferenceEngine()
    
    assert "Adobe Experience Platform" in engine.XDM_EXPERT_SYSTEM_PROMPT
    assert "XDM" in engine.XDM_EXPERT_SYSTEM_PROMPT
    assert "Profile" in engine.XDM_EXPERT_SYSTEM_PROMPT
    assert "ExperienceEvent" in engine.XDM_EXPERT_SYSTEM_PROMPT
    assert "Email" in engine.XDM_EXPERT_SYSTEM_PROMPT
    assert "identity" in engine.XDM_EXPERT_SYSTEM_PROMPT.lower()


def test_ai_inference_engine_few_shot_examples():
    """Test that few-shot examples are included."""
    engine = AIInferenceEngine()
    
    assert hasattr(engine, "SCHEMA_GENERATION_EXAMPLES")
    examples = engine.SCHEMA_GENERATION_EXAMPLES
    
    assert "Example 1" in examples
    assert "B2C Customer Profile" in examples
    assert "E-commerce" in examples or "Purchase" in examples
    assert "Product" in examples
    assert "email" in examples.lower()
    assert "price" in examples.lower()


@pytest.mark.asyncio
async def test_xdm_class_context_in_prompt(sample_b2c_data):
    """Test that XDM class context is included in the prompt."""
    
    mock_response = MagicMock()
    mock_response.content = [MagicMock(type="text", text='{"reasoning": "test"}')]
    
    with patch("adobe_experience.agent.inference.Anthropic") as mock_anthropic_class:
        mock_anthropic_instance = MagicMock()
        mock_anthropic_instance.messages.create = MagicMock(return_value=mock_response)
        mock_anthropic_class.return_value = mock_anthropic_instance
        
        engine = AIInferenceEngine()
        engine.anthropic = mock_anthropic_instance
        engine.active_client = "anthropic"
        
        # Test with Profile class
        request = SchemaGenerationRequest(
            sample_data=sample_b2c_data,
            schema_name="Test",
            class_id="https://ns.adobe.com/xdm/context/profile",
        )
        
        await engine.generate_schema_with_ai(request)
        
        # Check that prompt includes class context
        call_kwargs = mock_anthropic_instance.messages.create.call_args.kwargs
        assert "messages" in call_kwargs
        user_message = call_kwargs["messages"][0]["content"]
        assert "Profile" in user_message
        assert "attributes" in user_message or "identity" in user_message


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
