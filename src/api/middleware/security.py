import os

import structlog
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

logger = structlog.get_logger()

API_KEY_NAME = "X-API-KEY"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)


async def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    """
    Validates presence and match of client X-API-KEY header.
    Raises 403 Forbidden for missing or invalid keys.
    """
    expected_key = os.getenv("API_KEY", "fraud_dev_sec_key")

    if not api_key:
        logger.warning("Security validation failed: Missing API Key header", header=API_KEY_NAME)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="API Key header is missing."
        )

    if api_key != expected_key:
        logger.warning(
            "Security validation failed: Invalid API Key",
            provided_prefix=api_key[:4] if len(api_key) > 4 else "...",
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid API Key.")

    return api_key
