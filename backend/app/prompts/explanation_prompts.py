from typing import Dict, Any

MATCH_EXPLANATION_SYSTEM_PROMPT = """You are an expert technical talent recruiter and candidate evaluator.
Your task is to produce a concise, honest, and highly specific explanation for why a candidate scored a specific match score for a job posting.

CRITICAL CONSTRAINTS & RULES:
1. GROUNDED IN PROVIDED DATA ONLY:
   - Base your explanation ONLY on the structured score data and skills provided in the prompt context.
   - DO NOT invent, hallucinate, or assume any skills, technologies, employment dates, or certifications not explicitly listed in the input data.

2. NO GENERIC FILLER OR FLUFF:
   - FORBIDDEN PHRASES: Do NOT use vague phrases like "strong candidate", "good fit", "excellent match", or "great potential" WITHOUT immediately backing them up with exact skill names or experience numbers.
   - Every claim must reference specific matched skills, missing skills, or exact numeric years of experience.

3. SCORE TONE CALIBRATION:
   - Your explanation MUST reflect the magnitude of the Final Score:
     * Score >= 80%: Enthusiastic and highlighting strong overlap, while noting any minor gaps.
     * Score 50% - 79%: Balanced tone, explicitly contrasting strong matched criteria with missing requirements.
     * Score < 50%: Direct and honest tone highlighting major skill gaps or experience shortfalls without false positivity.

4. STRUCTURED OUTPUT MANDATE:
   - You MUST respond using the `generate_candidate_explanation` tool call.
"""

MATCH_EXPLANATION_TOOL = {
    "name": "generate_candidate_explanation",
    "description": "Generates a structured, grounded explanation of candidate match results.",
    "input_schema": {
        "type": "object",
        "properties": {
            "summary": {
                "type": "string",
                "description": "Short paragraph (3-5 sentences) providing a grounded, specific overview of matched qualifications, skill gaps, and experience alignment."
            },
            "strengths": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of specific matched skills, experience alignment, and qualifications."
            },
            "gaps": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of missing required/preferred skills, experience shortfalls, or education mismatches."
            },
            "verdict": {
                "type": "string",
                "description": "A single-sentence overall match summary verdict."
            }
        },
        "required": ["summary", "strengths", "gaps", "verdict"]
    }
}


def build_explanation_user_prompt(
    candidate_name: str,
    job_title: str,
    final_score: float,
    hybrid_breakdown: Dict[str, Any]
) -> str:
    """
    Formats structured Phase 4 match evaluation data into a prompt context for LLM explanation generation.
    """
    skills_detail = hybrid_breakdown.get("breakdown", {}).get("skills", {})
    exp_detail = hybrid_breakdown.get("breakdown", {}).get("experience", {})
    edu_detail = hybrid_breakdown.get("breakdown", {}).get("education", {})

    matched_req = skills_detail.get("matched_required_skills", [])
    missing_req = skills_detail.get("missing_required_skills", [])
    matched_pref = skills_detail.get("matched_preferred_skills", [])
    missing_pref = skills_detail.get("missing_preferred_skills", [])

    cand_years = exp_detail.get("candidate_years", 0.0)
    req_years = exp_detail.get("required_years", 0.0)
    exp_status = exp_detail.get("status", "unknown")
    overqualified = exp_detail.get("overqualified_flag", False)

    cand_degrees = edu_detail.get("candidate_degrees", [])
    req_edu = edu_detail.get("required_education", "None")
    edu_status = edu_detail.get("status", "unknown")

    prompt = f"""Evaluate candidate '{candidate_name}' for the job position '{job_title}':

EVALUATION SCORES (Phase 4 Hybrid Engine Output):
- Final Overall Hybrid Score: {final_score}%
- Semantic Similarity Sub-score: {hybrid_breakdown.get('semantic_score', 0.0)}%
- Skill Overlap Sub-score: {hybrid_breakdown.get('skill_overlap_score', 0.0)}%
- Experience Match Sub-score: {hybrid_breakdown.get('experience_score', 0.0)}%
- Education Match Sub-score: {hybrid_breakdown.get('education_score', 0.0)}%

SKILL BREAKDOWN:
- Matched Required Skills: {', '.join(matched_req) if matched_req else 'None'}
- Missing Required Skills: {', '.join(missing_req) if missing_req else 'None'}
- Matched Preferred Skills: {', '.join(matched_pref) if matched_pref else 'None'}
- Missing Preferred Skills: {', '.join(missing_pref) if missing_pref else 'None'}

EXPERIENCE BREAKDOWN:
- Candidate Total Experience: {cand_years} years
- Job Minimum Required Experience: {req_years} years
- Experience Status: {exp_status} (Overqualified Flag: {overqualified})

EDUCATION BREAKDOWN:
- Candidate Degrees: {', '.join(cand_degrees) if cand_degrees else 'None listed'}
- Job Education Requirement: {req_edu}
- Education Status: {edu_status}

Instructions: Generate a structured match explanation (summary, strengths, gaps, verdict) strictly grounded in these exact facts.
"""
    return prompt
