"""
Example strategy implementation template.
"""

import asyncio
import logging
from typing import List, Optional

from ...common import (
    PromptRetrievalInput,
    PromptRetrievalOutput, 
    QuestionInput,
    QuestionPromptMatch,
    PromptRetrievalStrategy,
    TelemetryService,
)
from .config import ExampleStrategyConfig


class ExamplePromptStrategy(PromptRetrievalStrategy):
    """
    Example implementation of a prompt retrieval strategy.
    
    Replace this with your actual strategy implementation.
    """
    
    def __init__(
        self,
        config: ExampleStrategyConfig,
        telemetry: TelemetryService,
        max_parallel_requests: int = 5,
    ) -> None:
        self._config = config
        self._logger = telemetry
        self._semaphore = asyncio.Semaphore(max_parallel_requests)
        
        # Initialize your strategy-specific components here
        # e.g., HTTP clients, AI clients, database connections, etc.
    
    async def retrieve_prompts(self, request: PromptRetrievalInput) -> PromptRetrievalOutput:
        """
        Retrieve prompts for the given questions.
        
        Args:
            request: Input containing questions to find prompts for
            
        Returns:
            Output containing prompt matches for each question
        """
        self._logger.info(
            "Starting prompt retrieval for assessment_template_id=%s with %d questions",
            request.assessment_template_id,
            len(request.questions),
        )
        
        # Process questions in parallel with semaphore for concurrency control
        tasks = [
            self._process_question(q) 
            for q in request.questions
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions and convert to QuestionPromptMatch objects
        prompt_matches = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # Log error and create error result
                question = request.questions[i]
                self._logger.error(
                    "Error processing question_id=%s: %s", 
                    question.question_id, 
                    str(result)
                )
                prompt_matches.append(
                    QuestionPromptMatch(
                        question_id=question.question_id,
                        question_text=question.question_text,
                        match_found=False,
                        match_score=None,
                        selected_prompt_text=None,
                        error=f"Processing error: {result}",
                    )
                )
            else:
                prompt_matches.append(result)
        
        return PromptRetrievalOutput(
            assessment_template_id=request.assessment_template_id,
            results=prompt_matches,
        )
    
    async def _process_question(self, question: QuestionInput) -> QuestionPromptMatch:
        """
        Process a single question to find the best prompt match.
        
        Args:
            question: The question to find a prompt for
            
        Returns:
            The best prompt match for the question
        """
        async with self._semaphore:
            try:
                # TODO: Implement your strategy logic here
                # This is where you would:
                # 1. Call your AI service/database/API
                # 2. Process the question text
                # 3. Find matching prompts
                # 4. Score the matches
                # 5. Return the best match
                
                # Example placeholder implementation:
                # (Replace this with your actual logic)
                return QuestionPromptMatch(
                    question_id=question.question_id,
                    question_text=question.question_text,
                    match_found=False,  # Set to True when you find a match
                    match_score=None,   # Set to actual similarity score
                    selected_prompt_text=None,  # Set to the matched prompt text
                    error=None,
                )
                
            except Exception as e:
                self._logger.error(
                    "Exception processing question_id=%s: %s",
                    question.question_id,
                    str(e)
                )
                return QuestionPromptMatch(
                    question_id=question.question_id,
                    question_text=question.question_text,
                    match_found=False,
                    match_score=None,
                    selected_prompt_text=None,
                    error=f"Strategy error: {e}",
                )
