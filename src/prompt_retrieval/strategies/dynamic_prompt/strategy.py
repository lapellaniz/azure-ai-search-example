"""
Dynamic prompt generation strategy implementation.

This strategy uses AI models to dynamically generate prompts based on input questions.
"""


from ...common import (
    PromptRetrievalInput,
    PromptRetrievalOutput,
    PromptRetrievalStrategy,
    QuestionPromptMatch,
    TelemetryService,
)
from .config import DynamicPromptConfig


class DynamicPromptStrategy(PromptRetrievalStrategy):
    """
    Generates contextually relevant prompts using AI models based on question analysis.
    Enables adaptive prompt creation when pre-existing prompts are insufficient or unavailable.
    """
    
    def __init__(
        self,
        config: DynamicPromptConfig,
        telemetry: TelemetryService,
    ) -> None:
        """Initialize the dynamic prompt strategy.
        
        Args:
            config: Configuration for the AI model and prompt generation
            telemetry: Telemetry service for logging and metrics
        """
        self._config = config
        self._logger = telemetry
        
    async def retrieve_prompts(self, request: PromptRetrievalInput) -> PromptRetrievalOutput:
        """Generate prompts dynamically for the given questions.
        
        Args:
            request: Input containing questions for which to generate prompts
            
        Returns:
            Output containing generated prompts for each question
        """
        self._logger.info(
            "Starting dynamic prompt generation for assessment_template_id=%s with %d questions",
            request.assessment_template_id,
            len(request.questions),
        )
        
        with self._logger.start_span(
            "dynamic_prompt_retrieve_prompts",
            {"assessment_template_id": request.assessment_template_id, "question_count": len(request.questions)},
        ):
            # TODO: Implement dynamic prompt generation using AI model
            # This should:
            # 1. Connect to AI service (OpenAI/Azure OpenAI)
            # 2. For each question, generate a relevant prompt using the model
            # 3. Apply prompt engineering techniques (system prompts, templates)
            # 4. Return generated prompts with appropriate metadata
            
            matches: list[QuestionPromptMatch] = []
            
            for question in request.questions:
                self._logger.debug("Generating dynamic prompt for question_id=%s", question.question_id)
                
                try:
                    # Placeholder implementation - replace with actual AI generation
                    generated_prompt = f"[AI-Generated] Please provide a comprehensive response to: {question.question_text}"
                    
                    match = QuestionPromptMatch(
                        question_id=question.question_id,
                        question_text=question.question_text,
                        match_found=True,
                        match_score=1.0,  # Always perfect match for generated prompts
                        selected_prompt_text=generated_prompt,
                    )
                    matches.append(match)
                    
                except Exception as ex:
                    self._logger.error("Error generating prompt for question_id=%s: %s", question.question_id, ex)
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
            "Finished dynamic prompt generation for assessment_template_id=%s (matched=%d/%d)",
            request.assessment_template_id, matched_count, len(matches)
        )
        
        return PromptRetrievalOutput(
            assessment_template_id=request.assessment_template_id,
            results=matches,
        )
