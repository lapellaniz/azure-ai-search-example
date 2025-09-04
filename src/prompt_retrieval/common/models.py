
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class QuestionInput:
    question_id: str
    question_text: str


@dataclass(frozen=True)
class PromptRetrievalInput:
    assessment_template_id: str
    questions: list[QuestionInput]


@dataclass
class QuestionPromptMatch:
    question_id: str
    question_text: str
    match_found: bool
    match_score: float | None = None
    selected_prompt_text: str | None = None
    error: str | None = None


@dataclass
class PromptRetrievalOutput:
    assessment_template_id: str
    results: list[QuestionPromptMatch] = field(default_factory=list)
