"""
RizzAI backend — FastAPI entrypoint.

Run locally: uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.chat import router as chat_router
from routes.health import router as health_router
from services.config import settings


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Startup/shutdown hooks (extend if you add DB pools, etc.)."""
    yield


app = FastAPI(
    title="RizzAI API",
    description="Advanced AI dating assistant — reply suggestions API",
    version="0.1.0",
    lifespan=lifespan,
)

# Allow Expo web and native dev clients to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(chat_router)


@app.get("/")
async def root():
    """API root with a short hint."""
    return {
        "service": "RizzAI",
        "docs": "/docs",
        "health": "/health",
    }
