from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.llm_test import router as llm_test_router

__all__ = ["health_router", "llm_test_router"]
