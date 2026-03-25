from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any, Awaitable, Callable

from redis.asyncio import Redis


RIDE_EVENTS_STREAM = "stream:ride_events"
DRIVER_EVENTS_STREAM = "stream:driver_events"
ONBOARDING_EVENTS_STREAM = "stream:onboarding_events"
NOTIFICATION_JOBS_STREAM = "stream:notification_jobs"
DRIVER_PRESENCE_CHANNEL = "channel:driver_presence"
DRIVER_PRESENCE_INDEX_KEY = "presence:drivers:index"


@lru_cache
def get_redis_client() -> Redis:
    return Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"), decode_responses=True)


async def publish_event(stream_name: str, event_type: str, payload: dict[str, Any]) -> str:
    message = {
        "event_type": event_type,
        "payload": json.dumps(payload),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    return await get_redis_client().xadd(stream_name, message)


async def consume_events(
    stream_name: str,
    group: str,
    consumer: str,
    handler: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
):
    redis = get_redis_client()
    try:
        await redis.xgroup_create(stream_name, group, id="0", mkstream=True)
    except Exception:
        pass

    while True:
        records = await redis.xreadgroup(group, consumer, {stream_name: ">"}, count=10, block=5000)
        for _stream, entries in records:
            for message_id, fields in entries:
                event = {
                    "id": message_id,
                    "event_type": fields.get("event_type"),
                    "payload": json.loads(fields.get("payload", "{}")),
                    "created_at": fields.get("created_at"),
                }
                if handler is not None:
                    await handler(event)
                yield event
                await redis.xack(stream_name, group, message_id)
