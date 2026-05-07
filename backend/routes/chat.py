"""POST /api/reply — reply generation endpoint."""

from __future__ import annotations

import logging
import time

from fastapi import APIRouter, HTTPException, Request

from schemas import (
    ConversationAnalysis,
    RankedReplyItem,
    ReplyMetrics,
    ReplyRequest,
    ReplyResponse,
    ResponseMeta,
    RetrievalDebugItem,
)
from services.analyzer_service import analyze_conversation
from services.llm_service import get_last_provider_name
from services.ranking_service import rank_replies
from services.rizz_service import generate_rag_replies

logger = logging.getLogger("rizzai.api.reply")

router = APIRouter(prefix="/api", tags=["reply"])

# Labels assigned by position in the ranked list.
_RANK_LABELS = ["smooth", "bold", "playful", "safe", "sweet"]

# Safe fallback replies returned when the full pipeline fails.
_FALLBACK_REPLIES = [
    "Haha fair enough — what are you up to today?",
    "Low-key curious now. Give me one fun detail about you.",
    "Nice, keeping it simple works. Want to keep chatting?",
    "You seem cool. Coffee person or tea person?",
    "I can work with this vibe — what should I know next?",
]


def _label_for_rank(rank: int) -> str:
    idx = (rank - 1) % len(_RANK_LABELS)
    return _RANK_LABELS[idx]


def _build_top_pick_reason(item: RankedReplyItem) -> str:
    return f"Ranked #1 with {item.score}/10 — {item.explanation}"


def _build_fallback_response(warning: str) -> ReplyResponse:
    """Return a valid ReplyResponse with safe mock replies and a warning field."""
    items = [
        RankedReplyItem(
            text=text,
            score=6,
            metrics=ReplyMetrics(naturalness=7, confidence=6, tone_match=6, respectfulness=9),
            label=_label_for_rank(rank),
            explanation="Fallback reply — AI generation temporarily unavailable.",
            rank=rank,
        )
        for rank, text in enumerate(_FALLBACK_REPLIES, start=1)
    ]
    return ReplyResponse(
        replies=items,
        top_pick_reason="Fallback reply used — LLM provider unavailable.",
        warning=warning,
    )


@router.post(
    "/reply",
    response_model=ReplyResponse,
    response_model_exclude_none=True,
    summary="Generate ranked dating reply suggestions",
)
async def create_reply(body: ReplyRequest, request: Request) -> ReplyResponse:
    """
    Full pipeline:
    1. Analyze conversation mood / intent / tone
    2. Generate reply candidates via RAG + LLM
    3. Rank and diversify replies
    4. Return structured, ranked response
    """
    _t_start = time.perf_counter()
    _steps: list[str] = []

    # ── Guard: empty input ────────────────────────────────────────────────
    if not body.conversation_text:
        logger.warning("[reply] rejected — empty conversation_text")
        raise HTTPException(
            status_code=400,
            detail="conversation_text cannot be empty. Please provide the message you want to respond to.",
        )

    logger.info(
        "[reply] text=%r tone=%s style=%s debug=%s",
        body.conversation_text[:60],
        body.tone,
        body.user_style,
        body.retrieval_debug,
    )

    # ── Step 1: Conversation analysis ────────────────────────────────────
    try:
        raw_analysis = analyze_conversation(
            body.conversation_text,
            analysis_debug=body.analysis_debug,
        )
        logger.info(
            "[Analyzer] mood=%s  intent=%s  interest=%s  suggested_tone=%s",
            raw_analysis.get("mood"),
            raw_analysis.get("intent"),
            raw_analysis.get("interest_level"),
            raw_analysis.get("suggested_tone"),
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("[reply] analyzer failed (%s) — using defaults", exc)
        raw_analysis = {
            "mood": "dry",
            "intent": "continue chat",
            "interest_level": "medium",
            "suggested_tone": "playful",
        }
    _steps.append("analyze")

    # Resolve effective tone: user preference → analyzer suggestion → default
    effective_tone = (
        body.tone
        or raw_analysis.get("suggested_tone")
        or "playful"
    )
    # If conversation is dry/confused, avoid overly flirty tone
    if (
        raw_analysis.get("mood") in {"dry", "confused"}
        and effective_tone in {"flirty", "funny"}
        and not body.tone  # only override if user didn't explicitly choose
    ):
        effective_tone = raw_analysis.get("suggested_tone", "playful")

    logger.info("[reply] effective_tone=%s", effective_tone)

    # ── Step 2: Generate reply candidates ────────────────────────────────
    try:
        result = await generate_rag_replies(
            conversation_text=body.conversation_text,
            tone=effective_tone,
            user_style=body.user_style or "calm",
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("[reply] generation failed (%s) — returning fallback response", type(exc).__name__)
        return _build_fallback_response(
            "Reply generation is temporarily unavailable. These are placeholder suggestions."
        )

    _steps.append("retrieve")
    _steps.append("generate")

    raw_replies: list[str] = result.get("replies") or []
    if not raw_replies:
        logger.warning("[reply] generation returned empty replies — returning fallback response")
        return _build_fallback_response(
            "No replies could be generated. These are placeholder suggestions."
        )

    logger.info("[Pipeline] generated=%d raw replies  tone=%s", len(raw_replies), effective_tone)

    # ── Step 3: Rank and diversify ────────────────────────────────────────
    intent = raw_analysis.get("intent", "")
    try:
        ranked = rank_replies(raw_replies, tone=effective_tone, intent=intent)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[reply] ranking failed (%s) — using unranked order", exc)
        # Fallback: wrap raw replies without scores
        ranked = [
            {
                "reply": r,
                "score": 7,
                "metrics": {
                    "naturalness": 7,
                    "confidence": 7,
                    "tone_match": 7,
                    "respectfulness": 7,
                },
                "explanation": "Decent reply.",
            }
            for r in raw_replies[:5]
        ]

    _steps.append("rank")
    logger.info("[Ranking] completed  top=%d  intent=%s", len(ranked), intent or "—")

    # ── Step 4: Build structured reply items ─────────────────────────────
    reply_items: list[RankedReplyItem] = []
    labels_from_service: list[str] = result.get("labels") or []

    for i, ranked_item in enumerate(ranked):
        rank = i + 1
        label = (
            labels_from_service[i]
            if i < len(labels_from_service)
            else _label_for_rank(rank)
        )
        metrics = ranked_item.get("metrics", {})
        reply_items.append(
            RankedReplyItem(
                text=ranked_item["reply"],
                score=ranked_item["score"],
                metrics=ReplyMetrics(
                    naturalness=metrics.get("naturalness", 7),
                    confidence=metrics.get("confidence", 7),
                    tone_match=metrics.get("tone_match", 7),
                    respectfulness=metrics.get("respectfulness", 7),
                ),
                label=label,
                explanation=ranked_item.get("explanation", "Decent reply."),
                rank=rank,
            )
        )

    if not reply_items:
        logger.warning("[reply] ranking produced no items — returning fallback response")
        return _build_fallback_response(
            "Reply ranking failed. These are placeholder suggestions."
        )

    top_pick_reason = _build_top_pick_reason(reply_items[0])
    logger.info("[Ranking] top_score=%d  top=%r", reply_items[0].score, reply_items[0].text[:50])

    _latency_ms = round((time.perf_counter() - _t_start) * 1000)
    _meta = ResponseMeta(latency_ms=_latency_ms, steps=_steps)
    logger.info("[meta] latency=%dms  steps=%s", _latency_ms, _steps)

    # ── Step 5: Build optional debug payloads ────────────────────────────
    retrieval_debug_payload = None
    if body.retrieval_debug:
        retrieval_debug_payload = [
            RetrievalDebugItem(
                pattern_id=item.get("id"),
                tone=item.get("tone"),
                situation=item.get("situation"),
                score=item.get("relevance_score"),
                reason=(item.get("retrieval_debug") or {}).get("reason"),
            )
            for item in result.get("inspiration_examples", [])
        ]

    provider = get_last_provider_name() if body.retrieval_debug else None

    # ── Step 6: Build analysis for response ──────────────────────────────
    analysis_out = None
    try:
        analysis_out = ConversationAnalysis(**raw_analysis)
    except Exception:  # noqa: BLE001
        pass  # non-critical — omit if fields don't match

    return ReplyResponse(
        analysis=analysis_out,
        replies=reply_items,
        top_pick_reason=top_pick_reason,
        provider_used=provider,
        retrieval_debug=retrieval_debug_payload,
        warning=None,
        meta=_meta,
    )


