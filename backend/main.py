"""
CharmAI backend — FastAPI entrypoint.

Run locally:
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from routes.analyze import router as analyze_router
from routes.chat import router as chat_router
from routes.health import router as health_router
from routes.vision import router as vision_router
from routes.writing import router as writing_router
from services.config import settings
from services.embeddings import preload_embeddings

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("rizzai.main")


# ---------------------------------------------------------------------------
# App lifecycle
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("CharmAI backend starting up")
    if settings.preload_embeddings:
        try:
            preload_embeddings()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Embedding preload failed (%s) — will load on first RAG request", exc)
    logger.info(
        "Reply pipeline: skip_llm_analyze=%s preload_embeddings=%s",
        settings.skip_llm_analyze,
        settings.preload_embeddings,
    )
    yield
    logger.info("CharmAI backend shutting down")


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

app = FastAPI(
    title="CharmAI API",
    description=(
        "Advanced AI dating assistant — reply suggestions, conversation analysis, "
        "and RAG-powered ranking."
    ),
    version="0.2.0",
    lifespan=lifespan,
)

# Allow Expo web, native dev clients, and local testing tools
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request logging middleware
# ---------------------------------------------------------------------------

@app.middleware("http")
async def _log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "%s %s → %d  (%.0fms)",
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )
    return response


# ---------------------------------------------------------------------------
# Global error handlers
# ---------------------------------------------------------------------------

@app.exception_handler(RequestValidationError)
async def _validation_error_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    """Return readable 422 messages instead of FastAPI's default nested structure."""
    errors = [
        f"{' → '.join(str(loc) for loc in e['loc'])}: {e['msg']}"
        for e in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={"error": "Validation failed", "detail": errors},
    )


@app.exception_handler(Exception)
async def _unhandled_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    """Catch anything that slips through route handlers."""
    logger.error("Unhandled exception: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": "An unexpected error occurred. Please try again.",
        },
    )


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(health_router)
app.include_router(chat_router)
app.include_router(analyze_router)
app.include_router(vision_router)
app.include_router(writing_router)


# ---------------------------------------------------------------------------
# Root
# ---------------------------------------------------------------------------

@app.get("/", include_in_schema=False)
async def root():
    return {
        "service": "CharmAI",
        "version": "0.2.0",
        "docs": "/docs",
        "health": "/health",
        "endpoints": [
            "POST /api/reply",
            "POST /api/analyze",
            "POST /api/extract-from-image",
            "POST /api/openers",
            "POST /api/bio",
            "GET  /health",
        ],
    }
