import json
import logging
from typing import Dict, Any, List
import anthropic
import openai
from app.core.config import settings

logger = logging.getLogger(__name__)


def generate_tailored_interview_questions(
    candidate_name: str,
    candidate_data: Dict[str, Any],
    job_title: str,
    job_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Generate 3-5 tailored technical & behavioral interview questions with evaluation rubrics
    targeted at candidate skill gaps and job requirements.
    """
    prompt = f"""You are an expert technical interviewer and talent assessor.
Generate 4 highly tailored interview questions for Candidate "{candidate_name}" applying for the role "{job_title}".

Candidate Summary:
- Skills: {candidate_data.get('skills', [])}
- Experience: {candidate_data.get('experience_years', 0)} years
- Background: {json.dumps(candidate_data.get('experience', []), indent=2)[:1000]}

Job Description:
- Title: {job_title}
- Required Skills: {job_data.get('skills', [])}
- Requirements: {job_data.get('requirements', []) or job_data.get('description', '')}

Requirements:
Return ONLY a valid JSON object matching this schema:
{{
  "overall_assessment": "Short summary of focus areas during interview",
  "skill_gaps_to_probe": ["gap 1", "gap 2"],
  "questions": [
    {{
      "id": 1,
      "category": "Technical Depth" or "Behavioral" or "Architecture/Design",
      "question": "Clear, specific question targeting a skill gap or core requirement",
      "purpose": "Why this question is being asked",
      "ideal_answer_points": ["Key point 1", "Key point 2"],
      "evaluation_rubric": {{
        "excellent": "What candidate says to score 5/5",
        "acceptable": "What candidate says to score 3/5",
        "red_flags": "What candidate says/does to fail"
      }}
    }}
  ]
}}

Return ONLY the raw JSON string. No markdown wrappers.
"""

    if settings.ANTHROPIC_API_KEY:
        try:
            client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
            response = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=1500,
                messages=[{"role": "user", "content": prompt}]
            )
            content = response.content[0].text.strip()
            if content.startswith("```json"):
                content = content.replace("```json", "").replace("```", "").strip()
            elif content.startswith("```"):
                content = content.replace("```", "").strip()
            return json.loads(content)
        except Exception as e:
            logger.warning(f"Claude interview generation failed: {str(e)}")

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
            logger.warning(f"OpenAI interview generation failed: {str(e)}")

    # Fallback response
    return {
        "overall_assessment": f"Assess {candidate_name}'s experience against {job_title} key requirements.",
        "skill_gaps_to_probe": job_data.get("skills", ["General Technical Alignment"])[:3],
        "questions": [
            {
                "id": 1,
                "category": "Technical Depth",
                "question": f"Can you walk us through a recent project where you applied {candidate_data.get('skills', ['key technologies'])[0] if candidate_data.get('skills') else 'your key skills'} under tight deadlines?",
                "purpose": "Evaluate practical implementation experience.",
                "ideal_answer_points": [
                    "Clear architectural explanation",
                    "Specific problem solved and metrics achieved"
                ],
                "evaluation_rubric": {
                    "excellent": "Provides specific metrics, trade-offs, and clear architecture breakdown.",
                    "acceptable": "Describes project lifecycle and role clearly.",
                    "red_flags": "Vague explanations with no technical details."
                }
            },
            {
                "id": 2,
                "category": "System Design",
                "question": f"How would you design a scalable service tailored for {job_title} core responsibilities?",
                "purpose": "Assess system architecture skills.",
                "ideal_answer_points": [
                    "Decoupled components",
                    "Caching and database optimization"
                ],
                "evaluation_rubric": {
                    "excellent": "Covers load balancing, caching, database indexing, and fault tolerance.",
                    "acceptable": "Covers basic API layout and DB schema.",
                    "red_flags": "Ignores scaling bottleneck risks."
                }
            }
        ]
    }
