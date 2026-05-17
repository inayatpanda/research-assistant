import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from ..container import Container, get_container
from ..services.pdf_text import detect_mime
from ..services.storage.signed_urls import TokenExpired, TokenInvalid, verify_token

router = APIRouter(tags=["files"])
log = logging.getLogger("research_api.files")


@router.get("/files/{token}")
async def serve_file(token: str, container: Container = Depends(get_container)) -> Response:
    try:
        ref = verify_token(token, secret=container.settings.api_signing_secret)
    except TokenExpired:
        raise HTTPException(status_code=410, detail="token expired") from None
    except TokenInvalid:
        raise HTTPException(status_code=403, detail="invalid token") from None
    try:
        data = await container.storage.read(ref)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="file not found") from None
    except Exception as e:
        # Log internally — never echo internal paths or stack traces to the client.
        log.exception("file read failed for backend=%s", ref.backend)
        raise HTTPException(status_code=500, detail="internal error") from e
    return Response(content=data, media_type=detect_mime(data) or "application/octet-stream")
