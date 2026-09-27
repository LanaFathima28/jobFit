import logging
import anthropic
from app.core.config import settings

logger = logging.getLogger(__name__)


def verify_claude_connection(prompt: str = "Respond with: JobFit LLM integration working!") -> str:
    """
    Utility service to verify connectivity with the Anthropic Claude API.
    Used for Phase 0 verification endpoint and test suite.
    """
    if not settings.ANTHROPIC_API_KEY:
        raise ValueError(
            "ANTHROPIC_API_KEY is not configured in environment variables or .env file."
        )

    try:
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=100,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        # Extract text response from blocks
        if response.content and len(response.content) > 0:
            return response.content[0].text
        return "No response content received from Claude API."
    except Exception as e:
        logger.error(f"Error connecting to Anthropic Claude API: {str(e)}")
        raise e


# Alias for compatibility
test_claude_connection = verify_claude_connection


