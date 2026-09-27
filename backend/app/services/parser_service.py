import io
import json
import logging
from typing import Any, Dict
import pdfplumber
import docx
import anthropic
import openai
from app.core.config import settings

logger = logging.getLogger(__name__)


from app.services.extraction_service import extract_text_from_file_bytes


def extract_text_from_file(file_bytes: bytes, filename: str) -> str:
    """
    Extract raw text from PDF or DOCX file bytes using extraction_service.
    """
    result = extract_text_from_file_bytes(file_bytes, filename)
    return result.text


def parse_resume_to_structured_json(raw_text: str) -> Dict[str, Any]:
    """
    Use Claude/OpenAI to extract structured candidate profile from raw resume text.
    """
    if not raw_text:
        return {
            "name": "Unknown Candidate",
            "email": "",
            "skills": [],
            "experience_years": 0,
            "summary": "Empty resume provided."
        }

    prompt = f"""Extract structured information from the following resume text into a strict JSON object.

JSON Schema required:
{{
  "name": "Candidate's full name",
  "email": "Candidate email if available",
  "phone": "Candidate phone if available",
  "summary": "Brief 2-3 sentence executive summary",
  "skills": ["list", "of", "technical", "and", "soft", "skills"],
  "experience_years": estimated_total_years_as_integer,
  "experience": [
    {{
      "company": "Company Name",
      "role": "Job Title",
      "duration": "Dates worked",
      "highlights": ["key achievements/responsibilities"]
    }}
  ],
  "education": [
    {{
      "degree": "Degree Name",
      "institution": "University/School",
      "year": "Graduation year or dates"
    }}
  ]
}}

Return ONLY valid raw JSON. No markdown wrappers, no commentary.

Resume Text:
{raw_text[:4000]}
"""

    # Try Anthropic Claude first if configured
    if settings.ANTHROPIC_API_KEY:
        try:
            client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
            response = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=1500,
                messages=[{"role": "user", "content": prompt}]
            )
            content = response.content[0].text.strip()
            # Clean potential markdown JSON formatting
            if content.startswith("```json"):
                content = content.replace("```json", "").replace("```", "").strip()
            elif content.startswith("```"):
                content = content.replace("```", "").strip()
            return json.loads(content)
        except Exception as e:
            logger.warning(f"Claude parsing failed, trying OpenAI/fallback: {str(e)}")

    # Try OpenAI if configured
    if settings.OPENAI_API_KEY:
        try:
            client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content
            return json.loads(content)
        except Exception as e:
            logger.warning(f"OpenAI parsing failed: {str(e)}")

    # Deterministic fallback parser if AI key is missing or calls fail
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    candidate_name = lines[0] if lines else "Candidate"
    
    # Extract naive skills from words
    common_tech_keywords = [
        "Python", "FastAPI", "React", "Next.js", "TypeScript", "JavaScript",
        "PostgreSQL", "SQL", "Docker", "AWS", "Git", "Node.js", "Java", "C++",
        "Tailwind", "REST API", "GraphQL", "Redis", "Celery", "Linux"
    ]
    detected_skills = [kw for kw in common_tech_keywords if kw.lower() in raw_text.lower()]
    
    return {
        "name": candidate_name[:100],
        "email": "",
        "phone": "",
        "summary": raw_text[:250] + "..." if len(raw_text) > 250 else raw_text,
        "skills": detected_skills if detected_skills else ["General Technical Skills"],
        "experience_years": 3,
        "experience": [],
        "education": []
    }
