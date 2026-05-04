"""Chat / reply generation endpoints."""

from fastapi import APIRouter, HTTPException

from schemas import ReplyRequest, ReplyResponse
from services.rizz_service import generate_rag_replies

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/reply", response_model=ReplyResponse)
async def create_reply(body: ReplyRequest) -> ReplyResponse:
    """Generate dating reply suggestions from the user's message."""
    try:
        result = await generate_rag_replies(
            conversation_text=body.message,
            tone=body.tone or "playful",
            user_style="calm",
        )
    except Exception as exc:  # noqa: BLE001 — surface provider errors cleanly
        raise HTTPException(
            status_code=502,
            detail=f"Could not generate replies: {exc!s}",
        ) from exc

    debug_payload = None
    if body.retrieval_debug:
        debug_payload = [
            {
                "pattern_id": item.get("id"),
                "tone": item.get("tone"),
                "situation": item.get("situation"),
                "score": item.get("relevance_score"),
                "reason": item.get("retrieval_debug", {}).get("reason"),
            }
            for item in result.get("inspiration_examples", [])
        ]

    return ReplyResponse(
        replies=result["replies"],
        labels=result["labels"],
        suggestions=result["replies"],
        note=result.get("note"),
        retrieval_debug=debug_payload,
    )
