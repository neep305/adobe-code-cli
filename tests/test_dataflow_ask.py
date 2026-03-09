"""Tests for natural language dataflow querying."""

import pytest
from unittest.mock import AsyncMock, Mock, patch

from adobe_experience.agent.inference import (
    AIInferenceEngine,
    DataflowQueryIntent,
    DataflowQueryRequest,
    DataflowQueryResponse,
)
from adobe_experience.core.config import AEPConfig
from adobe_experience.flow.models import Dataflow, DataflowState, FlowSpec


@pytest.fixture
def mock_config():
    """Create mock AEP config."""
    config = Mock(spec=AEPConfig)
    config.anthropic_api_key = Mock()
    config.anthropic_api_key.get_secret_value.return_value = "sk-ant-test-key-actual-length-requirement-met"
    config.openai_api_key = None
    config.ai_provider = "anthropic"
    config.ai_model = "claude-3-5-sonnet-20241022"
    return config


@pytest.fixture
def mock_anthropic_client():
    """Create mock Anthropic client."""
    return Mock()


@pytest.fixture
def sample_dataflows():
    """Create sample dataflow objects."""
    return [
        Dataflow(
            id="df1-1234-5678-9abc",
            name="Customer Data Sync",
            state=DataflowState.ENABLED,
            flow_spec=FlowSpec(id="spec-123", version="1.0"),
            created_at=1708500000000,
            updated_at=1708500000000,
            source_connection_ids=["conn-1"],
            target_connection_ids=["conn-2"],
            etag="etag-1",
        ),
        Dataflow(
            id="df2-1234-5678-9abc",
            name="Order Pipeline",
            state=DataflowState.ENABLED,
            flow_spec=FlowSpec(id="spec-456", version="1.0"),
            created_at=1708500000000,
            updated_at=1708500000000,
            source_connection_ids=["conn-3"],
            target_connection_ids=["conn-4"],
            etag="etag-2",
        ),
        Dataflow(
            id="df3-1234-5678-9abc",
            name="Event Stream",
            state=DataflowState.ENABLED,
            flow_spec=FlowSpec(id="spec-789", version="1.0"),
            created_at=1708500000000,
            updated_at=1708500000000,
            source_connection_ids=["conn-5"],
            target_connection_ids=["conn-6"],
            etag="etag-3",
        ),
    ]


class TestDataflowQueryModels:
    """Test dataflow query Pydantic models."""

    def test_dataflow_query_intent_enum(self):
        """Test DataflowQueryIntent enum values."""
        assert DataflowQueryIntent.LIST_FAILED_DATAFLOWS == "list_failed_dataflows"
        assert DataflowQueryIntent.HEALTH_CHECK == "health_check"
        assert DataflowQueryIntent.GET_DETAILS == "get_details"
        assert DataflowQueryIntent.COMPARE_DATAFLOWS == "compare_dataflows"
        assert DataflowQueryIntent.LIST_ALL == "list_all"

    def test_dataflow_query_request_defaults(self):
        """Test DataflowQueryRequest default values."""
        request = DataflowQueryRequest(intent=DataflowQueryIntent.LIST_FAILED_DATAFLOWS)
        
        assert request.intent == DataflowQueryIntent.LIST_FAILED_DATAFLOWS
        assert request.time_range_days == 7
        assert request.severity_threshold == 80.0
        assert request.dataflow_filter is None

    def test_dataflow_query_request_validation(self):
        """Test DataflowQueryRequest field validation."""
        # Valid request
        request = DataflowQueryRequest(
            intent=DataflowQueryIntent.HEALTH_CHECK,
            time_range_days=14,
            severity_threshold=90.0,
        )
        assert request.time_range_days == 14
        assert request.severity_threshold == 90.0

    def test_dataflow_query_response_structure(self):
        """Test DataflowQueryResponse structure."""
        response = DataflowQueryResponse(
            summary="3개의 dataflow에서 문제가 발견되었습니다.",
            failed_dataflows=[
                {"name": "Test Flow", "id": "123", "success_rate": 75.0}
            ],
            total_checked=10,
            language="ko",
            intent=DataflowQueryIntent.LIST_FAILED_DATAFLOWS,
            time_range_days=7,
        )
        
        assert response.summary == "3개의 dataflow에서 문제가 발견되었습니다."
        assert len(response.failed_dataflows) == 1
        assert response.total_checked == 10
        assert response.language == "ko"
        assert response.intent == DataflowQueryIntent.LIST_FAILED_DATAFLOWS


class TestLanguageDetection:
    """Test language auto-detection in dataflow queries."""

    def test_detect_korean_question(self):
        """Test Korean language detection."""
        korean_questions = [
            "현재 fail된 dataflow를 알려줘",
            "데이터플로우 상태 확인",
            "문제가 있는 것을 보여줘",
        ]
        
        for question in korean_questions:
            has_korean = any('\uac00' <= char <= '\ud7a3' for char in question)
            assert has_korean, f"Korean not detected in: {question}"

    def test_detect_english_question(self):
        """Test English language detection (no Korean chars)."""
        english_questions = [
            "Show me failed dataflows",
            "What dataflows have issues?",
            "Check dataflow health",
        ]
        
        for question in english_questions:
            has_korean = any('\uac00' <= char <= '\ud7a3' for char in question)
            assert not has_korean, f"Korean incorrectly detected in: {question}"


class TestAnswerDataflowQuestion:
    """Test AIInferenceEngine.answer_dataflow_question method."""

    @pytest.mark.asyncio
    async def test_answer_question_korean(self, mock_config, mock_anthropic_client, sample_dataflows):
        """Test answering Korean question."""
        # Mock Anthropic API response
        mock_response = Mock()
        mock_response.content = [
            Mock(
                type="tool_use",
                input={
                    "intent": "list_failed_dataflows",
                    "time_range_days": 7,
                    "severity_threshold": 80.0,
                }
            )
        ]
        
        mock_summary_response = Mock()
        mock_summary_response.content = [
            Mock(text="3개의 dataflow에서 최근 7일간 문제가 발견되었습니다.")
        ]
        
        mock_anthropic_client.messages.create.side_effect = [mock_response, mock_summary_response]
        
        with patch('adobe_experience.agent.inference.Anthropic', return_value=mock_anthropic_client):
            engine = AIInferenceEngine(mock_config)
            
            result = await engine.answer_dataflow_question(
                question="현재 fail된 dataflow를 알려줘",
                dataflows=sample_dataflows,
                language="ko",
            )
        
        assert isinstance(result, DataflowQueryResponse)
        assert result.language == "ko"
        assert result.total_checked == 3
        assert "dataflow" in result.summary.lower() or "문제" in result.summary

    @pytest.mark.asyncio
    async def test_answer_question_english(self, mock_config, mock_anthropic_client, sample_dataflows):
        """Test answering English question."""
        # Mock Anthropic API response  
        mock_response = Mock()
        mock_response.content = [
            Mock(
                type="tool_use",
                input={
                    "intent": "list_failed_dataflows",
                    "time_range_days": 7,
                    "severity_threshold": 80.0,
                }
            )
        ]
        
        mock_summary_response = Mock()
        mock_summary_response.content = [
            Mock(text="Issues found in 3 dataflows over the last 7 days.")
        ]
        
        mock_anthropic_client.messages.create.side_effect = [mock_response, mock_summary_response]
        
        with patch('adobe_experience.agent.inference.Anthropic', return_value=mock_anthropic_client):
            engine = AIInferenceEngine(mock_config)
            
            result = await engine.answer_dataflow_question(
                question="Show me failed dataflows",
                dataflows=sample_dataflows,
                language="en",
            )
        
        assert isinstance(result, DataflowQueryResponse)
        assert result.language == "en"
        assert result.total_checked == 3

    @pytest.mark.asyncio
    async def test_auto_detect_language_korean(self, mock_config, mock_anthropic_client, sample_dataflows):
        """Test automatic language detection for Korean."""
        # Mock responses
        mock_response = Mock()
        mock_response.content = [
            Mock(
                type="tool_use",
                input={
                    "intent": "health_check",
                    "time_range_days": 3,
                    "severity_threshold": 80.0,
                }
            )
        ]
        
        mock_summary_response = Mock()
        mock_summary_response.content = [Mock(text="모든 dataflow가 정상입니다.")]
        
        mock_anthropic_client.messages.create.side_effect = [mock_response, mock_summary_response]
        
        with patch('adobe_experience.agent.inference.Anthropic', return_value=mock_anthropic_client):
            engine = AIInferenceEngine(mock_config)
            
            # Don't specify language - should auto-detect Korean
            result = await engine.answer_dataflow_question(
                question="최근 3일간 문제가 있었던 것은?",
                dataflows=sample_dataflows,
            )
        
        assert result.language == "ko"

    @pytest.mark.asyncio
    async def test_auto_detect_language_english(self, mock_config, mock_anthropic_client, sample_dataflows):
        """Test automatic language detection for English."""
        # Mock responses
        mock_response = Mock()
        mock_response.content = [
            Mock(
                type="tool_use",
                input={
                    "intent": "list_all",
                    "time_range_days": 7,
                    "severity_threshold": 80.0,
                }
            )
        ]
        
        mock_summary_response = Mock()
        mock_summary_response.content = [Mock(text="All dataflows are healthy.")]
        
        mock_anthropic_client.messages.create.side_effect = [mock_response, mock_summary_response]
        
        with patch('adobe_experience.agent.inference.Anthropic', return_value=mock_anthropic_client):
            engine = AIInferenceEngine(mock_config)
            
            # Don't specify language - should auto-detect English
            result = await engine.answer_dataflow_question(
                question="Show all dataflows",
                dataflows=sample_dataflows,
            )
        
        assert result.language == "en"

    @pytest.mark.asyncio
    async def test_intent_classification(self, mock_config, mock_anthropic_client, sample_dataflows):
        """Test different intent classifications."""
        test_cases = [
            ("현재 fail된 dataflow를 알려줘", DataflowQueryIntent.LIST_FAILED_DATAFLOWS),
            ("dataflow 상태 확인", DataflowQueryIntent.HEALTH_CHECK),
            ("dataflow-123 details", DataflowQueryIntent.GET_DETAILS),
        ]
        
        with patch('adobe_experience.agent.inference.Anthropic', return_value=mock_anthropic_client):
            engine = AIInferenceEngine(mock_config)
            
            for question, expected_intent in test_cases:
                mock_response = Mock()
                mock_response.content = [
                    Mock(
                        type="tool_use",
                        input={
                            "intent": expected_intent.value,
                            "time_range_days": 7,
                            "severity_threshold": 80.0,
                        }
                    )
                ]
                
                mock_summary_response = Mock()
                mock_summary_response.content = [Mock(text="Summary text")]
                
                mock_anthropic_client.messages.create.side_effect = [mock_response, mock_summary_response]
                
                result = await engine.answer_dataflow_question(
                    question=question,
                    dataflows=sample_dataflows,
                )
                
                assert result.intent == expected_intent

    @pytest.mark.asyncio
    async def test_empty_dataflows_list(self, mock_config, mock_anthropic_client):
        """Test handling empty dataflows list."""
        # Mock responses
        mock_response = Mock()
        mock_response.content = [
            Mock(
                type="tool_use",
                input={
                    "intent": "list_all",
                    "time_range_days": 7,
                    "severity_threshold": 80.0,
                }
            )
        ]
        
        mock_summary_response = Mock()
        mock_summary_response.content = [Mock(text="No dataflows found.")]
        
        mock_anthropic_client.messages.create.side_effect = [mock_response, mock_summary_response]
        
        with patch('adobe_experience.agent.inference.Anthropic', return_value=mock_anthropic_client):
            engine = AIInferenceEngine(mock_config)
            
            result = await engine.answer_dataflow_question(
                question="Show all dataflows",
                dataflows=[],
            )
        
        assert result.total_checked == 0
        assert len(result.failed_dataflows) == 0

    @pytest.mark.asyncio
    async def test_authentication_error(self, mock_config, mock_anthropic_client, sample_dataflows):
        """Test handling authentication errors."""
        mock_anthropic_client.messages.create.side_effect = Exception("invalid x-api-key")
        
        with patch('adobe_experience.agent.inference.Anthropic', return_value=mock_anthropic_client):
            engine = AIInferenceEngine(mock_config)
            
            with pytest.raises(ValueError, match="API authentication failed"):
                await engine.answer_dataflow_question(
                    question="Show failures",
                    dataflows=sample_dataflows,
                )


class TestDataflowFiltering:
    """Test dataflow filtering logic."""

    def test_severity_threshold_filtering(self):
        """Test filtering by severity threshold."""
        dataflows_info = [
            {"name": "Flow 1", "success_rate": 95.0},
            {"name": "Flow 2", "success_rate": 75.0},
            {"name": "Flow 3", "success_rate": 85.0},
        ]
        
        threshold = 80.0
        filtered = [f for f in dataflows_info if f["success_rate"] < threshold]
        
        assert len(filtered) == 1
        assert filtered[0]["name"] == "Flow 2"

    def test_no_failures_scenario(self):
        """Test scenario where no failures exist."""
        dataflows_info = [
            {"name": "Flow 1", "success_rate": 100.0},
            {"name": "Flow 2", "success_rate": 98.0},
        ]
        
        threshold = 80.0
        filtered = [f for f in dataflows_info if f["success_rate"] < threshold]
        
        assert len(filtered) == 0

class TestInteractiveAskMode:
    """Test interactive ask mode functionality."""
    
    @patch("adobe_experience.cli.dataflow.Prompt.ask")
    @patch("adobe_experience.cli.dataflow._handle_single_question")
    def test_interactive_mode_with_exit_command(self, mock_handle_q, mock_prompt):
        """Test interactive mode exits on 'exit' command."""
        from adobe_experience.cli.dataflow import _interactive_ask_mode
        
        # Simulate user asking 2 questions then exiting
        mock_prompt.side_effect = [
            "Show failed dataflows",
            "What is the status?",
            "exit"
        ]
        
        _interactive_ask_mode(days=7, json_output=False)
        
        # Should have called handler twice (not for 'exit')
        assert mock_handle_q.call_count == 2
        assert mock_prompt.call_count == 3
        
        # Verify questions were passed correctly
        mock_handle_q.assert_any_call("Show failed dataflows", 7, False)
        mock_handle_q.assert_any_call("What is the status?", 7, False)
    
    @patch("adobe_experience.cli.dataflow.Prompt.ask")
    @patch("adobe_experience.cli.dataflow._handle_single_question")
    def test_interactive_mode_with_quit_command(self, mock_handle_q, mock_prompt):
        """Test interactive mode exits on 'quit' command."""
        from adobe_experience.cli.dataflow import _interactive_ask_mode
        
        mock_prompt.side_effect = ["question 1", "quit"]
        
        _interactive_ask_mode(days=7, json_output=False)
        
        assert mock_handle_q.call_count == 1
        mock_handle_q.assert_called_with("question 1", 7, False)
    
    @patch("adobe_experience.cli.dataflow.Prompt.ask")
    @patch("adobe_experience.cli.dataflow._handle_single_question")
    def test_interactive_mode_with_korean_exit(self, mock_handle_q, mock_prompt):
        """Test interactive mode exits on Korean '종료' command."""
        from adobe_experience.cli.dataflow import _interactive_ask_mode
        
        mock_prompt.side_effect = ["현재 fail된 dataflow?", "종료"]
        
        _interactive_ask_mode(days=7, json_output=False)
        
        assert mock_handle_q.call_count == 1
        mock_handle_q.assert_called_with("현재 fail된 dataflow?", 7, False)
    
    @patch("adobe_experience.cli.dataflow.Prompt.ask")
    @patch("adobe_experience.cli.dataflow._handle_single_question")
    def test_interactive_mode_skips_empty_questions(self, mock_handle_q, mock_prompt):
        """Test interactive mode skips empty input."""
        from adobe_experience.cli.dataflow import _interactive_ask_mode
        
        mock_prompt.side_effect = ["", "  ", "valid question", "q"]
        
        _interactive_ask_mode(days=7, json_output=False)
        
        # Should only handle the valid question
        assert mock_handle_q.call_count == 1
        mock_handle_q.assert_called_with("valid question", 7, False)
    
    @patch("adobe_experience.cli.dataflow.Prompt.ask")
    @patch("adobe_experience.cli.dataflow._handle_single_question")
    def test_interactive_mode_handles_keyboard_interrupt_in_prompt(self, mock_handle_q, mock_prompt):
        """Test interactive mode handles Ctrl+C in prompt gracefully."""
        from adobe_experience.cli.dataflow import _interactive_ask_mode
        
        # First KeyboardInterrupt, then exit
        mock_prompt.side_effect = [KeyboardInterrupt(), "exit"]
        
        _interactive_ask_mode(days=7, json_output=False)
        
        # Should not have processed any questions
        assert mock_handle_q.call_count == 0
    
    @patch("adobe_experience.cli.dataflow.Prompt.ask")
    @patch("adobe_experience.cli.dataflow._handle_single_question")
    def test_interactive_mode_keyboard_interrupt_outer(self, mock_handle_q, mock_prompt):
        """Test interactive mode handles outer KeyboardInterrupt."""
        from adobe_experience.cli.dataflow import _interactive_ask_mode
        
        # Simulate Ctrl+C during question handling
        mock_prompt.return_value = "question"
        mock_handle_q.side_effect = KeyboardInterrupt()
        
        # Should exit gracefully
        _interactive_ask_mode(days=7, json_output=False)
        
        assert mock_handle_q.call_count == 1
    
    @patch("adobe_experience.cli.dataflow._handle_single_question")
    def test_ask_command_one_shot_mode(self, mock_handle_q):
        """Test ask command in one-shot mode (backward compatibility)."""
        from adobe_experience.cli.dataflow import ask_dataflow_question
        
        ask_dataflow_question(
            question="Show failed dataflows",
            days=7,
            json_output=False
        )
        
        mock_handle_q.assert_called_once_with("Show failed dataflows", 7, False)
    
    @patch("adobe_experience.cli.dataflow._interactive_ask_mode")
    def test_ask_command_interactive_mode(self, mock_interactive):
        """Test ask command enters interactive mode when no question provided."""
        from adobe_experience.cli.dataflow import ask_dataflow_question
        
        ask_dataflow_question(
            question=None,
            days=7,
            json_output=False
        )
        
        mock_interactive.assert_called_once_with(7, False)
    
    @patch("adobe_experience.cli.dataflow._interactive_ask_mode")
    def test_ask_command_interactive_with_custom_days(self, mock_interactive):
        """Test ask command passes custom days to interactive mode."""
        from adobe_experience.cli.dataflow import ask_dataflow_question
        
        ask_dataflow_question(
            question=None,
            days=30,
            json_output=True
        )
        
        mock_interactive.assert_called_once_with(30, True)