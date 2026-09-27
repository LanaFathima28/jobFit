from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from app.services.llm_service import verify_claude_connection
from app.core.config import settings

router = APIRouter()


class LLMTestRequest(BaseModel):
    prompt: str = "Respond with: JobFit LLM integration working!"


@router.post("/llm-test", status_code=status.HTTP_200_OK)
@router.get("/llm-test", status_code=status.HTTP_200_OK)
def llm_test(request: LLMTestRequest = LLMTestRequest()):
    """
    Test endpoint verifying Anthropic Claude API connection.
    """
    if not settings.ANTHROPIC_API_KEY:
        return {
            "status": "warning",
            "message": "ANTHROPIC_API_KEY is not set in environment settings. Please set it in .env file to run LLM tests.",
            "response": None
        }

    try:
        response_text = verify_claude_connection(prompt=request.prompt)
        return {
            "status": "success",
            "message": "Claude API integration verified successfully",
            "response": response_text
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Claude API request failed: {str(e)}"
        )

