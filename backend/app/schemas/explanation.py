from typing import List
from pydantic import BaseModel, Field


class CandidateExplanationSchema(BaseModel):
    summary: str = Field(
        ...,
        description="Concise paragraph (3 to 5 sentences) summarizing the candidate's match alignment, key matched skills, experience/education gaps, and suitability for the role."
    )
    strengths: List[str] = Field(
        default_factory=list,
        description="List of specific matched skills, experience highlights, and key strengths."
    )
    gaps: List[str] = Field(
        default_factory=list,
        description="List of missing required/preferred skills, experience shortfalls, or education mismatches."
    )
    verdict: str = Field(
        ...,
        description="One-line overall match summary verdict e.g. 'Strong match with 100% required skill coverage and 6 years backend experience.'"
    )
