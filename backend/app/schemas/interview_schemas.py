from typing import List, Optional
from pydantic import BaseModel, Field


class TechnicalQuestionItem(BaseModel):
    question: str = Field(
        ...,
        description="Detailed technical question probing candidate's claimed skills in the context of their actual work experience."
    )
    target_skill: str = Field(
        ...,
        description="The specific technical skill or technology being probed e.g. PostgreSQL, FastAPI."
    )
    context_reference: Optional[str] = Field(
        None,
        description="Reference to candidate's listed experience or company e.g. 'Backend Engineer role at TechCorp'."
    )


class BehavioralQuestionItem(BaseModel):
    question: str = Field(
        ...,
        description="Behavioral question probing role transitions, scope growth, team leadership, or career progression."
    )
    focus_area: Optional[str] = Field(
        None,
        description="Key focus area e.g. 'Seniority transition from Lead to Principal Engineer'."
    )


class GapProbingQuestionItem(BaseModel):
    question: str = Field(
        ...,
        description="Question probing adjacent/transferable knowledge targeting a missing required skill or experience shortfall."
    )
    target_gap: str = Field(
        ...,
        description="The missing skill or experience gap from Phase 4 e.g. 'AWS Cloud Infrastructure'."
    )
    probing_strategy: Optional[str] = Field(
        None,
        description="Strategy for assessing transferable knowledge e.g. 'Assess transferable container deployment experience from Docker/Linux'."
    )


class InterviewQuestionsSchema(BaseModel):
    technical_questions: List[TechnicalQuestionItem] = Field(
        default_factory=list,
        description="List of 2 to 3 candidate-specific technical deep-dive questions."
    )
    behavioral_questions: List[BehavioralQuestionItem] = Field(
        default_factory=list,
        description="List of 2 to 3 career progression and behavioral questions."
    )
    gap_probing_questions: List[GapProbingQuestionItem] = Field(
        default_factory=list,
        description="List of 2 to 3 gap probing questions targeting missing requirements via transferable skills."
    )
