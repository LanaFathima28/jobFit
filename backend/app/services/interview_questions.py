import json
import logging
import re
from typing import Dict, Any, Tuple, List, Optional
from pydantic import ValidationError

import anthropic
import openai

from app.core.config import settings
from app.prompts.interview_prompts import (
    INTERVIEW_QUESTIONS_SYSTEM_PROMPT,
    INTERVIEW_QUESTIONS_TOOL,
    build_interview_prompt,
)
from app.schemas.interview_schemas import InterviewQuestionsSchema
from app.services.structured_extraction import (
    _call_claude_tool_use,
    _call_openai_tool_use,
)

logger = logging.getLogger(__name__)


def _validate_interview_grounding(
    questions_dict: Dict[str, Any],
    candidate_structured_data: Dict[str, Any],
    job_structured_data: Dict[str, Any]
) -> List[str]:
    """
    Grounding validation check.
    Checks that company names or tech skills referenced in generated questions exist within the
    candidate's actual structured_data or job_structured_data.
    Returns list of warning messages (empty list if fully grounded).
    """
    warnings = []
    cand_skills = set(s.lower() for s in candidate_structured_data.get("skills", []))
    job_skills = set(s.lower() for s in job_structured_data.get("required_skills", []) + job_structured_data.get("preferred_skills", []))
    all_known_skills = cand_skills.union(job_skills)

    tech_questions = questions_dict.get("technical_questions", [])
    for q in tech_questions:
        target = q.get("target_skill", "").lower()
        if target and target not in all_known_skills and not any(target in s for s in all_known_skills):
            warnings.append(f"Grounding Warning: Technical question targeted '{q.get('target_skill')}' which is not in candidate or job skills.")

    gap_questions = questions_dict.get("gap_probing_questions", [])
    for q in gap_questions:
        target_gap = q.get("target_gap", "").lower()
        is_exp_or_learning = any(k in target_gap for k in ["experience", "years", "shortfall", "learning", "growth", "degree"])
        if target_gap and not is_exp_or_learning and target_gap not in all_known_skills and not any(target_gap in s for s in all_known_skills):
            warnings.append(f"Grounding Warning: Gap question targeted '{q.get('target_gap')}' which was not in job required/preferred skills.")

    return warnings



def _generate_fallback_interview_questions(
    candidate_name: str,
    job_title: str,
    candidate_structured_data: Dict[str, Any],
    job_structured_data: Dict[str, Any],
    hybrid_breakdown: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Deterministic fallback interview question generator used if AI API calls fail or keys are unconfigured.
    """
    cand_skills = candidate_structured_data.get("skills", [])
    work_history = candidate_structured_data.get("work_history", [])
    cand_years = candidate_structured_data.get("total_years_experience", 0.0)

    skills_detail = hybrid_breakdown.get("breakdown", {}).get("skills", {})
    exp_detail = hybrid_breakdown.get("breakdown", {}).get("experience", {})

    matched_req = skills_detail.get("matched_required_skills", [])
    missing_req = skills_detail.get("missing_required_skills", [])
    req_years = exp_detail.get("required_years", 0.0)

    # Technical Questions
    tech_questions = []
    if matched_req:
        primary_skill = matched_req[0]
        ref_company = work_history[0].get("company", "your recent role") if work_history and isinstance(work_history[0], dict) else "your experience"
        tech_questions.append({
            "question": f"Given your listed experience with {primary_skill} at {ref_company}, walk me through a major architecture or design decision you made using {primary_skill}.",
            "target_skill": primary_skill,
            "context_reference": f"{ref_company}"
        })
    if len(matched_req) > 1:
        second_skill = matched_req[1]
        tech_questions.append({
            "question": f"How have you handled performance optimization or complex troubleshooting when building production features with {second_skill}?",
            "target_skill": second_skill,
            "context_reference": "Claimed skills"
        })
    if not tech_questions:
        tech_questions.append({
            "question": f"Walk me through a technical project you engineered that best demonstrates your core software development capabilities.",
            "target_skill": cand_skills[0] if cand_skills else "Software Engineering",
            "context_reference": "General resume background"
        })

    # Behavioral Questions
    behavioral_questions = []
    if work_history and len(work_history) >= 2 and isinstance(work_history[0], dict) and isinstance(work_history[1], dict):
        recent_title = work_history[0].get("title", "role")
        prev_title = work_history[1].get("title", "previous role")
        behavioral_questions.append({
            "question": f"Reflecting on your transition from {prev_title} to {recent_title}, how did your technical responsibilities and leadership scope evolve?",
            "focus_area": f"Career progression from {prev_title} to {recent_title}"
        })
    else:
        behavioral_questions.append({
            "question": f"Describe a situation in your work history where you had to adapt quickly to changing technical requirements or project deadlines.",
            "focus_area": "Adaptability and project ownership"
        })

    behavioral_questions.append({
        "question": f"Tell me about a time you encountered a major technical disagreement with a team member or stakeholder and how you reached resolution.",
        "focus_area": "Technical collaboration and communication"
    })

    # Gap Probing Questions
    gap_questions = []
    if missing_req:
        for missing in missing_req[:2]:
            gap_questions.append({
                "question": f"We require {missing} for this role, which is not explicitly on your resume. Based on your background in {', '.join(cand_skills[:2]) if cand_skills else 'software engineering'}, how would you leverage your existing knowledge to ramp up quickly on {missing}?",
                "target_gap": missing,
                "probing_strategy": f"Assess transferable knowledge from {cand_skills[0] if cand_skills else 'existing skills'} to {missing}"
            })
    if cand_years < req_years:
        gap_questions.append({
            "question": f"This position requires {req_years} years of experience, and your background shows {cand_years} years. What accelerated project experiences or deep technical contributions demonstrate readiness for this level of responsibility?",
            "target_gap": f"Years of experience shortfall ({cand_years} vs. {req_years} required years)",
            "probing_strategy": "Assess project depth and technical maturity"
        })
    if not gap_questions:
        gap_questions.append({
            "question": f"What is a technical domain or tool relevant to {job_title} that you haven't mastered yet, and how do you plan to develop proficiency in it?",
            "target_gap": "Continuous learning & skill expansion",
            "probing_strategy": "Evaluate self-directed growth"
        })

    return {
        "technical_questions": tech_questions,
        "behavioral_questions": behavioral_questions,
        "gap_probing_questions": gap_questions
    }


def generate_interview_questions(
    candidate_name: str,
    job_title: str,
    candidate_structured_data: Dict[str, Any],
    job_structured_data: Dict[str, Any],
    hybrid_breakdown: Dict[str, Any]
) -> Tuple[Dict[str, Any], str, str]:
    """
    Generates candidate-specific, grounded interview questions using Claude (with OpenAI fallback),
    Pydantic validation, grounding check, and retry logic.

    Returns:
        (questions_dict, status, raw_llm_output)
    """
    user_prompt = build_interview_prompt(
        candidate_name=candidate_name,
        job_title=job_title,
        candidate_structured_data=candidate_structured_data,
        job_structured_data=job_structured_data,
        hybrid_breakdown=hybrid_breakdown
    )

    if not settings.ANTHROPIC_API_KEY and not settings.OPENAI_API_KEY:
        fallback = _generate_fallback_interview_questions(
            candidate_name, job_title, candidate_structured_data, job_structured_data, hybrid_breakdown
        )
        return fallback, "fallback", "No AI API keys configured. Used deterministic fallback question generator."

    raw_llm_output = ""
    tool_input = {}

    # Attempt 1: Call LLM
    try:
        if settings.ANTHROPIC_API_KEY:
            raw_llm_output, tool_input = _call_claude_tool_use(
                INTERVIEW_QUESTIONS_SYSTEM_PROMPT, user_prompt, INTERVIEW_QUESTIONS_TOOL
            )
        elif settings.OPENAI_API_KEY:
            raw_llm_output, tool_input = _call_openai_tool_use(
                INTERVIEW_QUESTIONS_SYSTEM_PROMPT, user_prompt, INTERVIEW_QUESTIONS_TOOL
            )
    except Exception as api_err:
        logger.error(f"Interview questions API call attempt 1 failed: {str(api_err)}")
        raw_llm_output = f"API Error: {str(api_err)}"

    # Attempt 1 Validation
    try:
        if tool_input:
            validated = InterviewQuestionsSchema.model_validate(tool_input)
            questions_dict = validated.model_dump()

            warnings = _validate_interview_grounding(questions_dict, candidate_structured_data, job_structured_data)
            if warnings:
                for w in warnings:
                    logger.warning(w)

            return questions_dict, "success", raw_llm_output
    except ValidationError as val_err:
        logger.warning(f"Interview questions attempt 1 validation error: {str(val_err)}. Retrying...")
        retry_prompt = f"{user_prompt}\n\n[SYSTEM NOTE: Previous tool call failed validation: {str(val_err)}. Please generate carefully.]"

        try:
            if settings.ANTHROPIC_API_KEY:
                raw_llm_2, tool_input_2 = _call_claude_tool_use(
                    INTERVIEW_QUESTIONS_SYSTEM_PROMPT, retry_prompt, INTERVIEW_QUESTIONS_TOOL
                )
            else:
                raw_llm_2, tool_input_2 = _call_openai_tool_use(
                    INTERVIEW_QUESTIONS_SYSTEM_PROMPT, retry_prompt, INTERVIEW_QUESTIONS_TOOL
                )

            validated_2 = InterviewQuestionsSchema.model_validate(tool_input_2)
            questions_dict = validated_2.model_dump()
            return questions_dict, "success", f"Retry Output:\n{raw_llm_2}"
        except Exception as retry_err:
            logger.error(f"Interview questions attempt 2 failed: {str(retry_err)}")

    # Fallback if AI call failed
    fallback = _generate_fallback_interview_questions(
        candidate_name, job_title, candidate_structured_data, job_structured_data, hybrid_breakdown
    )
    return fallback, "fallback", f"LLM question generation failed. Used fallback. Raw LLM: {raw_llm_output}"
