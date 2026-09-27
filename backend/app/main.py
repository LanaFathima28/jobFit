from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.core.exceptions import (
    http_exception_handler,
    validation_exception_handler,
    global_exception_handler
)
from app.db.session import engine
from app.db.base import Base
from app.api.v1.router import api_router
from app.api.v1.endpoints.health import router as health_router

# Ensure tables are created automatically if needed
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    description="Backend API for AI-powered Resume Ranking & Interview Question Generator"
)

# Register Global Exception Handlers for Standardized Error Responses
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register top-level /health endpoint as required by Phase 0 spec
app.include_router(health_router, tags=["Health"])

# Register API v1 router and top-level /api router alias
app.include_router(api_router, prefix=settings.API_V1_STR)
app.include_router(api_router, prefix="/api")


@app.get("/")
def root():
    return {
        "message": "Welcome to JobFit AI API",
        "docs": "/docs",
        "health": "/health",
        "version": settings.VERSION
    }
