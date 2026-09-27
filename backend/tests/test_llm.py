import pytest
from app.core.config import settings
from app.services.llm_service import verify_claude_connection


def test_llm_service_connection():
    """
    Test minimal call to Anthropic Claude API using verify_claude_connection.
    Skipped automatically if ANTHROPIC_API_KEY is not configured.
    """
    if not settings.ANTHROPIC_API_KEY:
        pytest.skip("Skipping LLM integration test because ANTHROPIC_API_KEY is not set.")

    response = verify_claude_connection(prompt="Say 'Integration Test Success'")
    assert response is not None
    assert len(response.strip()) > 0

