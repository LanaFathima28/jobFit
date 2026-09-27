import re
from typing import List, Dict, Any, Tuple, Optional
from app.services.skill_normalizer import normalize_skill, normalize_skills

# Degree Hierarchy mapping
DEGREE_LEVELS = {
    "doctorate": 4, "phd": 4, "ph.d.": 4, "doctoral": 4,
    "master": 3, "masters": 3, "ms": 3, "m.s.": 3, "mba": 3, "m.b.a.": 3, "msc": 3, "m.sc.": 3,
    "bachelor": 2, "bachelors": 2, "bs": 2, "b.s.": 2, "ba": 2, "b.a.": 2, "bsc": 2, "b.sc.": 2, "b.e.": 2, "b.tech": 2,
    "associate": 1, "associates": 1, "aa": 1, "as": 1
}


def calculate_skill_overlap_score(
    candidate_skills: List[str],
    job_required_skills: List[str],
    job_preferred_skills: Optional[List[str]] = None
) -> Tuple[float, Dict[str, Any]]:
    """
    Calculates skill overlap sub-score (0.0 to 1.0).
    Required skills contribute 75% of score weight; Preferred skills contribute 25%.
    Returns (score_0_to_1, detail_dict).
    """
    job_preferred_skills = job_preferred_skills or []
    
    cand_norm = set(normalize_skills(candidate_skills))
    req_norm = normalize_skills(job_required_skills)
    pref_norm = normalize_skills(job_preferred_skills)

    matched_req = [s for s in req_norm if s in cand_norm]
    missing_req = [s for s in req_norm if s not in cand_norm]

    matched_pref = [s for s in pref_norm if s in cand_norm]
    missing_pref = [s for s in pref_norm if s not in cand_norm]

    req_ratio = len(matched_req) / len(req_norm) if req_norm else 1.0
    pref_ratio = len(matched_pref) / len(pref_norm) if pref_norm else 1.0

    if req_norm and pref_norm:
        score = (0.75 * req_ratio) + (0.25 * pref_ratio)
    elif req_norm:
        score = req_ratio
    elif pref_norm:
        score = pref_ratio
    else:
        # Job has no skill requirements stated -> default to 1.0 (no penalty)
        score = 1.0

    detail = {
        "matched_required_skills": matched_req,
        "missing_required_skills": missing_req,
        "matched_preferred_skills": matched_pref,
        "missing_preferred_skills": missing_pref,
        "required_overlap_ratio": round(req_ratio, 4),
        "preferred_overlap_ratio": round(pref_ratio, 4)
    }

    return round(score, 4), detail


def calculate_experience_score(
    candidate_years: float,
    job_min_years: float
) -> Tuple[float, Dict[str, Any]]:
    """
    Calculates experience sub-score (0.0 to 1.0).
    - Underqualified (< job_min_years): ratio decay = candidate_years / job_min_years.
    - Qualified (job_min_years <= candidate_years <= job_min_years + 3): score = 1.0.
    - Overqualified (> job_min_years + 3): gentle decay down to a floor of 0.70.
    Returns (score_0_to_1, detail_dict).
    """
    candidate_years = max(0.0, float(candidate_years or 0.0))
    job_min_years = max(0.0, float(job_min_years or 0.0))

    if job_min_years == 0.0:
        return 1.0, {
            "candidate_years": candidate_years,
            "required_years": 0.0,
            "status": "qualified",
            "overqualified_flag": False
        }

    if candidate_years < job_min_years:
        score = candidate_years / job_min_years
        status = "underqualified"
        overqualified_flag = False
    elif candidate_years <= job_min_years + 3.0:
        score = 1.0
        status = "qualified"
        overqualified_flag = False
    else:
        # Overqualified case: subtract 0.03 per extra year beyond (job_min_years + 3), floor at 0.70
        extra_years = candidate_years - (job_min_years + 3.0)
        score = max(0.70, 1.0 - (0.03 * extra_years))
        status = "overqualified"
        overqualified_flag = True

    detail = {
        "candidate_years": round(candidate_years, 1),
        "required_years": round(job_min_years, 1),
        "status": status,
        "overqualified_flag": overqualified_flag
    }

    return round(score, 4), detail


def _parse_degree_level(degree_str: str) -> int:
    if not degree_str:
        return 0
    clean = re.sub(r"[^\w\s\.]", "", degree_str.lower())
    words = clean.split()
    max_level = 0
    for w in words:
        if w in DEGREE_LEVELS:
            max_level = max(max_level, DEGREE_LEVELS[w])
    return max_level


def calculate_education_score(
    candidate_education: List[Dict[str, Any]],
    job_education_req: Optional[str]
) -> Tuple[float, Dict[str, Any]]:
    """
    Calculates education sub-score (0.0 to 1.0) comparing candidate degrees against job requirement.
    If job has no education requirement stated, returns 1.0.
    """
    if not job_education_req or not job_education_req.strip() or job_education_req.lower() in ["none", "n/a", "any"]:
        return 1.0, {
            "candidate_degrees": [e.get("degree", "") for e in (candidate_education or []) if isinstance(e, dict)],
            "required_education": job_education_req or "None",
            "status": "no_requirement_stated"
        }

    req_level = _parse_degree_level(job_education_req)
    if req_level == 0:
        req_level = 2  # Default to Bachelor's if ambiguous string like "Degree in CS"

    cand_degrees = []
    cand_max_level = 0
    for edu in candidate_education or []:
        if isinstance(edu, dict):
            deg_title = edu.get("degree", "")
            cand_degrees.append(deg_title)
            cand_max_level = max(cand_max_level, _parse_degree_level(deg_title))

    if cand_max_level >= req_level:
        score = 1.0
        status = "meets_or_exceeds"
    elif cand_max_level == req_level - 1:
        score = 0.80
        status = "one_level_below"
    else:
        score = 0.50
        status = "below_requirement"

    detail = {
        "candidate_degrees": cand_degrees,
        "candidate_degree_level": cand_max_level,
        "required_education": job_education_req,
        "required_degree_level": req_level,
        "status": status
    }

    return round(score, 4), detail


def calculate_hybrid_score(
    semantic_score_0_to_1: float,
    candidate_structured_data: Optional[Dict[str, Any]],
    job_structured_data: Optional[Dict[str, Any]],
    weights: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    Calculates weighted hybrid final score (0.0 to 100.0) combining semantic similarity and rule sub-scores.
    """
    # Default weights: Skills 40%, Semantic 30%, Experience 20%, Education 10%
    w = {
        "skills_weight": 0.40,
        "semantic_weight": 0.30,
        "experience_weight": 0.20,
        "education_weight": 0.10
    }
    if weights:
        w.update(weights)

    # Normalize weights so they sum to 1.0
    total_w = sum(w.values())
    if total_w > 0:
        w = {k: v / total_w for k, v in w.items()}

    cand_data = candidate_structured_data or {}
    job_data = job_structured_data or {}

    # 1. Skill Overlap Sub-score
    cand_skills = cand_data.get("skills", [])
    job_req_skills = job_data.get("required_skills") or job_data.get("skills") or []
    job_pref_skills = job_data.get("preferred_skills") or []
    skill_score_0_to_1, skill_detail = calculate_skill_overlap_score(cand_skills, job_req_skills, job_pref_skills)

    # 2. Experience Sub-score
    cand_exp = cand_data.get("total_years_experience") or cand_data.get("experience_years") or 0.0
    job_min_exp = job_data.get("min_years_experience") or job_data.get("min_experience_years") or 0.0
    exp_score_0_to_1, exp_detail = calculate_experience_score(cand_exp, job_min_exp)

    # 3. Education Sub-score
    cand_edu = cand_data.get("education") or []
    job_edu_req = job_data.get("education_requirement")
    edu_score_0_to_1, edu_detail = calculate_education_score(cand_edu, job_edu_req)

    # 4. Semantic Similarity Sub-score (Clamped 0.0 to 1.0)
    sem_score_0_to_1 = max(0.0, min(1.0, float(semantic_score_0_to_1 or 0.0)))

    # Weighted combination (scaled to 0-100%)
    weighted_sum_0_to_1 = (
        (w["skills_weight"] * skill_score_0_to_1) +
        (w["semantic_weight"] * sem_score_0_to_1) +
        (w["experience_weight"] * exp_score_0_to_1) +
        (w["education_weight"] * edu_score_0_to_1)
    )

    final_score_pct = round(weighted_sum_0_to_1 * 100.0, 2)
    rule_score_pct = round(
        ((skill_score_0_to_1 * 0.57) + (exp_score_0_to_1 * 0.29) + (edu_score_0_to_1 * 0.14)) * 100.0,
        2
    )

    return {
        "final_score": final_score_pct,
        "semantic_score": round(sem_score_0_to_1 * 100.0, 2),
        "rule_score": rule_score_pct,
        "skill_overlap_score": round(skill_score_0_to_1 * 100.0, 2),
        "experience_score": round(exp_score_0_to_1 * 100.0, 2),
        "education_score": round(edu_score_0_to_1 * 100.0, 2),
        "weights_used": {k: round(v, 4) for k, v in w.items()},
        "breakdown": {
            "skills": skill_detail,
            "experience": exp_detail,
            "education": edu_detail
        }
    }
