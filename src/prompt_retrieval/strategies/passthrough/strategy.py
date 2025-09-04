"""
Passthrough prompt strategy implementation.

This strategy uses input questions directly as prompts with optional formatting.
"""


from ...common import (
    PromptRetrievalInput,
    PromptRetrievalOutput,
    PromptRetrievalStrategy,
    QuestionPromptMatch,
    TelemetryService,
)
from .config import PassthroughPromptConfig


class PassthroughPromptStrategy(PromptRetrievalStrategy):
    """
    Transforms questions directly into prompts using configurable formatting templates.
    Provides a reliable fallback when similarity search fails or returns low-quality matches.
    """
    
    def __init__(
        self,
        config: PassthroughPromptConfig,
        telemetry: TelemetryService,
    ) -> None:
        """Initialize the passthrough prompt strategy.
        
        Args:
            config: Configuration for question formatting
            telemetry: Telemetry service for logging and metrics
        """
        self._config = config
        self._logger = telemetry
        
    async def retrieve_prompts(self, request: PromptRetrievalInput) -> PromptRetrievalOutput:
        """Use questions directly as prompts with optional formatting.
        
        Args:
            request: Input containing questions to be used as prompts
            
        Returns:
            Output containing questions formatted as prompts
        """
        self._logger.info(
            "Starting passthrough prompt retrieval for assessment_template_id=%s with %d questions",
            request.assessment_template_id,
            len(request.questions),
        )
        
        with self._logger.start_span(
            "passthrough_retrieve_prompts",
            {"assessment_template_id": request.assessment_template_id, "question_count": len(request.questions)},
        ):
            matches: list[QuestionPromptMatch] = []
            
            for question in request.questions:
                self._logger.debug("Processing question_id=%s for passthrough formatting", question.question_id)
                
                try:
                    # Format the question as a prompt
                    prompt_text = self._format_question_as_prompt(question.question_text)
                    
                    match = QuestionPromptMatch(
                        question_id=question.question_id,
                        question_text=question.question_text,
                        match_found=True,
                        match_score=1.0,  # Always perfect match for passthrough
                        selected_prompt_text=prompt_text,
                    )
                    matches.append(match)
                    
                except Exception as ex:
                    self._logger.error("Error formatting question_id=%s: %s", question.question_id, ex)
                    # Return a match with error for this question
                    match = QuestionPromptMatch(
                        question_id=question.question_id,
                        question_text=question.question_text,
                        match_found=False,
                        error=str(ex),
                    )
                    matches.append(match)
        
        # Record metrics
        matched_count = sum(1 for match in matches if match.match_found)
        self._logger.record_matched_questions(request.assessment_template_id, matched_count)
        
        self._logger.info(
            "Finished passthrough prompt retrieval for assessment_template_id=%s (matched=%d/%d)",
            request.assessment_template_id, matched_count, len(matches)
        )
        
        return PromptRetrievalOutput(
            assessment_template_id=request.assessment_template_id,
            results=matches,
        )
    
    def _format_question_as_prompt(self, question_text: str) -> str:
        """Format a question as a prompt according to configuration.
        
        Args:
            question_text: The original question text
            
        Returns:
            Formatted prompt text
        """
        # Apply template formatting if configured
        if self._config.format_template:
            prompt_text = self._config.format_template.format(question=question_text)
        else:
            prompt_text = question_text
        
        # Add prefix if configured
        if self._config.prefix:
            prompt_text = f"{self._config.prefix} {prompt_text}"
        
        # Add suffix if configured
        if self._config.suffix:
            prompt_text = f"{prompt_text} {self._config.suffix}"
        
        return prompt_text
