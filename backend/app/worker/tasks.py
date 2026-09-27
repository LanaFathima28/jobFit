import logging
from typing import Dict, Any, Optional, List
from uuid import UUID
from app.worker.celery_app import celery_app, update_task_progress
from app.db.session import SessionLocal
from app.models.candidate import Candidate
from app.models.job import Job
from app.models.match import Match
from app.services.extraction_service import extract_text_from_file_bytes, ExtractionStatus
from app.services.structured_extraction import (
    extract_candidate_structured_data,
    extract_job_structured_data
)
from app.services.embedding_service import (
    build_candidate_embedding_input,
    build_job_embedding_input,
    generate_text_embedding,
    compute_cosine_similarity
)
from app.services.scoring import calculate_hybrid_score
from app.services.explanation import generate_candidate_explanation
from app.services.interview_questions import generate_interview_questions
from app.core.config import settings

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="app.worker.tasks.recompute_candidate_embedding")
def recompute_candidate_embedding_task(self, candidate_id_str: str) -> bool:
    """
    Background worker task to recompute candidate vector embedding.
    """
    db = SessionLocal()
    try:
        cand_id = UUID(candidate_id_str)
        candidate = db.query(Candidate).filter(Candidate.id == cand_id).first()
        if not candidate:
            logger.error(f"Candidate {candidate_id_str} not found for embedding update.")
            return False

        structured = candidate.structured_data or {}
        text_for_embedding = build_candidate_embedding_input(structured, candidate.raw_text)
        
        embedding_vector = generate_text_embedding(text_for_embedding)
        candidate.embedding_input = text_for_embedding
        candidate.embedding = embedding_vector
        db.commit()
        logger.info(f"Successfully recomputed embedding for candidate {candidate_id_str}")
        return True
    except Exception as e:
        logger.error(f"Error recomputing candidate embedding: {str(e)}")
        db.rollback()
        return False
    finally:
        db.close()


@celery_app.task(bind=True, name="app.worker.tasks.process_candidate_file_pipeline_task")
def process_candidate_file_pipeline_task(self, candidate_id_str: str) -> Dict[str, Any]:
    """
    Async pipeline for single uploaded candidate resume:
    1. Extract text if missing/pending.
    2. Run structured profile extraction (LLM).
    3. Generate 1536-dim vector embedding.
    """
    db = SessionLocal()
    try:
        cand_id = UUID(candidate_id_str)
        candidate = db.query(Candidate).filter(Candidate.id == cand_id).first()
        if not candidate:
            err_msg = f"Candidate {candidate_id_str} not found."
            update_task_progress(self, state="FAILED", step="fetch_candidate", progress=0, error=err_msg)
            return {"status": "failed", "error": err_msg}

        update_task_progress(self, state="PROCESSING", step="text_extraction", progress=25, details={"candidate_id": candidate_id_str})

        # Step 1: Text extraction if not done yet
        if not candidate.raw_text and candidate.file_path:
            try:
                with open(candidate.file_path, "rb") as f:
                    file_bytes = f.read()
                ext_res = extract_text_from_file_bytes(file_bytes, candidate.original_filename or "resume.pdf")
                candidate.raw_text = ext_res.text if ext_res.status == ExtractionStatus.SUCCESS else None
                candidate.extraction_status = ext_res.status.value
                candidate.extraction_error = ext_res.error_message
                db.commit()
            except Exception as e:
                candidate.extraction_status = "failed"
                candidate.extraction_error = str(e)
                db.commit()
                logger.error(f"Text extraction failed for candidate {candidate_id_str}: {str(e)}")

        if not candidate.raw_text:
            err_msg = candidate.extraction_error or "Raw text extraction failed or text is empty."
            candidate.structured_extraction_status = "failed"
            candidate.debug_raw_llm_output = err_msg
            db.commit()
            update_task_progress(self, state="FAILED", step="text_extraction", progress=25, error=err_msg)
            return {"status": "failed", "candidate_id": candidate_id_str, "error": err_msg}

        # Step 2: Structured extraction (LLM)
        update_task_progress(self, state="PROCESSING", step="structured_extraction", progress=50, details={"candidate_id": candidate_id_str})
        try:
            structured_dict, ext_status, debug_llm = extract_candidate_structured_data(candidate.raw_text)
            candidate.structured_data = structured_dict
            candidate.structured_extraction_status = ext_status
            candidate.debug_raw_llm_output = debug_llm
            if structured_dict.get("full_name") and structured_dict["full_name"].strip():
                candidate.name = structured_dict["full_name"].strip()
            db.commit()
        except Exception as e:
            logger.error(f"Structured extraction error for candidate {candidate_id_str}: {str(e)}")
            candidate.structured_extraction_status = "failed"
            candidate.debug_raw_llm_output = str(e)
            db.commit()

        # Step 3: Embed candidate
        update_task_progress(self, state="PROCESSING", step="embedding_generation", progress=75, details={"candidate_id": candidate_id_str})
        try:
            emb_input = build_candidate_embedding_input(candidate.structured_data, candidate.raw_text)
            candidate.embedding_input = emb_input
            candidate.embedding = generate_text_embedding(emb_input)
            db.commit()
        except Exception as e:
            logger.error(f"Embedding generation error for candidate {candidate_id_str}: {str(e)}")

        db.refresh(candidate)
        res = {
            "status": "success",
            "candidate_id": str(candidate.id),
            "name": candidate.name,
            "extraction_status": candidate.extraction_status,
            "structured_extraction_status": candidate.structured_extraction_status,
            "has_embedding": candidate.embedding is not None
        }
        update_task_progress(self, state="SUCCESS", step="completed", progress=100, details=res)
        return res
    except Exception as exc:
        db.rollback()
        err_str = str(exc)
        logger.error(f"Candidate file pipeline task failed for {candidate_id_str}: {err_str}")
        update_task_progress(self, state="FAILED", step="pipeline_failed", progress=0, error=err_str)
        return {"status": "failed", "candidate_id": candidate_id_str, "error": err_str}
    finally:
        db.close()


@celery_app.task(bind=True, name="app.worker.tasks.generate_explanation_task")
def generate_explanation_task(self, match_id_str: str) -> Dict[str, Any]:
    """
    Generates AI match explanation for a single Candidate-Job match record.
    """
    db = SessionLocal()
    try:
        match_id = UUID(match_id_str)
        match = db.query(Match).filter(Match.id == match_id).first()
        if not match:
            return {"status": "failed", "error": f"Match {match_id_str} not found"}

        candidate = db.query(Candidate).filter(Candidate.id == match.candidate_id).first()
        job = db.query(Job).filter(Job.id == match.job_id).first()
        if not candidate or not job:
            return {"status": "failed", "error": "Associated candidate or job not found"}

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

        return {
            "status": status_str,
            "match_id": match_id_str,
            "candidate_name": candidate.name,
            "explanation": explanation_dict
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Error generating explanation for match {match_id_str}: {str(e)}")
        return {"status": "failed", "match_id": match_id_str, "error": str(e)}
    finally:
        db.close()


@celery_app.task(bind=True, name="app.worker.tasks.generate_questions_task")
def generate_questions_task(self, match_id_str: str) -> Dict[str, Any]:
    """
    Generates tailored AI interview questions for a single Candidate-Job match record.
    """
    db = SessionLocal()
    try:
        match_id = UUID(match_id_str)
        match = db.query(Match).filter(Match.id == match_id).first()
        if not match:
            return {"status": "failed", "error": f"Match {match_id_str} not found"}

        candidate = db.query(Candidate).filter(Candidate.id == match.candidate_id).first()
        job = db.query(Job).filter(Job.id == match.job_id).first()
        if not candidate or not job:
            return {"status": "failed", "error": "Associated candidate or job not found"}

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

        return {
            "status": status_str,
            "match_id": match_id_str,
            "candidate_name": candidate.name,
            "interview_questions": questions_dict
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Error generating interview questions for match {match_id_str}: {str(e)}")
        return {"status": "failed", "match_id": match_id_str, "error": str(e)}
    finally:
        db.close()


@celery_app.task(bind=True, name="app.worker.tasks.process_job_pipeline_task")
def process_job_pipeline_task(
    self,
    job_id_str: str,
    top_n_explain: int = 10,
    top_n_questions: int = 5,
    weights_override: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    Full async orchestration pipeline for a Job:
    1. Extract structured criteria and embed Job description if needed.
    2. Extract structured data and embed candidates needing processing.
    3. Compute hybrid scoring against all candidates and rank them.
    4. Generate AI explanations for top N candidates.
    5. Generate tailored AI interview questions for top N candidates.
    """
    db = SessionLocal()
    try:
        job_id = UUID(job_id_str)
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            err_msg = f"Job {job_id_str} not found."
            update_task_progress(self, state="FAILED", step="fetch_job", progress=0, error=err_msg)
            return {"status": "failed", "error": err_msg}

        # Step 1: Ingest Job Description (Structured Extraction & Vector Embedding)
        update_task_progress(self, state="PROCESSING", step="ingesting_job", progress=10, details={"job_id": job_id_str})
        if not job.structured_data and job.description_text:
            try:
                struct_dict, status_str, debug_llm = extract_job_structured_data(job.description_text)
                job.structured_data = struct_dict
                job.structured_extraction_status = status_str
                job.debug_raw_llm_output = debug_llm
                if struct_dict.get("job_title") and struct_dict["job_title"].strip():
                    job.title = struct_dict["job_title"].strip()
                db.commit()
            except Exception as e:
                logger.error(f"Job structured extraction failed: {str(e)}")

        if not job.embedding and job.description_text:
            try:
                inp = build_job_embedding_input(job.structured_data, job.title, job.description_text)
                job.embedding_input = inp
                job.embedding = generate_text_embedding(inp)
                db.commit()
            except Exception as e:
                logger.error(f"Job embedding generation failed: {str(e)}")

        job_vector = job.embedding

        # Step 2: Ensure Candidate processing (Resilient per-candidate extraction & embedding)
        update_task_progress(self, state="PROCESSING", step="processing_candidates", progress=30)
        candidates = db.query(Candidate).all()
        processed_candidates_count = 0
        failed_candidates_count = 0

        for cand in candidates:
            try:
                # Text extraction fallback if raw_text is missing but file_path exists
                if not cand.raw_text and cand.file_path:
                    try:
                        with open(cand.file_path, "rb") as f:
                            fb = f.read()
                        res = extract_text_from_file_bytes(fb, cand.original_filename or "resume.pdf")
                        cand.raw_text = res.text if res.status == ExtractionStatus.SUCCESS else None
                        cand.extraction_status = res.status.value
                        cand.extraction_error = res.error_message
                        db.commit()
                    except Exception as e:
                        cand.extraction_status = "failed"
                        cand.extraction_error = str(e)
                        db.commit()

                # Skip structured extraction & embedding if candidate has no raw_text
                if not cand.raw_text:
                    cand.structured_extraction_status = "failed"
                    db.commit()
                    failed_candidates_count += 1
                    continue

                # Structured profile extraction if pending
                if not cand.structured_data or cand.structured_extraction_status == "pending":
                    try:
                        struct_d, st_str, dbg = extract_candidate_structured_data(cand.raw_text)
                        cand.structured_data = struct_d
                        cand.structured_extraction_status = st_str
                        cand.debug_raw_llm_output = dbg
                        if struct_d.get("full_name") and struct_d["full_name"].strip():
                            cand.name = struct_d["full_name"].strip()
                        db.commit()
                    except Exception as e:
                        cand.structured_extraction_status = "failed"
                        cand.debug_raw_llm_output = str(e)
                        db.commit()
                        failed_candidates_count += 1
                        continue

                if cand.structured_extraction_status == "failed":
                    failed_candidates_count += 1
                    continue

                # Vector embedding if missing
                if not cand.embedding:
                    try:
                        c_inp = build_candidate_embedding_input(cand.structured_data, cand.raw_text)
                        cand.embedding_input = c_inp
                        cand.embedding = generate_text_embedding(c_inp)
                        db.commit()
                    except Exception as e:
                        logger.error(f"Failed embedding candidate {cand.id}: {str(e)}")

                processed_candidates_count += 1
            except Exception as cand_exc:
                logger.error(f"Candidate {cand.id} pipeline error: {str(cand_exc)}")
                failed_candidates_count += 1

        # Step 3: Compute Hybrid Scores & Rank Candidates
        update_task_progress(self, state="PROCESSING", step="scoring_and_ranking", progress=60)
        
        # Prepare scoring weights
        weights = {
            "skills_weight": settings.DEFAULT_SKILLS_WEIGHT,
            "semantic_weight": settings.DEFAULT_SEMANTIC_WEIGHT,
            "experience_weight": settings.DEFAULT_EXPERIENCE_WEIGHT,
            "education_weight": settings.DEFAULT_EDUCATION_WEIGHT,
        }
        if weights_override:
            weights.update(weights_override)

        valid_candidates = [c for c in candidates if c.embedding is not None]
        matches_records: List[Match] = []

        for cand in valid_candidates:
            sim_score = compute_cosine_similarity(job_vector, cand.embedding) if job_vector and cand.embedding else 0.0
            hybrid_res = calculate_hybrid_score(
                semantic_score_0_to_1=sim_score,
                candidate_structured_data=cand.structured_data,
                job_structured_data=job.structured_data,
                weights=weights
            )

            match = db.query(Match).filter(Match.candidate_id == cand.id, Match.job_id == job.id).first()
            if match:
                match.semantic_score = hybrid_res["semantic_score"]
                match.rule_score = hybrid_res["rule_score"]
                match.skill_overlap_score = hybrid_res["skill_overlap_score"]
                match.experience_score = hybrid_res["experience_score"]
                match.education_score = hybrid_res["education_score"]
                match.final_score = hybrid_res["final_score"]
                match.score_breakdown = hybrid_res
            else:
                match = Match(
                    candidate_id=cand.id,
                    job_id=job.id,
                    semantic_score=hybrid_res["semantic_score"],
                    rule_score=hybrid_res["rule_score"],
                    skill_overlap_score=hybrid_res["skill_overlap_score"],
                    experience_score=hybrid_res["experience_score"],
                    education_score=hybrid_res["education_score"],
                    final_score=hybrid_res["final_score"],
                    score_breakdown=hybrid_res
                )
                db.add(match)
            db.commit()
            db.refresh(match)
            matches_records.append(match)

        # Sort matches by final_score descending
        matches_records.sort(key=lambda m: m.final_score or 0.0, reverse=True)

        # Step 4: AI Generation for Top N Matches
        update_task_progress(self, state="PROCESSING", step="generating_ai_insights", progress=80)
        
        top_explain_matches = matches_records[:top_n_explain]
        top_questions_matches = matches_records[:top_n_questions]

        explained_count = 0
        for m in top_explain_matches:
            try:
                res = generate_explanation_task.run(str(m.id))
                if res.get("status") in ["success", "completed"]:
                    explained_count += 1
            except Exception as e:
                logger.error(f"Error generating explanation for match {m.id}: {str(e)}")

        questions_count = 0
        for m in top_questions_matches:
            try:
                res = generate_questions_task.run(str(m.id))
                if res.get("status") in ["success", "completed", "cached"]:
                    questions_count += 1
            except Exception as e:
                logger.error(f"Error generating questions for match {m.id}: {str(e)}")

        # Step 5: Finalize task output
        summary = {
            "status": "success",
            "job_id": str(job.id),
            "job_title": job.title,
            "total_candidates": len(candidates),
            "processed_candidates": processed_candidates_count,
            "failed_candidates": failed_candidates_count,
            "ranked_matches_count": len(matches_records),
            "top_explanations_generated": explained_count,
            "top_questions_generated": questions_count,
        }
        update_task_progress(self, state="SUCCESS", step="completed", progress=100, details=summary)
        return summary

    except Exception as exc:
        db.rollback()
        err_str = str(exc)
        logger.error(f"Process job pipeline task failed for job {job_id_str}: {err_str}")
        update_task_progress(self, state="FAILED", step="pipeline_failed", progress=0, error=err_str)
        return {"status": "failed", "job_id": job_id_str, "error": err_str}
    finally:
        db.close()
