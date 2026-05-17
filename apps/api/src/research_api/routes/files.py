from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from ..container import Container, get_container
from ..services.pdf_text import detect_mime
from ..services.storage.signed_urls import TokenExpired, TokenInvalid, verify_token

router = APIRouter(tags=["files"])


@router.get("/files/{token}")
async def serve_file(token: str, container: Container = Depends(get_container)) -> Response:
    try:
        ref = verify_token(token, secret=container.settings.api_signing_secret)
    except TokenExpired as e:
        raise HTTPException(status_code=410, detail=str(e)) from e
    except TokenInvalid as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    try:
        data = await container.storage.read(ref)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail="file not found") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    return Response(content=data, media_type=detect_mime(data) or "application/octet-stream")
