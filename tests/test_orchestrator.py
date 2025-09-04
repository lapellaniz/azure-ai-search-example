"""
Tests for the prompt retrieval orchestrator.

This module contains comprehensive tests for the PromptRetrievalOrchestrator class,
covering orchestration flow, fallback strategies, error handling, and configuration scenarios.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch

from prompt_retrieval.common.models import (
    PromptRetrievalInput,
    PromptRetrievalOutput,
    QuestionInput,
    QuestionPromptMatch,
)
from prompt_retrieval.orchestrator.config import OrchestratorConfig
from prompt_retrieval.orchestrator.orchestrator import PromptRetrievalOrchestrator
from prompt_retrieval.strategies.similarity_search.strategy import SimilaritySearchPromptStrategy
from prompt_retrieval.strategies.passthrough.strategy import PassthroughPromptStrategy
from prompt_retrieval.strategies.dynamic_prompt.strategy import DynamicPromptStrategy


@pytest.fixture
def orchestrator_config():
    """Create a test orchestrator configuration."""
    return OrchestratorConfig(
        enable_dynamic_prompt=True,
        similarity_threshold=0.75,
        max_parallel_requests=5,
        fallback_to_passthrough=True,
        fallback_to_dynamic=True,
    )


@pytest.fixture
def minimal_orchestrator_config():
    """Create a minimal orchestrator configuration with no fallbacks."""
    return OrchestratorConfig(
        enable_dynamic_prompt=False,
        similarity_threshold=0.8,
        max_parallel_requests=3,
        fallback_to_passthrough=False,
        fallback_to_dynamic=False,
    )


@pytest.fixture
def mock_telemetry():
    """Create a mock telemetry service."""
    mock = Mock()
    mock.info = Mock()
    mock.debug = Mock()
    mock.warning = Mock()
    mock.error = Mock()
    mock.exception = Mock()
    mock.record_matched_questions = Mock()
    mock.start_span = Mock()
    
    # Make start_span return a context manager
    mock_span = Mock()
    mock_span.__enter__ = Mock(return_value=mock_span)
    mock_span.__exit__ = Mock(return_value=False)
    mock.start_span.return_value = mock_span
    
    return mock


@pytest.fixture
def mock_similarity_strategy():
    """Create a mock similarity search strategy."""
    return Mock(spec=SimilaritySearchPromptStrategy)


@pytest.fixture
def mock_passthrough_strategy():
    """Create a mock passthrough strategy."""
    return Mock(spec=PassthroughPromptStrategy)


@pytest.fixture
def mock_dynamic_strategy():
    """Create a mock dynamic prompt strategy."""
    return Mock(spec=DynamicPromptStrategy)


@pytest.fixture
def sample_questions():
    """Create sample questions for testing."""
    return [
        QuestionInput(question_id="q1", question_text="What is your age?"),
        QuestionInput(question_id="q2", question_text="Do you have diabetes?"),
        QuestionInput(question_id="q3", question_text="What medications are you taking?"),
    ]


@pytest.fixture
def high_score_matches():
    """Create sample matches with high similarity scores."""
    return [
        QuestionPromptMatch(
            question_id="q1",
            question_text="What is your age?",
            match_found=True,
            match_score=0.9,
            selected_prompt_text="Please provide your current age in years."
        ),
        QuestionPromptMatch(
            question_id="q2",
            question_text="Do you have diabetes?",
            match_found=True,
            match_score=0.85,
            selected_prompt_text="Please indicate if you have been diagnosed with diabetes."
        ),
    ]


@pytest.fixture
def low_score_matches():
    """Create sample matches with low similarity scores."""
    return [
        QuestionPromptMatch(
            question_id="q1",
            question_text="What is your age?",
            match_found=True,
            match_score=0.6,  # Below default threshold of 0.75
            selected_prompt_text="Some irrelevant prompt."
        ),
        QuestionPromptMatch(
            question_id="q2",
            question_text="Do you have diabetes?",
            match_found=False,
            match_score=None,
        ),
    ]


class TestOrchestratorInitialization:
    """Test orchestrator initialization and dependency injection."""

    def test_orchestrator_initialization_with_required_dependencies(
        self, orchestrator_config, mock_telemetry, mock_similarity_strategy
    ):
        """Test orchestrator initialization with only required dependencies."""
        orchestrator = PromptRetrievalOrchestrator(
            config=orchestrator_config,
            telemetry=mock_telemetry,
            similarity_strategy=mock_similarity_strategy,
        )
        
        assert orchestrator._config == orchestrator_config
        assert orchestrator._logger == mock_telemetry
        assert orchestrator._similarity_strategy == mock_similarity_strategy
        assert orchestrator._passthrough_strategy is None
        assert orchestrator._dynamic_strategy is None

    def test_orchestrator_initialization_with_all_dependencies(
        self, 
        orchestrator_config,
        mock_telemetry,
        mock_similarity_strategy,
        mock_passthrough_strategy,
        mock_dynamic_strategy
    ):
        """Test orchestrator initialization with all optional dependencies."""
        orchestrator = PromptRetrievalOrchestrator(
            config=orchestrator_config,
            telemetry=mock_telemetry,
            similarity_strategy=mock_similarity_strategy,
            passthrough_strategy=mock_passthrough_strategy,
            dynamic_strategy=mock_dynamic_strategy,
        )
        
        assert orchestrator._config == orchestrator_config
        assert orchestrator._logger == mock_telemetry
        assert orchestrator._similarity_strategy == mock_similarity_strategy
        assert orchestrator._passthrough_strategy == mock_passthrough_strategy
        assert orchestrator._dynamic_strategy == mock_dynamic_strategy


class TestOrchestratorMainFlow:
    """Test the main orchestration flow."""

    @pytest.mark.asyncio
    async def test_retrieve_prompts_no_questions_found(
        self, orchestrator_config, mock_telemetry, mock_similarity_strategy
    ):
        """Test behavior when no questions are found for the assessment template."""
        orchestrator = PromptRetrievalOrchestrator(
            config=orchestrator_config,
            telemetry=mock_telemetry,
            similarity_strategy=mock_similarity_strategy,
        )
        
        # Mock _get_questions_for_template to return empty list
        orchestrator._get_questions_for_template = AsyncMock(return_value=[])
        orchestrator._write_matches_to_store = AsyncMock()
        
        await orchestrator.retrieve_prompts("test-template-123")
        
        # Should log warning and return early
        mock_telemetry.warning.assert_called_once()
        orchestrator._write_matches_to_store.assert_not_called()

    @pytest.mark.asyncio
    async def test_retrieve_prompts_similarity_only_success(
        self, 
        orchestrator_config,
        mock_telemetry,
        mock_similarity_strategy,
        sample_questions,
        high_score_matches
    ):
        """Test successful orchestration with similarity search only."""
        orchestrator = PromptRetrievalOrchestrator(
            config=orchestrator_config,
            telemetry=mock_telemetry,
            similarity_strategy=mock_similarity_strategy,
        )
        
        # Mock dependencies
        orchestrator._get_questions_for_template = AsyncMock(return_value=sample_questions)
        orchestrator._write_matches_to_store = AsyncMock()
        
        # Mock similarity strategy to return high-score matches
        mock_similarity_strategy.retrieve_prompts = AsyncMock(
            return_value=PromptRetrievalOutput(
                assessment_template_id="test-template-123",
                results=high_score_matches
            )
        )
        
        await orchestrator.retrieve_prompts("test-template-123")
        
        # Verify calls
        orchestrator._get_questions_for_template.assert_called_once_with("test-template-123")
        mock_similarity_strategy.retrieve_prompts.assert_called_once()
        orchestrator._write_matches_to_store.assert_called_once()
        
        # Check that correct matches were written
        written_matches = orchestrator._write_matches_to_store.call_args[0][1]
        assert len(written_matches) == 2
        assert all(match.match_score >= orchestrator_config.similarity_threshold for match in written_matches)

    @pytest.mark.asyncio
    async def test_retrieve_prompts_with_fallback_to_passthrough(
        self,
        orchestrator_config,
        mock_telemetry,
        mock_similarity_strategy,
        mock_passthrough_strategy,
        sample_questions,
        low_score_matches
    ):
        """Test orchestration flow with fallback to passthrough strategy."""
        orchestrator = PromptRetrievalOrchestrator(
            config=orchestrator_config,
            telemetry=mock_telemetry,
            similarity_strategy=mock_similarity_strategy,
            passthrough_strategy=mock_passthrough_strategy,
        )
        
        # Mock dependencies
        orchestrator._get_questions_for_template = AsyncMock(return_value=sample_questions)
        orchestrator._write_matches_to_store = AsyncMock()
        
        # Mock similarity strategy to return low-score matches
        mock_similarity_strategy.retrieve_prompts = AsyncMock(
            return_value=PromptRetrievalOutput(
                assessment_template_id="test-template-123",
                results=low_score_matches
            )
        )
        
        # Mock passthrough strategy for remaining questions
        passthrough_matches = [
            QuestionPromptMatch(
                question_id="q3",
                question_text="What medications are you taking?",
                match_found=True,
                selected_prompt_text="Based on your question: What medications are you taking?"
            )
        ]
        mock_passthrough_strategy.retrieve_prompts = AsyncMock(
            return_value=PromptRetrievalOutput(
                assessment_template_id="test-template-123",
                results=passthrough_matches
            )
        )
        
        await orchestrator.retrieve_prompts("test-template-123")
        
        # Verify both strategies were called
        mock_similarity_strategy.retrieve_prompts.assert_called_once()
        mock_passthrough_strategy.retrieve_prompts.assert_called_once()
        
        # Check that passthrough was called with all unmatched questions 
        # (both low-score and no-match questions from similarity search)
        passthrough_call_args = mock_passthrough_strategy.retrieve_prompts.call_args[0][0]
        assert len(passthrough_call_args.questions) == 3  # All questions since none met threshold
        question_ids = {q.question_id for q in passthrough_call_args.questions}
        assert question_ids == {"q1", "q2", "q3"}

    @pytest.mark.asyncio
    async def test_retrieve_prompts_with_dynamic_fallback(
        self,
        orchestrator_config,
        mock_telemetry,
        mock_similarity_strategy,
        mock_dynamic_strategy,
        sample_questions
    ):
        """Test orchestration flow with fallback to dynamic prompt generation."""
        # Configure for dynamic fallback only
        orchestrator_config.fallback_to_passthrough = False
        orchestrator_config.fallback_to_dynamic = True
        orchestrator_config.enable_dynamic_prompt = True
        
        orchestrator = PromptRetrievalOrchestrator(
            config=orchestrator_config,
            telemetry=mock_telemetry,
            similarity_strategy=mock_similarity_strategy,
            dynamic_strategy=mock_dynamic_strategy,
        )
        
        # Mock dependencies
        orchestrator._get_questions_for_template = AsyncMock(return_value=sample_questions)
        orchestrator._write_matches_to_store = AsyncMock()
        
        # Mock similarity strategy to return no matches
        mock_similarity_strategy.retrieve_prompts = AsyncMock(
            return_value=PromptRetrievalOutput(
                assessment_template_id="test-template-123",
                results=[]
            )
        )
        
        # Mock dynamic strategy
        dynamic_matches = [
            QuestionPromptMatch(
                question_id="q1",
                question_text="What is your age?",
                match_found=True,
                selected_prompt_text="Generated prompt for age question"
            )
        ]
        mock_dynamic_strategy.retrieve_prompts = AsyncMock(
            return_value=PromptRetrievalOutput(
                assessment_template_id="test-template-123",
                results=dynamic_matches
            )
        )
        
        await orchestrator.retrieve_prompts("test-template-123")
        
        # Verify dynamic strategy was called
        mock_dynamic_strategy.retrieve_prompts.assert_called_once()
        
        # Verify results were written
        orchestrator._write_matches_to_store.assert_called_once()


class TestOrchestratorErrorHandling:
    """Test error handling in orchestrator."""

    @pytest.mark.asyncio
    async def test_similarity_strategy_exception_handling(
        self,
        minimal_orchestrator_config,  # Use minimal config with no fallbacks
        mock_telemetry,
        mock_similarity_strategy,
        sample_questions
    ):
        """Test that similarity strategy exceptions are handled gracefully."""
        orchestrator = PromptRetrievalOrchestrator(
            config=minimal_orchestrator_config,
            telemetry=mock_telemetry,
            similarity_strategy=mock_similarity_strategy,
        )
        
        # Mock dependencies
        orchestrator._get_questions_for_template = AsyncMock(return_value=sample_questions)
        orchestrator._write_matches_to_store = AsyncMock()
        
        # Mock similarity strategy to raise exception
        mock_similarity_strategy.retrieve_prompts = AsyncMock(
            side_effect=Exception("Search service unavailable")
        )
        
        await orchestrator.retrieve_prompts("test-template-123")
        
        # Should log error but continue execution
        mock_telemetry.error.assert_called()
        mock_telemetry.exception.assert_called()
        
        # Since similarity search failed and no fallbacks are enabled, should not write any results
        orchestrator._write_matches_to_store.assert_not_called()

    @pytest.mark.asyncio
    async def test_passthrough_strategy_exception_handling(
        self,
        orchestrator_config,
        mock_telemetry,
        mock_similarity_strategy,
        mock_passthrough_strategy,
        sample_questions
    ):
        """Test that passthrough strategy exceptions are handled gracefully."""
        orchestrator = PromptRetrievalOrchestrator(
            config=orchestrator_config,
            telemetry=mock_telemetry,
            similarity_strategy=mock_similarity_strategy,
            passthrough_strategy=mock_passthrough_strategy,
        )
        
        # Mock dependencies
        orchestrator._get_questions_for_template = AsyncMock(return_value=sample_questions)
        orchestrator._write_matches_to_store = AsyncMock()
        
        # Mock similarity strategy to return no matches
        mock_similarity_strategy.retrieve_prompts = AsyncMock(
            return_value=PromptRetrievalOutput(
                assessment_template_id="test-template-123",
                results=[]
            )
        )
        
        # Mock passthrough strategy to raise exception
        mock_passthrough_strategy.retrieve_prompts = AsyncMock(
            side_effect=Exception("Passthrough service error")
        )
        
        await orchestrator.retrieve_prompts("test-template-123")
        
        # Should log error but continue execution
        mock_telemetry.error.assert_called()
        mock_telemetry.exception.assert_called()


class TestOrchestratorConfiguration:
    """Test different configuration scenarios."""

    @pytest.mark.asyncio
    async def test_orchestrator_with_minimal_config(
        self,
        minimal_orchestrator_config,
        mock_telemetry,
        mock_similarity_strategy,
        sample_questions,
        low_score_matches
    ):
        """Test orchestrator with minimal configuration (no fallbacks)."""
        orchestrator = PromptRetrievalOrchestrator(
            config=minimal_orchestrator_config,
            telemetry=mock_telemetry,
            similarity_strategy=mock_similarity_strategy,
        )
        
        # Mock dependencies
        orchestrator._get_questions_for_template = AsyncMock(return_value=sample_questions)
        orchestrator._write_matches_to_store = AsyncMock()
        
        # Mock similarity strategy to return low-score matches
        mock_similarity_strategy.retrieve_prompts = AsyncMock(
            return_value=PromptRetrievalOutput(
                assessment_template_id="test-template-123",
                results=low_score_matches
            )
        )
        
        await orchestrator.retrieve_prompts("test-template-123")
        
        # Only similarity strategy should be called
        mock_similarity_strategy.retrieve_prompts.assert_called_once()
        
        # Should warn about unmatched questions
        mock_telemetry.warning.assert_called()

    @pytest.mark.asyncio
    async def test_orchestrator_with_high_similarity_threshold(
        self,
        orchestrator_config,
        mock_telemetry,
        mock_similarity_strategy,
        mock_passthrough_strategy,
        sample_questions
    ):
        """Test orchestrator with high similarity threshold."""
        # Set very high threshold
        orchestrator_config.similarity_threshold = 0.95
        
        orchestrator = PromptRetrievalOrchestrator(
            config=orchestrator_config,
            telemetry=mock_telemetry,
            similarity_strategy=mock_similarity_strategy,
            passthrough_strategy=mock_passthrough_strategy,
        )
        
        # Mock dependencies
        orchestrator._get_questions_for_template = AsyncMock(return_value=sample_questions)
        orchestrator._write_matches_to_store = AsyncMock()
        
        # Mock similarity strategy to return medium-score matches
        medium_score_matches = [
            QuestionPromptMatch(
                question_id="q1",
                question_text="What is your age?",
                match_found=True,
                match_score=0.8,  # Below the 0.95 threshold
                selected_prompt_text="Some prompt."
            )
        ]
        mock_similarity_strategy.retrieve_prompts = AsyncMock(
            return_value=PromptRetrievalOutput(
                assessment_template_id="test-template-123",
                results=medium_score_matches
            )
        )
        
        # Mock passthrough for fallback
        mock_passthrough_strategy.retrieve_prompts = AsyncMock(
            return_value=PromptRetrievalOutput(
                assessment_template_id="test-template-123",
                results=[]
            )
        )
        
        await orchestrator.retrieve_prompts("test-template-123")
        
        # Should fallback to passthrough for all questions since none meet threshold
        mock_passthrough_strategy.retrieve_prompts.assert_called_once()
        passthrough_call_args = mock_passthrough_strategy.retrieve_prompts.call_args[0][0]
        assert len(passthrough_call_args.questions) == len(sample_questions)


class TestOrchestratorHelperMethods:
    """Test orchestrator helper methods."""

    def test_process_similarity_results_with_good_matches(
        self, orchestrator_config, mock_telemetry, mock_similarity_strategy, high_score_matches, sample_questions
    ):
        """Test processing similarity results with matches above threshold."""
        orchestrator = PromptRetrievalOrchestrator(
            config=orchestrator_config,
            telemetry=mock_telemetry,
            similarity_strategy=mock_similarity_strategy,
        )
        
        result = PromptRetrievalOutput(
            assessment_template_id="test-123",
            results=high_score_matches
        )
        
        matched, unmatched = orchestrator._process_similarity_results(result, sample_questions)
        
        assert len(matched) == 2
        assert len(unmatched) == 1
        assert unmatched[0].question_id == "q3"  # The one not in high_score_matches

    def test_process_similarity_results_with_low_scores(
        self, orchestrator_config, mock_telemetry, mock_similarity_strategy, low_score_matches, sample_questions
    ):
        """Test processing similarity results with matches below threshold."""
        orchestrator = PromptRetrievalOrchestrator(
            config=orchestrator_config,
            telemetry=mock_telemetry,
            similarity_strategy=mock_similarity_strategy,
        )
        
        result = PromptRetrievalOutput(
            assessment_template_id="test-123",
            results=low_score_matches
        )
        
        matched, unmatched = orchestrator._process_similarity_results(result, sample_questions)
        
        assert len(matched) == 0  # No matches above threshold
        assert len(unmatched) == 3  # All questions remain unmatched

    def test_process_similarity_results_empty_results(
        self, orchestrator_config, mock_telemetry, mock_similarity_strategy, sample_questions
    ):
        """Test processing empty similarity results."""
        orchestrator = PromptRetrievalOrchestrator(
            config=orchestrator_config,
            telemetry=mock_telemetry,
            similarity_strategy=mock_similarity_strategy,
        )
        
        result = PromptRetrievalOutput(
            assessment_template_id="test-123",
            results=[]
        )
        
        matched, unmatched = orchestrator._process_similarity_results(result, sample_questions)
        
        assert len(matched) == 0
        assert len(unmatched) == 3
        assert unmatched == sample_questions

    @pytest.mark.asyncio
    async def test_get_questions_for_template_stub(
        self, orchestrator_config, mock_telemetry, mock_similarity_strategy
    ):
        """Test the stub implementation of _get_questions_for_template."""
        orchestrator = PromptRetrievalOrchestrator(
            config=orchestrator_config,
            telemetry=mock_telemetry,
            similarity_strategy=mock_similarity_strategy,
        )
        
        result = await orchestrator._get_questions_for_template("test-123")
        
        # Stub implementation returns empty list
        assert result == []
        mock_telemetry.info.assert_called()

    @pytest.mark.asyncio
    async def test_write_matches_to_store_stub(
        self, orchestrator_config, mock_telemetry, mock_similarity_strategy, high_score_matches
    ):
        """Test the stub implementation of _write_matches_to_store."""
        orchestrator = PromptRetrievalOrchestrator(
            config=orchestrator_config,
            telemetry=mock_telemetry,
            similarity_strategy=mock_similarity_strategy,
        )
        
        await orchestrator._write_matches_to_store("test-123", high_score_matches)
        
        # Stub implementation just logs
        mock_telemetry.info.assert_called()


class TestOrchestratorIntegration:
    """Integration tests for orchestrator with multiple strategies."""

    @pytest.mark.asyncio
    async def test_full_orchestration_flow_with_all_strategies(
        self,
        orchestrator_config,
        mock_telemetry,
        mock_similarity_strategy,
        mock_passthrough_strategy,
        mock_dynamic_strategy,
        sample_questions
    ):
        """Test full orchestration flow using all three strategies."""
        # Configure to avoid passthrough clearing all questions
        orchestrator_config.fallback_to_passthrough = False
        orchestrator_config.fallback_to_dynamic = True
        orchestrator_config.enable_dynamic_prompt = True
        
        orchestrator = PromptRetrievalOrchestrator(
            config=orchestrator_config,
            telemetry=mock_telemetry,
            similarity_strategy=mock_similarity_strategy,
            passthrough_strategy=mock_passthrough_strategy,
            dynamic_strategy=mock_dynamic_strategy,
        )
        
        # Mock dependencies
        orchestrator._get_questions_for_template = AsyncMock(return_value=sample_questions)
        orchestrator._write_matches_to_store = AsyncMock()
        
        # Mock similarity strategy to partially match
        similarity_matches = [
            QuestionPromptMatch(
                question_id="q1",
                question_text="What is your age?",
                match_found=True,
                match_score=0.9,
                selected_prompt_text="Similarity matched prompt for age"
            )
        ]
        mock_similarity_strategy.retrieve_prompts = AsyncMock(
            return_value=PromptRetrievalOutput(
                assessment_template_id="test-template-123",
                results=similarity_matches
            )
        )
        
        # Mock dynamic strategy to handle remaining questions
        dynamic_matches = [
            QuestionPromptMatch(
                question_id="q2",
                question_text="Do you have diabetes?",
                match_found=True,
                selected_prompt_text="Dynamic generated prompt for diabetes"
            ),
            QuestionPromptMatch(
                question_id="q3",
                question_text="What medications are you taking?",
                match_found=True,
                selected_prompt_text="Dynamic generated prompt for medications"
            )
        ]
        mock_dynamic_strategy.retrieve_prompts = AsyncMock(
            return_value=PromptRetrievalOutput(
                assessment_template_id="test-template-123",
                results=dynamic_matches
            )
        )
        
        await orchestrator.retrieve_prompts("test-template-123")
        
        # Verify similarity and dynamic strategies were called
        mock_similarity_strategy.retrieve_prompts.assert_called_once()
        mock_passthrough_strategy.retrieve_prompts.assert_not_called()  # Disabled in config
        mock_dynamic_strategy.retrieve_prompts.assert_called_once()
        
        # Verify final results contain matches from similarity and dynamic strategies
        orchestrator._write_matches_to_store.assert_called_once()
        written_matches = orchestrator._write_matches_to_store.call_args[0][1]
        assert len(written_matches) == 3
        
        # Check that each strategy handled its expected questions
        question_ids = {match.question_id for match in written_matches}
        assert question_ids == {"q1", "q2", "q3"}

    @pytest.mark.asyncio
    async def test_orchestration_with_passthrough_then_dynamic(
        self,
        orchestrator_config,
        mock_telemetry,
        mock_similarity_strategy,
        mock_passthrough_strategy,
        mock_dynamic_strategy,
        sample_questions
    ):
        """Test orchestration flow where passthrough fails and dynamic strategy succeeds."""
        orchestrator = PromptRetrievalOrchestrator(
            config=orchestrator_config,
            telemetry=mock_telemetry,
            similarity_strategy=mock_similarity_strategy,
            passthrough_strategy=mock_passthrough_strategy,
            dynamic_strategy=mock_dynamic_strategy,
        )
        
        # Mock dependencies
        orchestrator._get_questions_for_template = AsyncMock(return_value=sample_questions)
        orchestrator._write_matches_to_store = AsyncMock()
        
        # Mock similarity strategy to return no matches
        mock_similarity_strategy.retrieve_prompts = AsyncMock(
            return_value=PromptRetrievalOutput(
                assessment_template_id="test-template-123",
                results=[]
            )
        )
        
        # Mock passthrough strategy to return empty results (no matches)
        mock_passthrough_strategy.retrieve_prompts = AsyncMock(
            return_value=PromptRetrievalOutput(
                assessment_template_id="test-template-123",
                results=[]  # Passthrough fails to generate results
            )
        )
        
        # Mock dynamic strategy to handle all remaining questions
        dynamic_matches = [
            QuestionPromptMatch(
                question_id="q1",
                question_text="What is your age?",
                match_found=True,
                selected_prompt_text="Dynamic generated prompt for age"
            ),
            QuestionPromptMatch(
                question_id="q2",
                question_text="Do you have diabetes?",
                match_found=True,
                selected_prompt_text="Dynamic generated prompt for diabetes"
            ),
            QuestionPromptMatch(
                question_id="q3",
                question_text="What medications are you taking?",
                match_found=True,
                selected_prompt_text="Dynamic generated prompt for medications"
            )
        ]
        mock_dynamic_strategy.retrieve_prompts = AsyncMock(
            return_value=PromptRetrievalOutput(
                assessment_template_id="test-template-123",
                results=dynamic_matches
            )
        )
        
        await orchestrator.retrieve_prompts("test-template-123")
        
        # Verify all strategies were called
        mock_similarity_strategy.retrieve_prompts.assert_called_once()
        mock_passthrough_strategy.retrieve_prompts.assert_called_once()
        mock_dynamic_strategy.retrieve_prompts.assert_called_once()
        
        # Verify final results contain matches from dynamic strategy only
        orchestrator._write_matches_to_store.assert_called_once()
        written_matches = orchestrator._write_matches_to_store.call_args[0][1]
        assert len(written_matches) == 3
        
        # Check that dynamic strategy handled all questions
        question_ids = {match.question_id for match in written_matches}
        assert question_ids == {"q1", "q2", "q3"}

    @pytest.mark.asyncio
    async def test_orchestration_flow_with_telemetry_tracking(
        self,
        orchestrator_config,
        mock_telemetry,
        mock_similarity_strategy,
        sample_questions,
        high_score_matches
    ):
        """Test that orchestration flow properly uses telemetry tracking."""
        orchestrator = PromptRetrievalOrchestrator(
            config=orchestrator_config,
            telemetry=mock_telemetry,
            similarity_strategy=mock_similarity_strategy,
        )
        
        # Mock dependencies
        orchestrator._get_questions_for_template = AsyncMock(return_value=sample_questions)
        orchestrator._write_matches_to_store = AsyncMock()
        
        # Mock similarity strategy
        mock_similarity_strategy.retrieve_prompts = AsyncMock(
            return_value=PromptRetrievalOutput(
                assessment_template_id="test-template-123",
                results=high_score_matches
            )
        )
        
        await orchestrator.retrieve_prompts("test-template-123")
        
        # Verify telemetry calls
        mock_telemetry.info.assert_called()
        mock_telemetry.start_span.assert_called_once_with(
            "orchestrator_retrieve_prompts",
            {"assessment_template_id": "test-template-123"}
        )
        mock_telemetry.record_matched_questions.assert_called_once_with("test-template-123", 2)
