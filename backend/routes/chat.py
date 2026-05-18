"""POST /api/reply — reply generation endpoint."""

from __future__ import annotations

import asyncio
import logging
import time
from uuid import uuid4

from services.llm_service import pad_unique_replies

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
from services.analyzer_service import analyze_conversation, analyze_conversation_fast
from services.config import settings
from services.llm_service import get_last_provider_name
from services.ranking_service import rank_replies
from services.rizz_service import generate_rag_replies

logger = logging.getLogger("rizzai.api.reply")

router = APIRouter(prefix="/api", tags=["reply"])

# Labels assigned by position in the ranked list.
_RANK_LABELS = ["smooth", "bold", "playful", "safe", "sweet"]
_RANKING_TIMEOUT_SECONDS = 12

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


def _safe_analysis(raw_analysis: dict) -> ConversationAnalysis:
    """Best-effort conversion of analysis dict into a valid response model."""
    try:
        return ConversationAnalysis(**raw_analysis)
    except Exception:  # noqa: BLE001
        return ConversationAnalysis(
            mood="dry",
            intent="continue chat",
            interest_level="medium",
            suggested_tone="playful",
        )


def _build_fallback_response(
    *,
    request_id: str,
    analysis: ConversationAnalysis,
    provider_used: str,
    steps: list[str],
    step_times: dict[str, int],
    started_at: float,
    warning: str,
) -> ReplyResponse:
    """Return a valid ReplyResponse with safe mock replies and a warning field."""
    normalized_step_times = {
        "analyze": step_times.get("analyze", 0),
        "retrieve": step_times.get("retrieve", 0),
        "generate": step_times.get("generate", 0),
        "rank": step_times.get("rank", 0),
    }
    normalized_steps = [step for step in ["analyze", "retrieve", "generate", "rank"] if step in steps]
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
    latency_ms = round((time.perf_counter() - started_at) * 1000)
    return ReplyResponse(
        request_id=request_id,
        analysis=analysis,
        replies=items,
        top_pick_reason="Fallback reply used — LLM provider unavailable.",
        provider_used=provider_used,
        warning=warning,
        mode="fallback",
        meta=ResponseMeta(latency_ms=latency_ms, steps=normalized_steps, step_times=normalized_step_times),
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
    request_id = str(uuid4())
    _steps: list[str] = []
    _step_times: dict[str, int] = {}

    # ── Guard: empty input ────────────────────────────────────────────────
    if not body.conversation_text:
        logger.warning("[Request %s] [reply] rejected — empty conversation_text", request_id)
        raise HTTPException(
            status_code=400,
            detail={
                "request_id": request_id,
                "error": "conversation_text cannot be empty. Please provide the message you want to respond to.",
            },
        )

    logger.info(
        "[Request %s] [reply] text=%r tone=%s style=%s confidence=%s reply_count=%s debug=%s",
        request_id,
        body.conversation_text[:60],
        body.tone,
        body.user_style,
        body.confidence_level,
        body.reply_count,
        body.retrieval_debug,
    )

    # ── Step 1: Conversation analysis ────────────────────────────────────
    _t_step = time.perf_counter()
    try:
        if settings.skip_llm_analyze:
            raw_analysis = analyze_conversation_fast(
                body.conversation_text,
                analysis_debug=body.analysis_debug,
            )
        else:
            raw_analysis = analyze_conversation(
                body.conversation_text,
                analysis_debug=body.analysis_debug,
            )
        logger.info(
            "[Request %s] [Analyzer] mood=%s intent=%s interest=%s suggested_tone=%s",
            request_id,
            raw_analysis.get("mood"),
            raw_analysis.get("intent"),
            raw_analysis.get("interest_level"),
            raw_analysis.get("suggested_tone"),
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("[Request %s] [Analyzer] failed (%s) — using defaults", request_id, exc)
        raw_analysis = {
            "mood": "dry",
            "intent": "continue chat",
            "interest_level": "medium",
            "suggested_tone": "playful",
        }
    _steps.append("analyze")
    _step_times["analyze"] = round((time.perf_counter() - _t_step) * 1000)
    analysis_out = _safe_analysis(raw_analysis)

    # Tone and confidence come only from the user (Reply Setup screen).
    effective_tone = body.tone
    logger.info("[Request %s] [reply] user_tone=%s confidence=%s", request_id, effective_tone, body.confidence_level)

    # ── Step 2: Generate reply candidates ────────────────────────────────
    _t_step = time.perf_counter()
    try:
        result = await generate_rag_replies(
            conversation_text=body.conversation_text,
            tone=effective_tone,
            user_style=body.user_style or "",
            confidence_level=body.confidence_level,
            reply_count=body.reply_count,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "[Request %s] [LLM] generation failed (%s) — using fallback",
            request_id,
            type(exc).__name__,
        )
        _step_times["retrieve"] = 0
        _step_times["generate"] = round((time.perf_counter() - _t_step) * 1000)
        return _build_fallback_response(
            request_id=request_id,
            analysis=analysis_out,
            provider_used="mock",
            steps=["analyze", "retrieve", "generate"],
            step_times=_step_times,
            started_at=_t_start,
            warning="LLM unavailable, using fallback replies",
        )

    _steps.append("retrieve")
    _steps.append("generate")
    rag_time_ms = round((time.perf_counter() - _t_step) * 1000)
    retrieve_ms = max(1, round(rag_time_ms * 0.35))
    _step_times["retrieve"] = retrieve_ms
    _step_times["generate"] = max(1, rag_time_ms - retrieve_ms)

    raw_replies: list[str] = result.get("replies") or []
    if not raw_replies:
        logger.warning(
            "[Request %s] [LLM] empty generation result — using fallback",
            request_id,
        )
        return _build_fallback_response(
            request_id=request_id,
            analysis=analysis_out,
            provider_used="mock",
            steps=["analyze", "retrieve", "generate"],
            step_times=_step_times,
            started_at=_t_start,
            warning="LLM unavailable, using fallback replies",
        )

    logger.info(
        "[Request %s] [RAG] retrieved=%d",
        request_id,
        len(result.get("inspiration_examples", [])),
    )
    logger.info("[Request %s] [Pipeline] generated=%d tone=%s", request_id, len(raw_replies), effective_tone)

    # ── Step 3: Rank and diversify ────────────────────────────────────────
    intent = raw_analysis.get("intent", "")
    _t_step = time.perf_counter()
    try:
        ranked = await asyncio.wait_for(
            asyncio.to_thread(
                rank_replies,
                raw_replies,
                tone=effective_tone,
                intent=intent,
                top_n=body.reply_count,
            ),
            timeout=_RANKING_TIMEOUT_SECONDS,
        )
    except TimeoutError:
        logger.warning(
            "[Request %s] [Ranking] timed out after %ss — using unranked order",
            request_id,
            _RANKING_TIMEOUT_SECONDS,
        )
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
            for r in raw_replies[:body.reply_count]
        ]
    except Exception as exc:  # noqa: BLE001
        logger.warning("[Request %s] [Ranking] failed (%s) — using unranked order", request_id, exc)
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
            for r in raw_replies[:body.reply_count]
        ]

    _steps.append("rank")
    _step_times["rank"] = round((time.perf_counter() - _t_step) * 1000)
    logger.info("[Request %s] [Ranking] completed top=%d intent=%s", request_id, len(ranked), intent or "-")

    # Ensure we return the requested count with unique text (ranking may drop similar lines).
    ranked_texts = [str(item.get("reply", "")).strip() for item in ranked if str(item.get("reply", "")).strip()]
    if len(ranked_texts) < body.reply_count:
        pool = pad_unique_replies(raw_replies + ranked_texts, count=body.reply_count)
        seen = {t.lower() for t in ranked_texts}
        for text in pool:
            if len(ranked_texts) >= body.reply_count:
                break
            if text.lower() not in seen:
                ranked.append(
                    {
                        "reply": text,
                        "score": 6,
                        "metrics": {
                            "naturalness": 7,
                            "confidence": 6,
                            "tone_match": 6,
                            "respectfulness": 8,
                        },
                        "explanation": "Additional option.",
                    }
                )
                ranked_texts.append(text)
                seen.add(text.lower())
    ranked = ranked[: body.reply_count]

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
        logger.warning("[Request %s] [Ranking] produced no items — using fallback", request_id)
        return _build_fallback_response(
            request_id=request_id,
            analysis=analysis_out,
            provider_used="mock",
            steps=_steps,
            step_times=_step_times,
            started_at=_t_start,
            warning="LLM unavailable, using fallback replies",
        )

    top_pick_reason = _build_top_pick_reason(reply_items[0])
    logger.info("[Request %s] [Ranking] top_score=%d top=%r", request_id, reply_items[0].score, reply_items[0].text[:50])

    _latency_ms = round((time.perf_counter() - _t_start) * 1000)
    _meta = ResponseMeta(latency_ms=_latency_ms, steps=_steps, step_times=_step_times)
    logger.info("[Request %s] [meta] latency=%dms steps=%s", request_id, _latency_ms, _steps)

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

    provider = get_last_provider_name() or "mock"
    logger.info("[Request %s] [LLM] provider=%s", request_id, provider)

    return ReplyResponse(
        request_id=request_id,
        analysis=analysis_out,
        replies=reply_items,
        top_pick_reason=top_pick_reason,
        provider_used=provider,
        retrieval_debug=retrieval_debug_payload,
        warning=None,
        mode="normal",
        meta=_meta,
    )


