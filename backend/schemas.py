"""Pydantic models shared across the API."""

from pydantic import BaseModel, Field


class ReplyRequest(BaseModel):
    """User message and optional tone for the dating assistant."""

    message: str = Field(
        ...,
        min_length=1,
        max_length=4000,
        description="What you want to say or the situation to respond to.",
    )
    tone: str | None = Field(
        default="playful",
        description="e.g. playful, confident, polite, flirty",
    )
    retrieval_debug: bool = Field(
        default=False,
        description="Include retrieval reasoning payload when true.",
    )


class RetrievalDebugItem(BaseModel):
    """Explainability details for one retrieved pattern."""

    pattern_id: str | None = None
    tone: str | None = None
    situation: str | None = None
    score: float | None = None
    reason: str | None = None


class ReplyResponse(BaseModel):
    """Generated reply lines from the assistant."""

    replies: list[str] = Field(
        ...,
        description="Short reply ideas the user can send.",
    )
    labels: list[str] = Field(
        ...,
        description="Style tag for each reply, e.g. playful, bold, safe, smooth.",
    )
    suggestions: list[str] = Field(
        ...,
        description="Backward-compatible alias of replies.",
    )
    note: str | None = Field(
        default=None,
        description="Optional tip from the assistant.",
    )
    retrieval_debug: list[RetrievalDebugItem] | None = Field(
        default=None,
        description="Optional explainability payload for retrieved examples.",
    )


class HealthResponse(BaseModel):
    """Service health check."""

    status: str
    service: str
