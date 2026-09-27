from typing import Any, Dict, List, Optional
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)


class ErrorDetail(BaseModel):
    field: Optional[str] = None
    issue: str


class ErrorResponseBody(BaseModel):
    code: str
    message: str
    details: Optional[List[ErrorDetail]] = None


class StandardErrorResponse(BaseModel):
    error: ErrorResponseBody


def create_error_response(
    code: str,
    message: str,
    status_code: int,
    details: Optional[List[Dict[str, Any]]] = None
) -> JSONResponse:
    parsed_details = None
    if details:
        parsed_details = [
            {"field": d.get("field"), "issue": str(d.get("issue", ""))}
            for d in details
        ]

    content = {
        "error": {
            "code": code,
            "message": message,
            "details": parsed_details
        }
    }
    return JSONResponse(status_code=status_code, content=content)


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    code_map = {
        status.HTTP_400_BAD_REQUEST: "BAD_REQUEST",
        status.HTTP_401_UNAUTHORIZED: "UNAUTHORIZED",
        status.HTTP_403_FORBIDDEN: "FORBIDDEN",
        status.HTTP_404_NOT_FOUND: "NOT_FOUND",
        status.HTTP_429_TOO_MANY_REQUESTS: "RATE_LIMIT_EXCEEDED",
        status.HTTP_422_UNPROCESSABLE_ENTITY: "VALIDATION_ERROR",
    }
    code = code_map.get(exc.status_code, "HTTP_ERROR")
    message = str(exc.detail) if exc.detail else "An HTTP error occurred."
    return create_error_response(code=code, message=message, status_code=exc.status_code)


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    details = []
    for err in exc.errors():
        field_path = " -> ".join([str(loc) for loc in err.get("loc", []) if loc != "body"])
        details.append({
            "field": field_path or "body",
            "issue": err.get("msg", "Invalid value")
        })

    return create_error_response(
        code="VALIDATION_ERROR",
        message="Request payload validation failed.",
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        details=details
    )


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(f"Unhandled server error at {request.url.path}: {str(exc)}", exc_info=True)
    return create_error_response(
        code="INTERNAL_SERVER_ERROR",
        message="An internal server error occurred while processing your request.",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
    )
