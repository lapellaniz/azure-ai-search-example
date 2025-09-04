"""
Orchestrator for coordinating multiple prompt retrieval strategies.

This module provides an orchestrator that coordinates between different strategies
to provide the best possible prompt retrieval experience.
"""


from ..common import (
    PromptRetrievalInput,
    PromptRetrievalOutput,
    QuestionInput,
    QuestionPromptMatch,
    TelemetryService,
)
from ..strategies.dynamic_prompt import DynamicPromptStrategy
from ..strategies.passthrough import PassthroughPromptStrategy
from ..strategies.similarity_search import SimilaritySearchPromptStrategy
from .config import OrchestratorConfig


class PromptRetrievalOrchestrator:
    """Orchestrator that coordinates multiple prompt retrieval strategies."""
    
    def __init__(
        self,
        config: OrchestratorConfig,
        telemetry: TelemetryService,
        similarity_strategy: SimilaritySearchPromptStrategy,
        passthrough_strategy: PassthroughPromptStrategy | None = None,
        dynamic_strategy: DynamicPromptStrategy | None = None,
    ) -> None:
        """Initialize the orchestrator with injected strategies.
        
        Args:
            config: Configuration for orchestration behavior
            telemetry: Telemetry service for logging and metrics
            similarity_strategy: Required similarity search strategy
            passthrough_strategy: Optional passthrough strategy
            dynamic_strategy: Optional dynamic prompt generation strategy
        """
        self._config = config
        self._logger = telemetry
        
        # Use injected strategies
        self._similarity_strategy = similarity_strategy
        self._passthrough_strategy = passthrough_strategy
        self._dynamic_strategy = dynamic_strategy
    
    async def retrieve_prompts(self, assessment_template_id: str) -> None:
        """Orchestrate prompt retrieval for all questions in an assessment template.
        
        The orchestration flow:
        1. Retrieve questions for the assessment template
        2. Try similarity search first
        3. For unmatched questions, try passthrough (if enabled)
        4. For still unmatched questions, try dynamic prompt (if enabled)
        5. Write all results to data store
        
        Args:
            assessment_template_id: ID of the assessment template to process
        """
        self._logger.info("Orchestrator starting prompt retrieval for assessment_template_id=%s", assessment_template_id)
        
        with self._logger.start_span(
            "orchestrator_retrieve_prompts",
            {"assessment_template_id": assessment_template_id},
        ):
            # Step 0: Get questions for this assessment template
            questions = await self._get_questions_for_template(assessment_template_id)
            if not questions:
                self._logger.warning("No questions found for assessment_template_id=%s", assessment_template_id)
                return
            
            self._logger.info("Retrieved %d questions for assessment_template_id=%s", len(questions), assessment_template_id)
            
            # Create internal request object for processing
            request = PromptRetrievalInput(
                assessment_template_id=assessment_template_id,
                questions=questions
            )
            
            all_results: list[QuestionPromptMatch] = []
            unmatched_questions: list[QuestionInput] = list(questions)
            strategy_usage = {"similarity": 0, "passthrough": 0, "dynamic": 0}
            
            # Step 1: Try similarity search
            if unmatched_questions:
                self._logger.debug("Attempting similarity search for %d questions", len(unmatched_questions))
                similarity_result = await self._try_similarity_search(request, unmatched_questions)
                matched_questions, remaining_questions = self._process_similarity_results(
                    similarity_result, unmatched_questions
                )
                all_results.extend(matched_questions)
                unmatched_questions = remaining_questions
                strategy_usage["similarity"] = len(matched_questions)
                
                self._logger.info("Similarity search matched %d questions, %d remaining for assessment_template_id=%s",
                                len(matched_questions), len(unmatched_questions), assessment_template_id)
            
            # Step 2: Try passthrough for unmatched questions
            if unmatched_questions and self._config.fallback_to_passthrough and self._passthrough_strategy:
                self._logger.debug("Attempting passthrough for %d remaining questions", len(unmatched_questions))
                passthrough_result = await self._try_passthrough(request, unmatched_questions)
                if passthrough_result.results:
                    all_results.extend(passthrough_result.results)
                    strategy_usage["passthrough"] = len(passthrough_result.results)
                    unmatched_questions = []  # Passthrough handles all remaining questions
                    
                    self._logger.info("Passthrough handled %d questions for assessment_template_id=%s", 
                                    len(passthrough_result.results), assessment_template_id)
            
            # Step 3: Try dynamic prompt for still unmatched questions (if enabled)
            if (unmatched_questions and 
                self._config.enable_dynamic_prompt and 
                self._config.fallback_to_dynamic and 
                self._dynamic_strategy):
                
                self._logger.debug("Attempting dynamic prompt generation for %d remaining questions", len(unmatched_questions))
                dynamic_result = await self._try_dynamic_prompt(request, unmatched_questions)
                if dynamic_result.results:
                    all_results.extend(dynamic_result.results)
                    strategy_usage["dynamic"] = len(dynamic_result.results)
                    unmatched_questions = []  # Dynamic prompt handles all remaining questions
                    
                    self._logger.info("Dynamic prompt handled %d questions for assessment_template_id=%s", 
                                    len(dynamic_result.results), assessment_template_id)
            
            # Report any completely unmatched questions
            if unmatched_questions:
                unmatched_ids = [q.question_id for q in unmatched_questions]
                self._logger.warning("%d questions could not be matched by any strategy for assessment_template_id=%s: %s",
                                   len(unmatched_questions), assessment_template_id, unmatched_ids)
            
            # Step 4: Write results to data store
            if all_results:
                await self._write_matches_to_store(assessment_template_id, all_results)
                total_matches = sum(1 for result in all_results if result.match_found)
                self._logger.record_matched_questions(assessment_template_id, total_matches)
                self._logger.info("Orchestrator completed: wrote %d matches (%d successful) to data store for assessment_template_id=%s "
                                "using strategies: similarity=%d, passthrough=%d, dynamic=%d",
                                len(all_results), total_matches, assessment_template_id,
                                strategy_usage["similarity"], strategy_usage["passthrough"], strategy_usage["dynamic"])
            else:
                self._logger.warning("No matches generated for assessment_template_id=%s", assessment_template_id)
    
    async def _try_similarity_search(
        self, 
        request: PromptRetrievalInput, 
        questions: list[QuestionInput]
    ) -> PromptRetrievalOutput:
        """Try similarity search for the given questions."""
        similarity_request = PromptRetrievalInput(
            assessment_template_id=request.assessment_template_id,
            questions=questions
        )
        
        try:
            return await self._similarity_strategy.retrieve_prompts(similarity_request)
        except Exception as e:
            self._logger.error("Similarity search failed for assessment_template_id=%s: %s", 
                             request.assessment_template_id, e)
            self._logger.exception("Similarity search exception details")
            return PromptRetrievalOutput(
                assessment_template_id=request.assessment_template_id,
                results=[],
            )
    
    async def _try_passthrough(
        self, 
        request: PromptRetrievalInput, 
        questions: list[QuestionInput]
    ) -> PromptRetrievalOutput:
        """Try passthrough strategy for the given questions."""
        passthrough_request = PromptRetrievalInput(
            assessment_template_id=request.assessment_template_id,
            questions=questions
        )
        
        try:
            return await self._passthrough_strategy.retrieve_prompts(passthrough_request)
        except Exception as e:
            self._logger.error("Passthrough strategy failed for assessment_template_id=%s: %s", 
                             request.assessment_template_id, e)
            self._logger.exception("Passthrough strategy exception details")
            return PromptRetrievalOutput(
                assessment_template_id=request.assessment_template_id,
                results=[],
            )
    
    async def _try_dynamic_prompt(
        self, 
        request: PromptRetrievalInput, 
        questions: list[QuestionInput]
    ) -> PromptRetrievalOutput:
        """Try dynamic prompt strategy for the given questions."""
        dynamic_request = PromptRetrievalInput(
            assessment_template_id=request.assessment_template_id,
            questions=questions
        )
        
        try:
            return await self._dynamic_strategy.retrieve_prompts(dynamic_request)
        except Exception as e:
            self._logger.error("Dynamic prompt strategy failed for assessment_template_id=%s: %s", 
                             request.assessment_template_id, e)
            self._logger.exception("Dynamic prompt strategy exception details")
            return PromptRetrievalOutput(
                assessment_template_id=request.assessment_template_id,
                results=[],
            )
    
    def _process_similarity_results(
        self, 
        result: PromptRetrievalOutput, 
        original_questions: list[QuestionInput]
    ) -> tuple[list[QuestionPromptMatch], list[QuestionInput]]:
        """Process similarity search results and identify unmatched questions.
        
        Args:
            result: Result from similarity search
            original_questions: Original list of questions that were searched
            
        Returns:
            Tuple of (matched_questions, unmatched_questions)
        """
        if not result.results:
            return [], original_questions
        
        # Find matches that meet the threshold
        good_matches = [
            match for match in result.results 
            if match.match_found and match.match_score and match.match_score >= self._config.similarity_threshold
        ]
        
        # Identify which questions were successfully matched
        matched_question_ids: set[str] = {match.question_id for match in good_matches}
        
        # Find questions that weren't matched or didn't meet threshold
        unmatched_questions = [
            q for q in original_questions 
            if q.question_id not in matched_question_ids
        ]
        
        return good_matches, unmatched_questions
    
    async def _get_questions_for_template(self, assessment_template_id: str) -> list[QuestionInput]:
        """Retrieve questions for the given assessment template ID.
        
        Args:
            assessment_template_id: ID of the assessment template
            
        Returns:
            List of questions for the template
        """
        # TODO: Implement retrieval from data store/database
        # This should query the assessment template service/database to get
        # all questions associated with the given template ID
        
        self._logger.info(f"Retrieving questions for template {assessment_template_id} (stub implementation)")
        
        # Stub implementation - return empty list
        return []
    
    async def _write_matches_to_store(self, assessment_template_id: str, matches: list[QuestionPromptMatch]) -> None:
        """Write prompt matches to the data store.
        
        Args:
            assessment_template_id: ID of the assessment template
            matches: List of question-prompt matches to store
        """
        # TODO: Implement writing to data store/database
        # This should persist the matches to a database or other storage system
        # for later retrieval and use by other services
        
        self._logger.info(f"Writing {len(matches)} matches for template {assessment_template_id} to data store (stub implementation)")
        
        # Stub implementation - no actual storage
        pass
