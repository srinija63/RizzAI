"""GET /health — liveness probe."""

from __future__ import annotations

from fastapi import APIRouter

from schemas import HealthResponse

router = APIRouter(tags=["health"])

_VERSION = "0.2.0"


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Liveness probe",
)
async def health() -> HealthResponse:
    """Returns service status. Use for deployment health checks and local verification."""
    return HealthResponse(
        status="ok",
        service="charmai-backend",
        version=_VERSION,
    )
