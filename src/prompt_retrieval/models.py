
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass(frozen=True)
class QuestionInput:
    question_id: str
    question_text: str


@dataclass(frozen=True)
class PromptRetrievalInput:
    assessment_template_id: str
    questions: List[QuestionInput]


@dataclass
class QuestionPromptMatch:
    question_id: str
    question_text: str
    match_found: bool
    match_score: Optional[float] = None
    selected_prompt_text: Optional[str] = None
    error: Optional[str] = None


@dataclass
class PromptRetrievalOutput:
    assessment_template_id: str
    results: List[QuestionPromptMatch] = field(default_factory=list)
