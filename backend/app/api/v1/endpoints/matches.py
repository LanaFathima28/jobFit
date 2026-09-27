from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.candidate import Candidate
from app.models.job import Job
from app.models.match import Match
from app.schemas.match import MatchRankRequest, MatchLeaderboardItem, MatchResponse
from app.services.matching_service import (
    calculate_semantic_similarity,
    calculate_rule_based_similarity,
    generate_match_explanation
)
from app.core.security import verify_api_key

router = APIRouter(prefix="/matches", tags=["Matches"])


@router.post("/rank", response_model=List[MatchLeaderboardItem])
def rank_candidates_for_job(
    payload: MatchRankRequest,
    db: Session = Depends(get_db),
    api_key: Optional[str] = Depends(verify_api_key)
):
    """
    Compute hybrid match scores for candidates against a job description.
    Updates existing matches or inserts new matches into DB, then returns the ranked leaderboard.
    """
    job = db.query(Job).filter(Job.id == payload.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    query = db.query(Candidate)
    if payload.candidate_ids:
        query = query.filter(Candidate.id.in_(payload.candidate_ids))
    candidates = query.all()

    if not candidates:
        return []

    job_data = job.structured_data or {}
    job_skills = job_data.get("skills", [])
    job_exp = job_data.get("min_experience_years", 0)

    leaderboard: List[MatchLeaderboardItem] = []

    for candidate in candidates:
        candidate_data = candidate.structured_data or {}
        cand_skills = candidate_data.get("skills", [])
        cand_exp = candidate_data.get("experience_years", 0)

        semantic_score = calculate_semantic_similarity(
            candidate.embedding or [], job.embedding or []
        )

        rule_score = calculate_rule_based_similarity(
            candidate_skills=cand_skills,
            job_skills=job_skills,
            candidate_exp_years=cand_exp,
            job_min_exp_years=job_exp
        )

        final_score = round(0.6 * semantic_score + 0.4 * rule_score, 2)

        explanation = generate_match_explanation(
            candidate_name=candidate.name,
            candidate_data=candidate_data,
            job_title=job.title,
            job_data=job_data,
            semantic_score=semantic_score,
            rule_score=rule_score,
            final_score=final_score
        )

        existing_match = db.query(Match).filter(
            Match.job_id == job.id, Match.candidate_id == candidate.id
        ).first()

        if existing_match:
            existing_match.semantic_score = semantic_score
            existing_match.rule_score = rule_score
            existing_match.final_score = final_score
            existing_match.explanation = explanation
            db_match = existing_match
        else:
            db_match = Match(
                job_id=job.id,
                candidate_id=candidate.id,
                semantic_score=semantic_score,
                rule_score=rule_score,
                final_score=final_score,
                explanation=explanation
            )
            db.add(db_match)

        db.commit()
        db.refresh(db_match)

        leaderboard.append(
            MatchLeaderboardItem(
                id=db_match.id,
                candidate_id=candidate.id,
                candidate_name=candidate.name,
                candidate_skills=cand_skills,
                candidate_experience_years=cand_exp,
                job_id=job.id,
                semantic_score=semantic_score,
                rule_score=rule_score,
                final_score=final_score,
                explanation=explanation,
                created_at=db_match.created_at
            )
        )

    leaderboard.sort(key=lambda item: item.final_score, reverse=True)
    return leaderboard


@router.get("/job/{job_id}", response_model=List[MatchLeaderboardItem])
def get_job_matches(
    job_id: UUID,
    db: Session = Depends(get_db),
    api_key: Optional[str] = Depends(verify_api_key)
):
    """
    Fetch existing ranked candidate leaderboard for a specific job.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    matches = (
        db.query(Match)
        .join(Candidate, Match.candidate_id == Candidate.id)
        .filter(Match.job_id == job_id)
        .order_by(Match.final_score.desc())
        .all()
    )

    leaderboard: List[MatchLeaderboardItem] = []
    for m in matches:
        cand = m.candidate
        cand_data = cand.structured_data or {} if cand else {}
        leaderboard.append(
            MatchLeaderboardItem(
                id=m.id,
                candidate_id=m.candidate_id,
                candidate_name=cand.name if cand else "Unknown Candidate",
                candidate_skills=cand_data.get("skills", []) if cand else [],
                candidate_experience_years=cand_data.get("experience_years", 0) if cand else 0,
                job_id=m.job_id,
                semantic_score=m.semantic_score or 0.0,
                rule_score=m.rule_score or 0.0,
                final_score=m.final_score or 0.0,
                explanation=m.explanation,
                created_at=m.created_at
            )
        )

    return leaderboard


@router.post("/{match_id}/explain")
def generate_single_match_explanation(
    match_id: UUID,
    db: Session = Depends(get_db),
    api_key: Optional[str] = Depends(verify_api_key)
):
    """
    Phase 5 Core Endpoint: Generates or regenerates an AI match explanation for a single Candidate-Job match record.
    """
    from app.services.explanation import generate_candidate_explanation
    from app.services.scoring import calculate_hybrid_score

    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found.")

    candidate = db.query(Candidate).filter(Candidate.id == match.candidate_id).first()
    job = db.query(Job).filter(Job.id == match.job_id).first()

    if not candidate or not job:
        raise HTTPException(status_code=400, detail="Associated candidate or job record not found.")

    hybrid_breakdown = match.score_breakdown or calculate_hybrid_score(
        semantic_score_0_to_1=(match.semantic_score or 0.0) / 100.0,
        candidate_structured_data=candidate.structured_data,
        job_structured_data=job.structured_data
    )

    explanation_dict, status_str, raw_llm = generate_candidate_explanation(
        candidate_name=candidate.name,
        job_title=job.title,
        final_score=match.final_score or 0.0,
        hybrid_breakdown=hybrid_breakdown
    )

    match.explanation = explanation_dict.get("summary")
    updated_breakdown = dict(hybrid_breakdown)
    updated_breakdown["explanation_object"] = explanation_dict
    updated_breakdown["explanation_status"] = status_str
    match.score_breakdown = updated_breakdown

    db.commit()
    db.refresh(match)

    return {
        "match_id": str(match.id),
        "candidate_id": str(candidate.id),
        "candidate_name": candidate.name,
        "job_id": str(job.id),
        "final_score": match.final_score,
        "explanation": explanation_dict,
        "status": status_str
    }


@router.get("/{match_id}", response_model=MatchResponse)
def get_single_match(
    match_id: UUID,
    db: Session = Depends(get_db),
    api_key: Optional[str] = Depends(verify_api_key)
):
    """
    Get detailed match record by match ID, including cached scores, explanation, and interview questions.
    """
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found.")
    return match


@router.post("/{match_id}/generate-questions")
def generate_single_match_interview_questions(
    match_id: UUID,
    regenerate: bool = False,
    db: Session = Depends(get_db),
    api_key: Optional[str] = Depends(verify_api_key)
):
    """
    Phase 6 Core Endpoint: Generates and caches tailored, candidate-specific interview questions
    (technical deep-dives, behavioral trajectory, and gap probing) for a single Match record.
    Supports regenerate=true query parameter to bypass cache and produce fresh questions.
    """
    from app.services.interview_questions import generate_interview_questions
    from app.services.scoring import calculate_hybrid_score

    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found.")

    candidate = db.query(Candidate).filter(Candidate.id == match.candidate_id).first()
    job = db.query(Job).filter(Job.id == match.job_id).first()

    if not candidate or not job:
        raise HTTPException(status_code=400, detail="Associated candidate or job record not found.")

    if not regenerate and match.interview_questions:
        return {
            "match_id": str(match.id),
            "candidate_id": str(candidate.id),
            "candidate_name": candidate.name,
            "job_id": str(job.id),
            "interview_questions": match.interview_questions,
            "status": "cached"
        }

    hybrid_breakdown = match.score_breakdown or calculate_hybrid_score(
        semantic_score_0_to_1=(match.semantic_score or 0.0) / 100.0,
        candidate_structured_data=candidate.structured_data,
        job_structured_data=job.structured_data
    )

    questions_dict, status_str, raw_llm = generate_interview_questions(
        candidate_name=candidate.name,
        job_title=job.title,
        candidate_structured_data=candidate.structured_data or {},
        job_structured_data=job.structured_data or {},
        hybrid_breakdown=hybrid_breakdown
    )

    match.interview_questions = questions_dict
    updated_breakdown = dict(hybrid_breakdown or {})
    updated_breakdown["interview_questions"] = questions_dict
    updated_breakdown["questions_status"] = status_str
    match.score_breakdown = updated_breakdown

    db.commit()
    db.refresh(match)

    return {
        "match_id": str(match.id),
        "candidate_id": str(candidate.id),
        "candidate_name": candidate.name,
        "job_id": str(job.id),
        "interview_questions": questions_dict,
        "status": status_str
    }
