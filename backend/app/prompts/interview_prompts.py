from typing import Dict, Any, List

INTERVIEW_QUESTIONS_SYSTEM_PROMPT = """You are an expert technical interviewer and engineering hiring manager.
Your task is to generate a set of highly tailored, candidate-specific interview questions grounded in the candidate's actual resume history and the target job requirements.

CRITICAL CONSTRAINTS & RULES:
1. STRICT CANDIDATE GROUNDING:
   - Ground every technical question in the candidate's actual listed skills, past employer names, or project details.
   - Ground behavioral questions in their actual career trajectory (role transitions, tenure, seniority changes).
   - Ground gap probing questions directly in the missing required skills and experience shortfalls from Phase 4 scoring.

2. FORBIDDEN GENERIC TRIVIA / FAILURE CASES:
   - STRICTLY FORBIDDEN: Generic resume-agnostic questions like "Tell me about yourself", "What are your strengths and weaknesses", or "Explain REST APIs".
   - Every question must be candidate-specific and unusable for a different candidate.

3. GAP PROBING REQUIREMENT (TRANSFERABLE EXPERIENCE):
   - Do NOT ask trivial binary pass/fail questions for missing skills (e.g., FORBIDDEN: "Do you know AWS?").
   - Instead, assess ADJACENT/TRANSFERABLE knowledge. Ask how they would leverage their existing background (e.g. Docker, Linux, on-prem PostgreSQL) to get up to speed or design solutions using the missing skill (e.g. AWS).

4. CATEGORIES REQUIRED:
   - Technical Questions (2-3): Candidate-specific technical deep-dives referencing actual companies/projects.
   - Behavioral Questions (2-3): Career progression, transitions, or seniority growth.
   - Gap Probing Questions (2-3): Transferable experience assessment targeting missing skills.

5. STRUCTURED OUTPUT MANDATE:
   - You MUST respond using the `generate_interview_questions` tool call.
"""

INTERVIEW_QUESTIONS_TOOL = {
    "name": "generate_interview_questions",
    "description": "Generates a structured set of tailored, grounded candidate interview questions.",
    "input_schema": {
        "type": "object",
        "properties": {
            "technical_questions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "question": {"type": "string", "description": "Candidate-specific technical question."},
                        "target_skill": {"type": "string", "description": "Target skill being probed."},
                        "context_reference": {"type": "string", "description": "Reference to candidate's work history or company."}
                    },
                    "required": ["question", "target_skill"]
                },
                "description": "List of 2 to 3 candidate-specific technical questions."
            },
            "behavioral_questions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "question": {"type": "string", "description": "Candidate-specific behavioral question."},
                        "focus_area": {"type": "string", "description": "Career trajectory or transition focus area."}
                    },
                    "required": ["question"]
                },
                "description": "List of 2 to 3 behavioral and career trajectory questions."
            },
            "gap_probing_questions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "question": {"type": "string", "description": "Question assessing transferable knowledge for a missing skill."},
                        "target_gap": {"type": "string", "description": "Missing skill or experience gap."},
                        "probing_strategy": {"type": "string", "description": "Transferable knowledge assessment strategy."}
                    },
                    "required": ["question", "target_gap"]
                },
                "description": "List of 2 to 3 gap-probing questions assessing transferable skills."
            }
        },
        "required": ["technical_questions", "behavioral_questions", "gap_probing_questions"]
    }
}


def build_interview_prompt(
    candidate_name: str,
    job_title: str,
    candidate_structured_data: Dict[str, Any],
    job_structured_data: Dict[str, Any],
    hybrid_breakdown: Dict[str, Any]
) -> str:
    """
    Formats candidate resume profile, job criteria, and Phase 4 match gaps into context for LLM question generation.
    """
    cand_skills = candidate_structured_data.get("skills", [])
    work_history = candidate_structured_data.get("work_history", [])
    education = candidate_structured_data.get("education", [])
    cand_exp = candidate_structured_data.get("total_years_experience", 0.0)

    job_req_skills = job_structured_data.get("required_skills", [])
    job_min_exp = job_structured_data.get("min_years_experience", 0.0)
    job_resp = job_structured_data.get("responsibilities", [])

    skills_detail = hybrid_breakdown.get("breakdown", {}).get("skills", {})
    exp_detail = hybrid_breakdown.get("breakdown", {}).get("experience", {})

    matched_req = skills_detail.get("matched_required_skills", [])
    missing_req = skills_detail.get("missing_required_skills", [])
    missing_pref = skills_detail.get("missing_preferred_skills", [])

    # Format work history snippet
    history_snippets = []
    for wh in work_history[:4]:
        if isinstance(wh, dict):
            title = wh.get("title", "Role")
            company = wh.get("company", "Company")
            dates = f"{wh.get('start_date', '')} - {wh.get('end_date', '')}"
            desc = wh.get("description", "")
            history_snippets.append(f"- {title} at {company} ({dates}): {desc[:150]}")

    history_str = "\n".join(history_snippets) if history_snippets else "No explicit work history entries listed."

    prompt = f"""Generate tailored interview questions for candidate '{candidate_name}' applying for '{job_title}':

CANDIDATE PROFILE:
- Claimed Skills: {', '.join(cand_skills) if cand_skills else 'None listed'}
- Total Numeric Experience: {cand_exp} years
- Work History Summary:
{history_str}

JOB REQUIREMENTS:
- Required Skills: {', '.join(job_req_skills) if job_req_skills else 'None listed'}
- Minimum Required Experience: {job_min_exp} years
- Core Responsibilities: {', '.join(job_resp[:3]) if job_resp else 'Standard engineering duties'}

PHASE 4 MATCH EVALUATION & GAPS:
- Matched Required Skills: {', '.join(matched_req) if matched_req else 'None'}
- MISSING Required Skills: {', '.join(missing_req) if missing_req else 'None'}
- MISSING Preferred Skills: {', '.join(missing_pref) if missing_pref else 'None'}
- Experience Status: {exp_detail.get('status', 'qualified')} (Candidate: {cand_exp} yrs vs. Required: {job_min_exp} yrs)

Generate 2-3 Technical Questions, 2-3 Behavioral Questions, and 2-3 Gap Probing Questions strictly following the rules.
"""
    return prompt
