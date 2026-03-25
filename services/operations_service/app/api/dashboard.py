from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends, Header, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import TokenPayload, require_role, require_role_from_header_or_query
from app.db.session import get_db_session
from app.services.dashboard_service import dashboard_service
from shared.python.enums.roles import UserRole
from shared.python.events.streams import DRIVER_PRESENCE_CHANNEL, get_redis_client
from shared.python.schemas.responses import SuccessResponse

router = APIRouter(prefix="/api/v1/admin/dashboard", tags=["admin-dashboard"])


@router.get("/summary", response_model=SuccessResponse)
async def get_dashboard_summary(
    db: AsyncSession = Depends(get_db_session),
    _user: TokenPayload = Depends(require_role(UserRole.ADMIN)),
    authorization: str | None = Header(default=None),
) -> SuccessResponse:
    summary = await dashboard_service.get_summary(db, authorization)
    return SuccessResponse(data=summary.model_dump(mode="json"))


@router.get("/stream")
async def stream_dashboard_presence(
    db: AsyncSession = Depends(get_db_session),
    _user: TokenPayload = Depends(require_role_from_header_or_query(UserRole.ADMIN)),
    authorization: str | None = Header(default=None),
    access_token: str | None = Query(default=None, alias="access_token"),
) -> StreamingResponse:
    resolved_auth = authorization or (f"Bearer {access_token}" if access_token else None)

    async def event_generator():
        redis = get_redis_client()
        pubsub = redis.pubsub()
        await pubsub.subscribe(DRIVER_PRESENCE_CHANNEL)
        try:
            summary = await dashboard_service.get_summary(db, resolved_auth)
            yield f"event: summary\ndata: {json.dumps(summary.model_dump(mode='json'))}\n\n"
            while True:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=10.0)
                if message and message.get("data"):
                    yield f"event: presence\ndata: {message['data']}\n\n"
                    summary = await dashboard_service.get_summary(db, resolved_auth)
                    yield f"event: summary\ndata: {json.dumps(summary.model_dump(mode='json'))}\n\n"
                    continue
                yield ": keep-alive\n\n"
                await asyncio.sleep(0)
        finally:
            await pubsub.unsubscribe(DRIVER_PRESENCE_CHANNEL)
            await pubsub.close()

    return StreamingResponse(event_generator(), media_type="text/event-stream")
