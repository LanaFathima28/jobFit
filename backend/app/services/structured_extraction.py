import json
import logging
from typing import Dict, Any, Tuple
from pydantic import ValidationError

import anthropic
import openai

from app.core.config import settings
from app.prompts.extraction_prompts import (
    CANDIDATE_EXTRACTION_SYSTEM_PROMPT,
    CANDIDATE_EXTRACTION_TOOL,
    JOB_EXTRACTION_SYSTEM_PROMPT,
    JOB_EXTRACTION_TOOL,
)
from app.schemas.extraction_schemas import (
    CandidateExtractionSchema,
    JobExtractionSchema,
)
from app.services.skill_normalizer import normalize_skills

logger = logging.getLogger(__name__)


def _call_claude_tool_use(
    system_prompt: str,
    user_prompt: str,
    tool_definition: Dict[str, Any]
) -> Tuple[str, Dict[str, Any]]:
    """
    Executes a Claude API call with tool-use (structured outputs).
    Returns (raw_llm_response_text, extracted_tool_input_dict).
    """
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    response = client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=4000,
        system=system_prompt,
        tools=[tool_definition],
        tool_choice={"type": "tool", "name": tool_definition["name"]},
        messages=[{"role": "user", "content": user_prompt}]
    )

    raw_response_text = ""
    extracted_input = {}

    for block in response.content:
        if block.type == "text":
            raw_response_text += block.text + "\n"
        elif block.type == "tool_use" and block.name == tool_definition["name"]:
            extracted_input = block.input
            raw_response_text += f"[Tool Use Output: {json.dumps(block.input)}]"

    return raw_response_text.strip(), extracted_input


def _call_openai_tool_use(
    system_prompt: str,
    user_prompt: str,
    tool_definition: Dict[str, Any]
) -> Tuple[str, Dict[str, Any]]:
    """
    Fallback: Executes an OpenAI API call with function/tool calling.
    Returns (raw_llm_response_text, extracted_tool_input_dict).
    """
    client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
    tools = [{
        "type": "function",
        "function": {
            "name": tool_definition["name"],
            "description": tool_definition["description"],
            "parameters": tool_definition["input_schema"]
        }
    }]

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        tools=tools,
        tool_choice={"type": "function", "function": {"name": tool_definition["name"]}}
    )

    choice = response.choices[0]
    message = choice.message
    raw_response_text = message.content or ""
    extracted_input = {}

    if message.tool_calls:
        tool_call = message.tool_calls[0]
        extracted_input = json.loads(tool_call.function.arguments)
        raw_response_text += f"[Tool Call Arguments: {tool_call.function.arguments}]"

    return raw_response_text.strip(), extracted_input


def extract_candidate_structured_data(raw_text: str) -> Tuple[Dict[str, Any], str, str]:
    """
    Extracts structured candidate profile data from raw resume text using Claude Tool Use
    with Pydantic validation, skill normalization, and retry/fallback error handling.

    Returns:
        (structured_data_dict, extraction_status, debug_raw_llm_output)
    """
    if not raw_text or not raw_text.strip():
        return {}, "failed", "Cannot perform structured extraction: raw_text is empty."

    user_prompt = f"Resume Text:\n{raw_text[:8000]}"
    raw_llm_output = ""

    # Attempt 1: Call Claude API (or OpenAI fallback)
    tool_input = {}
    try:
        if settings.ANTHROPIC_API_KEY:
            raw_llm_output, tool_input = _call_claude_tool_use(
                CANDIDATE_EXTRACTION_SYSTEM_PROMPT, user_prompt, CANDIDATE_EXTRACTION_TOOL
            )
        elif settings.OPENAI_API_KEY:
            raw_llm_output, tool_input = _call_openai_tool_use(
                CANDIDATE_EXTRACTION_SYSTEM_PROMPT, user_prompt, CANDIDATE_EXTRACTION_TOOL
            )
        else:
            return {}, "failed", "No AI API keys (ANTHROPIC_API_KEY or OPENAI_API_KEY) configured."
    except Exception as api_err:
        logger.error(f"First attempt LLM API call error: {str(api_err)}")
        raw_llm_output = f"API Call Error: {str(api_err)}"

    # Attempt 1 Validation
    try:
        if tool_input:
            validated = CandidateExtractionSchema.model_validate(tool_input)
            validated.skills = normalize_skills(validated.skills)
            return validated.model_dump(), "success", raw_llm_output
    except ValidationError as val_err:
        logger.warning(f"Candidate extraction attempt 1 validation failed: {str(val_err)}. Retrying...")
        retry_prompt = f"{user_prompt}\n\n[SYSTEM NOTE: Your previous tool call failed validation with error: {str(val_err)}. Please re-extract carefully.]"
        
        # Attempt 2: Retry with validation error context
        try:
            if settings.ANTHROPIC_API_KEY:
                raw_llm_output_2, tool_input_2 = _call_claude_tool_use(
                    CANDIDATE_EXTRACTION_SYSTEM_PROMPT, retry_prompt, CANDIDATE_EXTRACTION_TOOL
                )
            else:
                raw_llm_output_2, tool_input_2 = _call_openai_tool_use(
                    CANDIDATE_EXTRACTION_SYSTEM_PROMPT, retry_prompt, CANDIDATE_EXTRACTION_TOOL
                )

            validated_2 = CandidateExtractionSchema.model_validate(tool_input_2)
            validated_2.skills = normalize_skills(validated_2.skills)
            return validated_2.model_dump(), "success", f"Retry Output:\n{raw_llm_output_2}"
        except Exception as retry_err:
            logger.error(f"Candidate extraction attempt 2 failed: {str(retry_err)}")
            return {}, "failed", f"Validation failed after 2 attempts. Error: {str(retry_err)}\nRaw LLM: {raw_llm_output}"

    # Fallback if no valid tool input returned
    return {}, "failed", f"Failed to extract structured candidate profile. Raw LLM response: {raw_llm_output}"


def extract_job_structured_data(raw_text: str) -> Tuple[Dict[str, Any], str, str]:
    """
    Extracts structured job posting requirements from raw job text using Claude Tool Use
    with Pydantic validation, skill normalization, and retry/fallback error handling.

    Returns:
        (structured_data_dict, extraction_status, debug_raw_llm_output)
    """
    if not raw_text or not raw_text.strip():
        return {}, "failed", "Cannot perform structured extraction: raw_text is empty."

    user_prompt = f"Job Description Text:\n{raw_text[:8000]}"
    raw_llm_output = ""

    # Attempt 1: Call LLM API
    tool_input = {}
    try:
        if settings.ANTHROPIC_API_KEY:
            raw_llm_output, tool_input = _call_claude_tool_use(
                JOB_EXTRACTION_SYSTEM_PROMPT, user_prompt, JOB_EXTRACTION_TOOL
            )
        elif settings.OPENAI_API_KEY:
            raw_llm_output, tool_input = _call_openai_tool_use(
                JOB_EXTRACTION_SYSTEM_PROMPT, user_prompt, JOB_EXTRACTION_TOOL
            )
        else:
            return {}, "failed", "No AI API keys configured."
    except Exception as api_err:
        logger.error(f"Job extraction attempt 1 API error: {str(api_err)}")
        raw_llm_output = f"API Call Error: {str(api_err)}"

    # Attempt 1 Validation
    try:
        if tool_input:
            validated = JobExtractionSchema.model_validate(tool_input)
            validated.required_skills = normalize_skills(validated.required_skills)
            validated.preferred_skills = normalize_skills(validated.preferred_skills)
            return validated.model_dump(), "success", raw_llm_output
    except ValidationError as val_err:
        logger.warning(f"Job extraction attempt 1 validation failed: {str(val_err)}. Retrying...")
        retry_prompt = f"{user_prompt}\n\n[SYSTEM NOTE: Your previous tool call failed validation: {str(val_err)}. Please re-extract carefully.]"
        
        try:
            if settings.ANTHROPIC_API_KEY:
                raw_llm_output_2, tool_input_2 = _call_claude_tool_use(
                    JOB_EXTRACTION_SYSTEM_PROMPT, retry_prompt, JOB_EXTRACTION_TOOL
                )
            else:
                raw_llm_output_2, tool_input_2 = _call_openai_tool_use(
                    JOB_EXTRACTION_SYSTEM_PROMPT, retry_prompt, JOB_EXTRACTION_TOOL
                )

            validated_2 = JobExtractionSchema.model_validate(tool_input_2)
            validated_2.required_skills = normalize_skills(validated_2.required_skills)
            validated_2.preferred_skills = normalize_skills(validated_2.preferred_skills)
            return validated_2.model_dump(), "success", f"Retry Output:\n{raw_llm_output_2}"
        except Exception as retry_err:
            logger.error(f"Job extraction attempt 2 failed: {str(retry_err)}")
            return {}, "failed", f"Validation failed after 2 attempts. Error: {str(retry_err)}\nRaw LLM: {raw_llm_output}"

    return {}, "failed", f"Failed to extract structured job details. Raw LLM response: {raw_llm_output}"
