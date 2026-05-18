"""Pydantic models shared across the CharmAI API."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

# ---------------------------------------------------------------------------
# Validation constants
# ---------------------------------------------------------------------------

_MAX_TEXT_CHARS = 4000
_VALID_TONES = {"funny", "flirty", "confident", "direct", "sweet", "playful"}
_VALID_STYLES = {"calm", "bold", "casual", "warm", "witty"}
_VALID_CONFIDENCE = {"low", "medium", "high"}


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
    tone: str = Field(
        ...,
        description="User-selected reply tone: funny | flirty | confident | direct (required).",
    )
    user_style: str | None = Field(
        default=None,
        description="Optional personal style: calm | bold | casual | warm | witty.",
    )
    confidence_level: str = Field(
        ...,
        description="User-selected confidence: low | medium | high (required).",
    )
    analysis_debug: bool = Field(
        default=False,
        description="Include analyzer source and reasoning in the response.",
    )
    retrieval_debug: bool = Field(
        default=False,
        description="Include RAG retrieval explainability payload in the response.",
    )
    reply_count: int = Field(
        default=3,
        ge=3,
        le=12,
        description="How many distinct reply suggestions to generate and rank (default 3; max 12).",
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
    def _validate_tone(cls, v: str) -> str:
        t = (v or "").strip().lower()
        if not t:
            raise ValueError("tone is required — pick funny, flirty, confident, or direct.")
        if t not in _VALID_TONES:
            raise ValueError(
                f"Invalid tone {v!r}. Choose from: {', '.join(sorted(_VALID_TONES))}."
            )
        return t

    @field_validator("user_style")
    @classmethod
    def _validate_style(cls, v: str | None) -> str | None:
        if v is not None and v.lower() not in _VALID_STYLES:
            raise ValueError(
                f"Invalid user_style {v!r}. Choose from: {', '.join(sorted(_VALID_STYLES))}."
            )
        return v.lower() if v else v

    @field_validator("confidence_level")
    @classmethod
    def _validate_confidence(cls, v: str) -> str:
        c = (v or "").strip().lower()
        if not c:
            raise ValueError("confidence_level is required — pick low, medium, or high.")
        if c not in _VALID_CONFIDENCE:
            raise ValueError(
                f"Invalid confidence_level {v!r}. Choose from: {', '.join(sorted(_VALID_CONFIDENCE))}."
            )
        return c


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
        description="LLM provider: gemini | ollama:<model> | mock. Present when retrieval_debug=true.",
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
# /api/extract-from-image
# ---------------------------------------------------------------------------

_MAX_IMAGE_BASE64_CHARS = 6_000_000
_VALID_IMAGE_MIME = {"image/jpeg", "image/jpg", "image/png", "image/webp"}


class ExtractFromImageRequest(BaseModel):
    """Screenshot → conversation text (vision). Requires GEMINI_API_KEY on the server."""

    image_base64: str = Field(
        ...,
        description="Base64-encoded image bytes (no data: URL prefix required).",
    )
    mime_type: str = Field(
        default="image/jpeg",
        description="MIME type of the image: image/jpeg | image/png | image/webp.",
    )

    @field_validator("mime_type")
    @classmethod
    def _normalize_mime(cls, v: str) -> str:
        m = (v or "image/jpeg").strip().lower()
        if m == "image/jpg":
            m = "image/jpeg"
        if m not in _VALID_IMAGE_MIME:
            raise ValueError(
                f"mime_type must be one of: {', '.join(sorted(_VALID_IMAGE_MIME))}."
            )
        return m

    @field_validator("image_base64")
    @classmethod
    def _validate_b64(cls, v: str) -> str:
        s = (v or "").strip()
        if s.startswith("data:"):
            comma = s.find(",")
            if comma != -1:
                s = s[comma + 1 :].strip()
        if not s:
            raise ValueError("image_base64 cannot be empty.")
        if len(s) > _MAX_IMAGE_BASE64_CHARS:
            raise ValueError(
                f"image_base64 too large — max {_MAX_IMAGE_BASE64_CHARS} characters."
            )
        return s


class ExtractFromImageResponse(BaseModel):
    conversation_text: str = Field(description="Plain text extracted from the screenshot.")
    warning: str | None = Field(default=None, description="Non-fatal notice from the extractor.")


# ---------------------------------------------------------------------------
# /api/openers, /api/bio
# ---------------------------------------------------------------------------

_MAX_PROFILE_CHARS = 2800
_VALID_OPENER_TONES = {"funny", "flirty", "confident", "direct"}
_VALID_BIO_TEMPLATES = {
    "witty_minimal",
    "warm_story",
    "bold_confident",
    "playful",
    "authentic_soft",
}


class OpenerRequest(BaseModel):
    """First-message openers from a dating profile description."""

    profile_description: str = Field(..., description="Profile text, prompts, or bullet facts about the person.")
    tone: str = Field(..., description="funny | flirty | confident | direct")
    count: int = Field(default=6, ge=3, le=10, description="How many distinct openers to return.")

    @field_validator("profile_description")
    @classmethod
    def _strip_profile(cls, v: str) -> str:
        s = (v or "").strip()
        if not s:
            raise ValueError("profile_description cannot be empty.")
        if len(s) > _MAX_PROFILE_CHARS:
            raise ValueError(f"profile_description too long — max {_MAX_PROFILE_CHARS} characters.")
        return s

    @field_validator("tone")
    @classmethod
    def _tone(cls, v: str) -> str:
        t = (v or "").strip().lower()
        if t not in _VALID_OPENER_TONES:
            raise ValueError(
                f"Invalid tone {v!r}. Choose from: {', '.join(sorted(_VALID_OPENER_TONES))}."
            )
        return t


class OpenerResponse(BaseModel):
    openers: list[str] = Field(description="Suggested first messages / openers.")
    provider_used: str | None = Field(default=None, description="gemini | ollama:<model> | mock")


class BioRequest(BaseModel):
    """Dating app bio variants from rough notes or facts."""

    about_text: str = Field(..., description="Rough notes, interests, voice, or bullets to shape into a bio.")
    style_template: str = Field(
        ...,
        description=(
            "Bio style: witty_minimal | warm_story | bold_confident | playful | authentic_soft"
        ),
    )
    variant_count: int = Field(default=3, ge=1, le=5, description="How many bio variants to return.")

    @field_validator("about_text")
    @classmethod
    def _about(cls, v: str) -> str:
        s = (v or "").strip()
        if not s:
            raise ValueError("about_text cannot be empty.")
        if len(s) > _MAX_PROFILE_CHARS:
            raise ValueError(f"about_text too long — max {_MAX_PROFILE_CHARS} characters.")
        return s

    @field_validator("style_template")
    @classmethod
    def _tpl(cls, v: str) -> str:
        t = (v or "").strip().lower()
        if t not in _VALID_BIO_TEMPLATES:
            raise ValueError(
                f"Invalid style_template {v!r}. Choose from: {', '.join(sorted(_VALID_BIO_TEMPLATES))}."
            )
        return t


class BioResponse(BaseModel):
    bios: list[str] = Field(description="Ready-to-paste bio variants.")
    provider_used: str | None = Field(default=None, description="gemini | ollama:<model> | mock")


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    """Service health check response."""

    status: str
    service: str
    version: str
