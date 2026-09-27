from fastapi import APIRouter
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.llm_test import router as llm_test_router
from app.api.v1.endpoints.candidates import router as candidates_router
from app.api.v1.endpoints.jobs import router as jobs_router
from app.api.v1.endpoints.matches import router as matches_router
from app.api.v1.endpoints.interviews import router as interviews_router
from app.api.v1.endpoints.config import router as config_router
from app.api.v1.endpoints.tasks import router as tasks_router

api_router = APIRouter()

api_router.include_router(health_router, tags=["Health"])
api_router.include_router(llm_test_router, tags=["LLM Verification"])
api_router.include_router(candidates_router)
api_router.include_router(jobs_router)
api_router.include_router(matches_router)
api_router.include_router(interviews_router)
api_router.include_router(config_router)
api_router.include_router(tasks_router)
