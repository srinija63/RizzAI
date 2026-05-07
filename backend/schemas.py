"""Pydantic models shared across the CharmAI API."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

# ---------------------------------------------------------------------------
# Validation constants
# ---------------------------------------------------------------------------

_MAX_TEXT_CHARS = 4000
_VALID_TONES = {"funny", "flirty", "confident", "direct", "sweet", "playful"}
_VALID_STYLES = {"calm", "bold", "casual", "warm", "witty"}


# ---------------------------------------------------------------------------
# Shared sub-models
# ---------------------------------------------------------------------------

class ConversationAnalysis(BaseModel):
    """Structured analyzer output for the input conversation."""

    mood: str = Field(description="Detected emotional mood: playful | dry | interested | confused")
    intent: str = Field(description="Inferred intent: continue chat | ask out | recover | flirt")
    interest_level: str = Field(description="Estimated interest: low | medium | high")
    suggested_tone: str = Field(description="Recommended reply tone based on analysis")
    source: str | None = Field(default=None, description="Analysis source: rule-based | llm | llm+guardrail | post-validation")
    reason: str | None = Field(default=None, description="Short reasoning string when analysis_debug is true")


class ReplyMetrics(BaseModel):
    """Per-metric breakdown for a single reply."""

    naturalness: int = Field(ge=1, le=10, description="Sounds like a real person (1–10)")
    confidence: int = Field(ge=1, le=10, description="Not needy or desperate (1–10)")
    tone_match: int = Field(ge=1, le=10, description="Aligns with selected tone (1–10)")
    respectfulness: int = Field(ge=1, le=10, description="Not pushy or manipulative (1–10)")


class RankedReplyItem(BaseModel):
    """A single generated reply with quality score and metadata."""

    text: str = Field(description="The reply text to send")
    score: int = Field(ge=1, le=10, description="Overall quality score (1–10)")
    metrics: ReplyMetrics = Field(description="Breakdown by naturalness, confidence, tone match, respectfulness")
    label: str = Field(description="Style tag: playful | bold | smooth | safe | sweet | direct")
    explanation: str = Field(description="Short coaching note about this reply")
    rank: int = Field(ge=1, description="Position in ranked list (1 = best)")


class RetrievalDebugItem(BaseModel):
    """Explainability details for one retrieved RAG pattern."""

    pattern_id: str | None = None
    tone: str | None = None
    situation: str | None = None
    score: float | None = None
    reason: str | None = None


class ResponseMeta(BaseModel):
    """Pipeline execution metadata returned on every /api/reply response."""

    latency_ms: int = Field(description="Total wall-clock time for the request in milliseconds.")
    steps: list[str] = Field(
        description="Ordered list of pipeline steps that completed: analyze | retrieve | generate | rank."
    )
    step_times: dict[str, int] = Field(
        default_factory=dict,
        description="Per-step latency in milliseconds for analyze/retrieve/generate/rank.",
    )


# ---------------------------------------------------------------------------
# /api/reply
# ---------------------------------------------------------------------------

class ReplyRequest(BaseModel):
    """Request payload for reply generation."""

    conversation_text: str = Field(
        ...,
        description="The conversation or message you want to respond to.",
    )
    tone: str | None = Field(
        default=None,
        description="Preferred reply tone. One of: funny | flirty | confident | direct | sweet | playful. "
                    "If omitted, the analyzer's suggested tone is used.",
    )
    user_style: str | None = Field(
        default="calm",
        description="Your personal communication style: calm | bold | casual | warm | witty.",
    )
    analysis_debug: bool = Field(
        default=False,
        description="Include analyzer source and reasoning in the response.",
    )
    retrieval_debug: bool = Field(
        default=False,
        description="Include RAG retrieval explainability payload in the response.",
    )

    @field_validator("conversation_text")
    @classmethod
    def _validate_text(cls, v: str) -> str:
        # Empty check is enforced at the route level (returns 400, not 422).
        if len(v.strip()) > _MAX_TEXT_CHARS:
            raise ValueError(
                f"conversation_text too long — max {_MAX_TEXT_CHARS} characters "
                f"(received {len(v.strip())})."
            )
        return v.strip()

    @field_validator("tone")
    @classmethod
    def _validate_tone(cls, v: str | None) -> str | None:
        if v is not None and v.lower() not in _VALID_TONES:
            raise ValueError(
                f"Invalid tone {v!r}. Choose from: {', '.join(sorted(_VALID_TONES))}."
            )
        return v.lower() if v else v

    @field_validator("user_style")
    @classmethod
    def _validate_style(cls, v: str | None) -> str | None:
        if v is not None and v.lower() not in _VALID_STYLES:
            raise ValueError(
                f"Invalid user_style {v!r}. Choose from: {', '.join(sorted(_VALID_STYLES))}."
            )
        return v.lower() if v else v


class ReplyResponse(BaseModel):
    """Full response from the reply generation endpoint."""

    request_id: str | None = Field(
        default=None,
        description="Unique request identifier for tracing logs and responses.",
    )
    analysis: ConversationAnalysis = Field(
        description="Conversation analysis that guided tone and strategy.",
    )
    replies: list[RankedReplyItem] = Field(
        description="Ranked reply suggestions, best first.",
    )
    top_pick_reason: str = Field(
        description="Why the top reply was ranked #1.",
    )
    provider_used: str | None = Field(
        default=None,
        description="LLM provider: openai | ollama:<model> | mock. Present when retrieval_debug=true.",
    )
    retrieval_debug: list[RetrievalDebugItem] | None = Field(
        default=None,
        description="RAG retrieval explainability payload. Present when retrieval_debug=true.",
    )
    warning: str | None = Field(
        default=None,
        description="Non-fatal warning, e.g. LLM unavailable — fallback replies returned.",
    )
    mode: str | None = Field(
        default=None,
        description="Response mode: normal | fallback.",
    )
    meta: ResponseMeta = Field(
        description="Pipeline execution metadata: latency and steps completed.",
    )


# ---------------------------------------------------------------------------
# /api/analyze
# ---------------------------------------------------------------------------

class AnalyzeRequest(BaseModel):
    """Request payload for the conversation analysis endpoint."""

    conversation_text: str = Field(
        ...,
        description="Conversation text to analyze for mood, intent, and interest level.",
    )
    analysis_debug: bool = Field(
        default=False,
        description="Include analyzer source and short reasoning when true.",
    )

    @field_validator("conversation_text")
    @classmethod
    def _validate_text(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("conversation_text cannot be empty.")
        if len(stripped) > _MAX_TEXT_CHARS:
            raise ValueError(
                f"conversation_text too long — max {_MAX_TEXT_CHARS} characters."
            )
        return stripped


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    """Service health check response."""

    status: str
    service: str
    version: str
