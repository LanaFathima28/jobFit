import json
import logging
import re
from typing import Dict, Any, Tuple, List, Optional
from pydantic import ValidationError

import anthropic
import openai

from app.core.config import settings
from app.prompts.explanation_prompts import (
    MATCH_EXPLANATION_SYSTEM_PROMPT,
    MATCH_EXPLANATION_TOOL,
    build_explanation_user_prompt,
)
from app.schemas.explanation import CandidateExplanationSchema
from app.services.structured_extraction import (
    _call_claude_tool_use,
    _call_openai_tool_use,
)

logger = logging.getLogger(__name__)


def _validate_explanation_grounding(
    explanation_dict: Dict[str, Any],
    hybrid_breakdown: Dict[str, Any]
) -> List[str]:
    """
    Lightweight grounding validation check.
    Ensures that any tech skills mentioned in summary/strengths/gaps exist within the
    candidate's actual extracted skills or job requirements.
    Returns list of ungrounded skill warning strings (empty list if fully grounded).
    """
    skills_detail = hybrid_breakdown.get("breakdown", {}).get("skills", {})
    matched_req = skills_detail.get("matched_required_skills", [])
    missing_req = skills_detail.get("missing_required_skills", [])
    matched_pref = skills_detail.get("matched_preferred_skills", [])
    missing_pref = skills_detail.get("missing_preferred_skills", [])

    known_skills = set(
        [s.lower() for s in (matched_req + missing_req + matched_pref + missing_pref)]
    )

    combined_text = (
        explanation_dict.get("summary", "") + " " +
        " ".join(explanation_dict.get("strengths", [])) + " " +
        " ".join(explanation_dict.get("gaps", []))
    ).lower()

    # Common technical terms regex check if any unusual tech name appears
    warnings = []
    # If no known skills listed in prompt context, check if LLM hallucinated explicit tech stacks
    if not known_skills:
        # e.g., if candidate has 0 skills listed but summary names specific tech
        tech_matches = re.findall(r"\b(python|java|react|fastapi|docker|aws|c\+\+|sql|postgres|kubernetes)\b", combined_text)
        if tech_matches:
            warnings.append(f"Grounding Warning: Candidate has no listed skills, but explanation mentioned skills: {set(tech_matches)}")

    return warnings


def _generate_fallback_explanation(
    candidate_name: str,
    job_title: str,
    final_score: float,
    hybrid_breakdown: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Deterministic fallback explanation generator used if AI API calls fail or keys are unconfigured.
    """
    skills_detail = hybrid_breakdown.get("breakdown", {}).get("skills", {})
    exp_detail = hybrid_breakdown.get("breakdown", {}).get("experience", {})
    edu_detail = hybrid_breakdown.get("breakdown", {}).get("education", {})

    matched_req = skills_detail.get("matched_required_skills", [])
    missing_req = skills_detail.get("missing_required_skills", [])
    matched_pref = skills_detail.get("matched_preferred_skills", [])

    cand_years = exp_detail.get("candidate_years", 0.0)
    req_years = exp_detail.get("required_years", 0.0)

    strengths = []
    if matched_req:
        strengths.append(f"Matched required skills: {', '.join(matched_req)}")
    if matched_pref:
        strengths.append(f"Matched preferred skills: {', '.join(matched_pref)}")
    if cand_years >= req_years and req_years > 0:
        strengths.append(f"Meets or exceeds experience requirement with {cand_years} years (required {req_years} years)")

    gaps = []
    if missing_req:
        gaps.append(f"Missing required skills: {', '.join(missing_req)}")
    if cand_years < req_years:
        gaps.append(f"Underqualified in experience: has {cand_years} years vs. {req_years} years required")
    if edu_detail.get("status") == "below_requirement":
        gaps.append(f"Education degree level is below required: {edu_detail.get('required_education')}")

    if final_score >= 80.0:
        verdict = f"Excellent candidate match for {job_title} scoring {final_score}% overall."
    elif final_score >= 50.0:
        verdict = f"Moderate match scoring {final_score}% with balanced skill alignment."
    else:
        verdict = f"Low match scoring {final_score}% due to key skill and experience shortfalls."

    summary = (
        f"{candidate_name} scored {final_score}% overall for the {job_title} position. "
        f"Key matched skills include {', '.join(matched_req) if matched_req else 'none listed'}. "
        f"The candidate brings {cand_years} years of experience against a required {req_years} years."
    )

    return {
        "summary": summary,
        "strengths": strengths if strengths else ["No major skill matches recorded."],
        "gaps": gaps if gaps else ["No critical skill gaps identified."],
        "verdict": verdict
    }


def generate_candidate_explanation(
    candidate_name: str,
    job_title: str,
    final_score: float,
    hybrid_breakdown: Dict[str, Any]
) -> Tuple[Dict[str, Any], str, str]:
    """
    Generates a human-readable, grounded explanation of candidate match results using Claude
    (with OpenAI fallback), Pydantic validation, grounding check, and retry logic.

    Returns:
        (explanation_dict, status, raw_llm_output)
    """
    user_prompt = build_explanation_user_prompt(
        candidate_name=candidate_name,
        job_title=job_title,
        final_score=final_score,
        hybrid_breakdown=hybrid_breakdown
    )

    if not settings.ANTHROPIC_API_KEY and not settings.OPENAI_API_KEY:
        fallback = _generate_fallback_explanation(candidate_name, job_title, final_score, hybrid_breakdown)
        return fallback, "fallback", "No AI API keys configured. Used deterministic fallback generator."

    raw_llm_output = ""
    tool_input = {}

    # Attempt 1: Call LLM
    try:
        if settings.ANTHROPIC_API_KEY:
            raw_llm_output, tool_input = _call_claude_tool_use(
                MATCH_EXPLANATION_SYSTEM_PROMPT, user_prompt, MATCH_EXPLANATION_TOOL
            )
        elif settings.OPENAI_API_KEY:
            raw_llm_output, tool_input = _call_openai_tool_use(
                MATCH_EXPLANATION_SYSTEM_PROMPT, user_prompt, MATCH_EXPLANATION_TOOL
            )
    except Exception as api_err:
        logger.error(f"Explanation API call attempt 1 failed: {str(api_err)}")
        raw_llm_output = f"API Error: {str(api_err)}"

    # Attempt 1 Validation
    try:
        if tool_input:
            validated = CandidateExplanationSchema.model_validate(tool_input)
            explanation_dict = validated.model_dump()
            
            # Grounding validation check
            warnings = _validate_explanation_grounding(explanation_dict, hybrid_breakdown)
            if warnings:
                for w in warnings:
                    logger.warning(w)

            return explanation_dict, "success", raw_llm_output
    except ValidationError as val_err:
        logger.warning(f"Explanation attempt 1 validation error: {str(val_err)}. Retrying...")
        retry_prompt = f"{user_prompt}\n\n[SYSTEM NOTE: Previous output failed validation: {str(val_err)}. Please generate carefully.]"

        try:
            if settings.ANTHROPIC_API_KEY:
                raw_llm_2, tool_input_2 = _call_claude_tool_use(
                    MATCH_EXPLANATION_SYSTEM_PROMPT, retry_prompt, MATCH_EXPLANATION_TOOL
                )
            else:
                raw_llm_2, tool_input_2 = _call_openai_tool_use(
                    MATCH_EXPLANATION_SYSTEM_PROMPT, retry_prompt, MATCH_EXPLANATION_TOOL
                )

            validated_2 = CandidateExplanationSchema.model_validate(tool_input_2)
            explanation_dict = validated_2.model_dump()
            return explanation_dict, "success", f"Retry Output:\n{raw_llm_2}"
        except Exception as retry_err:
            logger.error(f"Explanation attempt 2 failed: {str(retry_err)}")

    # Fallback if AI call failed
    fallback = _generate_fallback_explanation(candidate_name, job_title, final_score, hybrid_breakdown)
    return fallback, "fallback", f"LLM explanation generation failed. Used fallback. Raw LLM: {raw_llm_output}"
