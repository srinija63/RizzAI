"""POST /api/analyze — conversation analysis endpoint."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from schemas import AnalyzeRequest, ConversationAnalysis
from services.analyzer_service import analyze_conversation

logger = logging.getLogger("rizzai.api.analyze")

router = APIRouter(prefix="/api", tags=["analyze"])


@router.post(
    "/analyze",
    response_model=ConversationAnalysis,
    response_model_exclude_none=True,
    summary="Analyze conversation mood, intent, and interest level",
)
async def analyze(body: AnalyzeRequest) -> ConversationAnalysis:
    """
    Analyze a conversation snippet and return structured insights:
    - mood: playful | dry | interested | confused
    - intent: continue chat | ask out | recover | flirt
    - interest_level: low | medium | high
    - suggested_tone: funny | flirty | confident | direct | sweet

    Set analysis_debug=true to also receive source and reasoning.
    """
    logger.info(
        "[analyze] text=%r debug=%s",
        body.conversation_text[:60],
        body.analysis_debug,
    )

    try:
        result = analyze_conversation(
            body.conversation_text,
            analysis_debug=body.analysis_debug,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("[analyze] failed: %s", exc)
        raise HTTPException(
            status_code=502,
            detail=f"Analysis failed: {exc!s}",
        ) from exc

    logger.info(
        "[Analyzer] mood=%s  intent=%s  interest=%s  suggested_tone=%s  source=%s",
        result.get("mood"),
        result.get("intent"),
        result.get("interest_level"),
        result.get("suggested_tone"),
        result.get("source", "—"),
    )

    try:
        return ConversationAnalysis(**result)
    except Exception as exc:  # noqa: BLE001
        logger.error("[analyze] response serialization failed: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Analysis completed but response could not be serialized.",
        ) from exc
