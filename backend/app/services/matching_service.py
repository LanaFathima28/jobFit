import json
import logging
from typing import Dict, Any, Tuple, List
import numpy as np
import anthropic
import openai
from app.core.config import settings

logger = logging.getLogger(__name__)


def calculate_semantic_similarity(
    candidate_vector: List[float], job_vector: List[float]
) -> float:
    """
    Calculate cosine similarity score between candidate and job embeddings (normalized to 0-100%).
    """
    if not candidate_vector or not job_vector:
        return 50.0

    v1 = np.array(candidate_vector)
    v2 = np.array(job_vector)

    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)

    if norm1 == 0 or norm2 == 0:
        return 50.0

    similarity = np.dot(v1, v2) / (norm1 * norm2)
    # Cosine similarity is usually in [-1, 1], scale to [0, 100]
    scaled_score = max(0.0, min(100.0, float((similarity + 1.0) / 2.0 * 100.0)))
    return round(scaled_score, 2)


def calculate_rule_based_similarity(
    candidate_skills: List[str],
    job_skills: List[str],
    candidate_exp_years: int = 0,
    job_min_exp_years: int = 0
) -> float:
    """
    Calculate rule-based match score based on skill overlaps and experience thresholds.
    """
    if not job_skills:
        return 75.0

    cand_skills_lower = {s.lower().strip() for s in candidate_skills if s}
    job_skills_lower = {s.lower().strip() for s in job_skills if s}

    matching_skills = cand_skills_lower.intersection(job_skills_lower)
    
    # Partial fuzzy match score
    fuzzy_matches = 0
    for js in job_skills_lower:
        if js not in matching_skills:
            if any(js in cs or cs in js for cs in cand_skills_lower):
                fuzzy_matches += 0.5

    skill_ratio = (len(matching_skills) + fuzzy_matches) / len(job_skills_lower)
    skill_score = min(1.0, skill_ratio) * 80.0  # Skills contribute up to 80%

    # Experience penalty or bonus up to 20%
    exp_score = 20.0
    if job_min_exp_years > 0:
        if candidate_exp_years >= job_min_exp_years:
            exp_score = 20.0
        else:
            exp_score = max(0.0, (candidate_exp_years / job_min_exp_years) * 20.0)

    total_rule_score = round(min(100.0, skill_score + exp_score), 2)
    return total_rule_score


def generate_match_explanation(
    candidate_name: str,
    candidate_data: Dict[str, Any],
    job_title: str,
    job_data: Dict[str, Any],
    semantic_score: float,
    rule_score: float,
    final_score: float
) -> str:
    """
    Use Claude or OpenAI to generate an executive fit breakdown and explanation.
    """
    prompt = f"""Generate a concise executive match assessment (3-4 bullet points / short paragraph) evaluating Candidate "{candidate_name}" for the role of "{job_title}".

Scores:
- Semantic Alignment: {semantic_score}%
- Skill/Requirements Rule Match: {rule_score}%
- Combined Hybrid Fit Score: {final_score}%

Candidate Profile:
{json.dumps(candidate_data, indent=2)[:1500]}

Job Description / Requirements:
{json.dumps(job_data, indent=2)[:1500]}

Include:
1. Key strengths & matching skills.
2. Missing skills or experience gaps.
3. Final hiring recommendation (Strong Fit, Moderate Fit, or Potential Risk).
Keep response under 200 words. No intro fluff.
"""

    if settings.ANTHROPIC_API_KEY:
        try:
            client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
            response = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=350,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text.strip()
        except Exception as e:
            logger.warning(f"Claude explanation generation failed: {str(e)}")

    if settings.OPENAI_API_KEY:
        try:
            client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=350
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.warning(f"OpenAI explanation generation failed: {str(e)}")

    # Fallback explanation if API keys missing
    cand_skills = candidate_data.get("skills", [])
    job_skills = job_data.get("skills", [])
    matched = [s for s in cand_skills if s in job_skills]
    missing = [s for s in job_skills if s not in cand_skills]

    return f"Match Score: {final_score}%. Matched skills: {', '.join(matched) if matched else 'General fit'}. Missing skills: {', '.join(missing) if missing else 'None detected'}. Semantic similarity alignment evaluated at {semantic_score}%."
