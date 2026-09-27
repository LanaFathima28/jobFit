import logging
import time
import re
from typing import List, Optional, Dict, Any
import numpy as np
import openai
from app.core.config import settings

logger = logging.getLogger(__name__)

EMBEDDING_DIMENSION = 1536
BATCH_SIZE = 100


def build_candidate_embedding_input(structured_data: Optional[Dict[str, Any]], raw_text: Optional[str] = None) -> str:
    """
    Constructs a focused, structured embedding_input text string for a candidate.
    Concentrates vector weight on canonical skills, role titles, key duties, and education.
    """
    if not structured_data:
        if raw_text and raw_text.strip():
            return raw_text.strip()[:4000]
        return "Candidate Profile: Unknown Candidate"

    lines = []

    full_name = structured_data.get("full_name") or structured_data.get("name") or "Candidate"
    lines.append(f"Candidate Profile: {full_name}")

    exp_years = structured_data.get("total_years_experience") or structured_data.get("experience_years") or 0
    lines.append(f"Total Experience: {exp_years} years")

    skills = structured_data.get("skills", [])
    if skills:
        lines.append(f"Technical Skills: {', '.join(skills)}")

    work_history = structured_data.get("work_history") or structured_data.get("experience") or []
    if work_history:
        lines.append("Work History:")
        for pos in work_history[:5]:  # Top 5 most recent roles
            if isinstance(pos, dict):
                title = pos.get("title") or pos.get("role") or ""
                company = pos.get("company") or ""
                start = pos.get("start_date") or pos.get("duration") or ""
                end = pos.get("end_date") or ""
                desc = pos.get("description") or ""
                if isinstance(pos.get("highlights"), list):
                    desc = "; ".join(pos["highlights"])

                date_str = f"({start} - {end})" if end else f"({start})" if start else ""
                lines.append(f"- {title} at {company} {date_str}: {desc[:250]}")

    education = structured_data.get("education", [])
    if education:
        lines.append("Education:")
        for edu in education:
            if isinstance(edu, dict):
                deg = edu.get("degree", "")
                inst = edu.get("institution", "")
                field = edu.get("field", "")
                yr = edu.get("year", "")
                lines.append(f"- {deg} in {field} at {inst} ({yr})".replace(" in  at", " at"))

    certs = structured_data.get("certifications", [])
    if certs:
        lines.append(f"Certifications: {', '.join(certs)}")

    return "\n".join(lines).strip()


def build_job_embedding_input(structured_data: Optional[Dict[str, Any]], title: str = "", description_text: Optional[str] = None) -> str:
    """
    Constructs a focused, structured embedding_input text string for a job description.
    Concentrates vector weight on job title, required skills, preferred skills, and responsibilities.
    """
    if not structured_data:
        if description_text and description_text.strip():
            return f"Job Title: {title}\nDescription: {description_text.strip()[:4000]}"
        return f"Job Title: {title}"

    lines = []
    job_title = structured_data.get("job_title") or title or "Job Opening"
    lines.append(f"Job Title: {job_title}")

    min_exp = structured_data.get("min_years_experience") or structured_data.get("min_experience_years") or 0
    lines.append(f"Minimum Experience Required: {min_exp} years")

    req_skills = structured_data.get("required_skills") or structured_data.get("skills") or []
    if req_skills:
        lines.append(f"Required Skills: {', '.join(req_skills)}")

    pref_skills = structured_data.get("preferred_skills", [])
    if pref_skills:
        lines.append(f"Preferred Skills: {', '.join(pref_skills)}")

    edu_req = structured_data.get("education_requirement")
    if edu_req:
        lines.append(f"Education Requirement: {edu_req}")

    responsibilities = structured_data.get("responsibilities", [])
    if responsibilities:
        lines.append("Key Responsibilities:")
        for resp in responsibilities:
            lines.append(f"- {resp}")

    return "\n".join(lines).strip()


def generate_batch_embeddings(texts: List[str]) -> List[List[float]]:
    """
    Generates 1536-dim vector embeddings for a list of text strings in batches using OpenAI text-embedding-3-small.
    Handles rate limits with exponential backoff retries and includes deterministic fallback if API key absent.
    """
    if not texts:
        return []

    # Clean texts
    cleaned_texts = [t.replace("\n", " ").strip()[:8000] if t else "Empty" for t in texts]

    if settings.OPENAI_API_KEY:
        try:
            client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
            all_embeddings = []

            # Batch process in chunks of BATCH_SIZE (100)
            for i in range(0, len(cleaned_texts), BATCH_SIZE):
                chunk = cleaned_texts[i : i + BATCH_SIZE]
                
                # Retry loop for API rate limits / connection issues
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        response = client.embeddings.create(
                            model="text-embedding-3-small",
                            input=chunk
                        )
                        chunk_embeddings = [item.embedding for item in response.data]
                        all_embeddings.extend(chunk_embeddings)
                        break
                    except Exception as err:
                        if attempt == max_retries - 1:
                            raise err
                        time.sleep(2 ** attempt)

            return all_embeddings
        except Exception as e:
            logger.error(f"Error calling OpenAI Batch Embeddings API: {str(e)}")

    # Deterministic feature-hashing fallback mechanism if OpenAI API key is missing or call fails
    logger.info("Using feature-hashing fallback vector embedding generation for batch.")
    fallback_results = []
    
    for text in cleaned_texts:
        vec = np.zeros(EMBEDDING_DIMENSION, dtype=np.float32)
        words = re.findall(r"\w+", text.lower())
        if not words:
            fallback_results.append([0.0] * EMBEDDING_DIMENSION)
            continue

        for word in words:
            # Hash word to feature index and sign
            h = hash(word)
            idx = abs(h) % EMBEDDING_DIMENSION
            sign = 1.0 if (h & 1) else -1.0
            vec[idx] += sign

        norm = np.linalg.norm(vec)
        if norm == 0:
            fallback_results.append([0.0] * EMBEDDING_DIMENSION)
        else:
            fallback_results.append((vec / norm).tolist())

    return fallback_results


def generate_text_embedding(text: str) -> Optional[List[float]]:
    """
    Generate a single 1536-dimensional vector embedding for text.
    """
    results = generate_batch_embeddings([text])
    return results[0] if results else [0.0] * EMBEDDING_DIMENSION


def compute_cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """
    Computes cosine similarity (1.0 = identical, 0.0 = orthogonal, -1.0 = opposite)
    between two 1536-dim vector embeddings in Python (used for SQLite fallback or in-memory evaluation).
    """
    if not vec_a or not vec_b:
        return 0.0
    a = np.array(vec_a)
    b = np.array(vec_b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    sim = float(np.dot(a, b) / (norm_a * norm_b))
    return max(0.0, min(1.0, sim))  # Clamp between 0.0 and 1.0 for cosine similarity
