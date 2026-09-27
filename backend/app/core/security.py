from typing import Optional
from fastapi import Header, HTTPException, status
from app.core.config import settings


async def verify_api_key(x_api_key: Optional[str] = Header(None)) -> Optional[str]:
    """
    Validates single-user API Key from 'X-API-Key' header.
    If settings.API_KEY is not configured (empty string), authentication is bypassed.
    """
    if not settings.API_KEY:
        return x_api_key

    if not x_api_key or x_api_key != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key header ('X-API-Key')."
        )

    return x_api_key
