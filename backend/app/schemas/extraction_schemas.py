from typing import List, Optional
from pydantic import BaseModel, Field


class WorkExperience(BaseModel):
    title: str = Field(..., description="Job title or role e.g. Senior Software Engineer")
    company: str = Field(..., description="Company, organization, or employer name")
    start_date: Optional[str] = Field(None, description="Start date formatted as YYYY-MM or YYYY")
    end_date: Optional[str] = Field(None, description="End date formatted as YYYY-MM, YYYY, or Present")
    description: Optional[str] = Field(None, description="Summary of key duties, technologies used, and achievements")


class Education(BaseModel):
    degree: str = Field(..., description="Degree name e.g., Bachelor of Science, Master of Science, Ph.D.")
    institution: str = Field(..., description="University, college, or school name")
    field: Optional[str] = Field(None, description="Major, concentration, or field of study e.g., Computer Science")
    year: Optional[str] = Field(None, description="Graduation year or dates attended e.g., 2020")


class CandidateExtractionSchema(BaseModel):
    full_name: str = Field(..., description="Candidate's full name")
    email: Optional[str] = Field(None, description="Candidate's email address if available")
    phone: Optional[str] = Field(None, description="Candidate's phone number if available")
    total_years_experience: float = Field(
        0.0, description="Estimated total numeric years of work experience derived by summing distinct non-overlapping employment periods"
    )
    skills: List[str] = Field(default_factory=list, description="List of technical, analytical, and professional skills")
    work_history: List[WorkExperience] = Field(default_factory=list, description="Chronological list of work experience")
    education: List[Education] = Field(default_factory=list, description="Academic degrees and qualifications")
    certifications: List[str] = Field(default_factory=list, description="List of professional certifications, licenses, or credentials")


class JobExtractionSchema(BaseModel):
    job_title: str = Field(..., description="Official job title")
    required_skills: List[str] = Field(default_factory=list, description="Mandatory/required technical or soft skills")
    preferred_skills: List[str] = Field(default_factory=list, description="Nice-to-have or preferred skills")
    min_years_experience: float = Field(0.0, description="Minimum numeric years of work experience required")
    education_requirement: Optional[str] = Field(None, description="Education requirement e.g., Bachelor's Degree in Computer Science")
    responsibilities: List[str] = Field(default_factory=list, description="List of core job duties and responsibilities")
