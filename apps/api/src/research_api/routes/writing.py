"""Writing-assist endpoint — Improve / Shorten / Formalise / Add Transition."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from ..container import Container, get_container
from ..schemas.writing import WritingAssistRequest, WritingAssistResponse
from ..services.ai import (
    AIError,
    AIProviderUnavailable,
    AIRateLimited,
    AISourceInsufficient,
)

router = APIRouter(tags=["writing"])
log = logging.getLogger("research_api.writing")


@router.post("/writing/assist", response_model=WritingAssistResponse)
async def writing_assist(
    body: WritingAssistRequest,
    container: Container = Depends(get_container),
) -> WritingAssistResponse:
    try:
        revised = await container.ai.assist_writing(body.text, body.action)
    except AIRateLimited:
        raise HTTPException(status_code=429, detail="AI rate limited") from None
    except AISourceInsufficient:
        raise HTTPException(status_code=422, detail="text too short to assist") from None
    except (AIProviderUnavailable, AIError):
        raise HTTPException(status_code=503, detail="AI provider unavailable") from None
    except Exception:
        log.exception("Unexpected AI error in writing_assist")
        raise HTTPException(status_code=503, detail="AI provider unavailable") from None
    return WritingAssistResponse(revised=revised)
