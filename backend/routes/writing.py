"""POST /api/openers, POST /api/bio — profile tools."""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, HTTPException

from schemas import BioRequest, BioResponse, OpenerRequest, OpenerResponse
from services.writing_service import generate_bios, generate_openers

logger = logging.getLogger("rizzai.api.writing")

router = APIRouter(prefix="/api", tags=["writing"])


@router.post("/openers", response_model=OpenerResponse)
async def create_openers(body: OpenerRequest) -> OpenerResponse:
    try:
        openers, provider = await asyncio.to_thread(
            generate_openers,
            profile_description=body.profile_description,
            tone=body.tone,
            count=body.count,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("[openers] failed: %s", exc)
        raise HTTPException(status_code=500, detail="Could not generate openers.") from exc

    if not openers:
        raise HTTPException(status_code=500, detail="Empty opener result.")
    return OpenerResponse(openers=openers, provider_used=provider)


@router.post("/bio", response_model=BioResponse)
async def create_bio_variants(body: BioRequest) -> BioResponse:
    try:
        bios, provider = await asyncio.to_thread(
            generate_bios,
            about_text=body.about_text,
            style_template=body.style_template,
            variant_count=body.variant_count,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("[bio] failed: %s", exc)
        raise HTTPException(status_code=500, detail="Could not generate bios.") from exc

    if not bios:
        raise HTTPException(status_code=500, detail="Empty bio result.")
    return BioResponse(bios=bios, provider_used=provider)
