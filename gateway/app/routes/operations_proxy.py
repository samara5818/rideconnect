from __future__ import annotations

import httpx
from fastapi import APIRouter, Request, Response
from fastapi.responses import StreamingResponse

from app.config import settings
from app.routes.proxy import forward_request

router = APIRouter(tags=["operations-proxy"])


@router.get("/api/v1/admin/dashboard/stream")
async def proxy_dashboard_stream(request: Request) -> StreamingResponse:
    target_url = f"{settings.operations_service_url}{request.url.path}"
    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in {"host", "content-length", "connection"}
    }
    client = httpx.AsyncClient(timeout=None)
    upstream_request = client.build_request(
        "GET",
        target_url,
        params=request.query_params,
        headers=headers,
    )
    upstream_response = await client.send(upstream_request, stream=True)

    async def stream_body():
        try:
            async for chunk in upstream_response.aiter_bytes():
                yield chunk
        finally:
            await upstream_response.aclose()
            await client.aclose()

    response_headers = {
        key: value
        for key, value in upstream_response.headers.items()
        if key.lower() not in {"content-encoding", "transfer-encoding", "connection", "content-length"}
    }
    return StreamingResponse(
        stream_body(),
        status_code=upstream_response.status_code,
        headers=response_headers,
        media_type=upstream_response.headers.get("content-type", "text/event-stream"),
    )


@router.api_route("/api/v1/admin/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
async def proxy_admin(path: str, request: Request) -> Response:
    return await forward_request(request, settings.operations_service_url)


@router.api_route("/api/v1/onboarding/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
async def proxy_onboarding(path: str, request: Request) -> Response:
    return await forward_request(request, settings.operations_service_url)
