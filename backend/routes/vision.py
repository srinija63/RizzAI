"""POST /api/extract-from-image — screenshot → conversation text (Gemini vision)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from schemas import ExtractFromImageRequest, ExtractFromImageResponse
from services.llm_service import extract_conversation_text_from_screenshot

logger = logging.getLogger("rizzai.api.vision")

router = APIRouter(prefix="/api", tags=["vision"])


@router.post(
    "/extract-from-image",
    response_model=ExtractFromImageResponse,
    summary="Extract chat text from a screenshot",
)
async def extract_from_image(body: ExtractFromImageRequest) -> ExtractFromImageResponse:
    try:
        text, warning = extract_conversation_text_from_screenshot(
            image_base64=body.image_base64,
            mime_type=body.mime_type,
        )
    except RuntimeError as exc:
        logger.warning("[extract-from-image] failed: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.error("[extract-from-image] unexpected: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Could not extract text from the image.",
        ) from exc

    return ExtractFromImageResponse(conversation_text=text, warning=warning)
