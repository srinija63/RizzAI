"""Health check."""

from fastapi import APIRouter

from schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Liveness probe for deployment and local checks."""
    return HealthResponse(status="ok", service="rizzai-backend")
