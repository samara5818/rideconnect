from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import CancelledBy, RideStatus
from app.models import Driver, DriverAvailabilityLog, Ride, RideEvent
from shared.python.events.streams import DRIVER_PRESENCE_CHANNEL, DRIVER_PRESENCE_INDEX_KEY, get_redis_client


PRESENCE_TTL_SECONDS = 30
HEARTBEAT_INTERVAL_SECONDS = 15
def _presence_key(driver_id: str) -> str:
    return f"presence:driver:{driver_id}"


class DriverPresenceService:
    async def _cancel_unfinished_rides_for_driver(self, db: AsyncSession, driver_id: str, reason: str) -> None:
        rides = (
            await db.execute(
                select(Ride).where(
                    and_(
                        Ride.driver_id == driver_id,
                        Ride.status.in_(
                            [
                                RideStatus.DRIVER_ASSIGNED,
                                RideStatus.DRIVER_EN_ROUTE,
                                RideStatus.DRIVER_ARRIVED,
                                RideStatus.RIDE_STARTED,
                            ]
                        ),
                    )
                )
            )
        ).scalars().all()
        if not rides:
            return

        now = datetime.now(timezone.utc)
        for ride in rides:
            ride.status = RideStatus.CANCELLED
            ride.cancelled_at = now
            ride.cancelled_by = CancelledBy.DRIVER
            ride.cancel_reason = reason
            db.add(ride)
            db.add(
                RideEvent(
                    ride_id=ride.id,
                    event_type="RIDE_CANCELLED",
                    event_payload={"cancel_reason": reason, "cancelled_by": CancelledBy.DRIVER.value},
                )
            )

    async def mark_online(self, driver_id: str, is_available: bool) -> None:
        redis = get_redis_client()
        expires_at = self._expires_at()
        payload = {
            "driver_id": driver_id,
            "is_online": True,
            "is_available": is_available,
            "expires_at": expires_at,
        }
        await redis.set(_presence_key(driver_id), json.dumps(payload), ex=PRESENCE_TTL_SECONDS)
        await redis.zadd(DRIVER_PRESENCE_INDEX_KEY, {driver_id: self._expiry_score()})
        await redis.publish(DRIVER_PRESENCE_CHANNEL, json.dumps({"type": "presence_changed", "driver_id": driver_id}))

    async def mark_offline(self, driver_id: str) -> None:
        redis = get_redis_client()
        await redis.delete(_presence_key(driver_id))
        await redis.zrem(DRIVER_PRESENCE_INDEX_KEY, driver_id)
        await redis.publish(DRIVER_PRESENCE_CHANNEL, json.dumps({"type": "presence_changed", "driver_id": driver_id}))

    async def heartbeat(self, driver_id: str) -> bool:
        redis = get_redis_client()
        raw = await redis.get(_presence_key(driver_id))
        if not raw:
            return False
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = {}
        payload.update(
            {
                "driver_id": driver_id,
                "is_online": True,
                "expires_at": self._expires_at(),
            }
        )
        await redis.set(_presence_key(driver_id), json.dumps(payload), ex=PRESENCE_TTL_SECONDS)
        await redis.zadd(DRIVER_PRESENCE_INDEX_KEY, {driver_id: self._expiry_score()})
        return True

    async def get_snapshot(self, driver_ids: list[str]) -> dict[str, dict]:
        if not driver_ids:
            return {}
        await self.cleanup_expired_presence()
        redis = get_redis_client()
        raw_items = await redis.mget([_presence_key(driver_id) for driver_id in driver_ids])
        snapshot: dict[str, dict] = {}
        for raw in raw_items:
            if not raw:
                continue
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                continue
            driver_id = payload.get("driver_id")
            if isinstance(driver_id, str):
                snapshot[driver_id] = payload
        return snapshot

    async def count_online(self) -> int:
        await self.cleanup_expired_presence()
        redis = get_redis_client()
        return int(await redis.zcard(DRIVER_PRESENCE_INDEX_KEY))

    async def cleanup_expired_presence(self) -> list[str]:
        redis = get_redis_client()
        now = self._now_score()
        expired_driver_ids = await redis.zrangebyscore(DRIVER_PRESENCE_INDEX_KEY, min=0, max=now)
        reconciled: list[str] = []
        for driver_id in expired_driver_ids:
            if await redis.exists(_presence_key(driver_id)):
                continue
            await redis.zrem(DRIVER_PRESENCE_INDEX_KEY, driver_id)
            reconciled.append(driver_id)
        return reconciled

    async def reconcile_expired_presence(self, db: AsyncSession) -> list[str]:
        expired_driver_ids = await self.cleanup_expired_presence()
        if not expired_driver_ids:
            return []

        rows = (
            await db.execute(
                select(Driver).where(Driver.id.in_(expired_driver_ids), Driver.is_online.is_(True))
            )
        ).scalars().all()
        if not rows:
            return expired_driver_ids

        for driver in rows:
            driver.is_online = False
            driver.is_available = False
            await self._cancel_unfinished_rides_for_driver(
                db,
                driver.id,
                "Driver presence expired before the ride was completed.",
            )
            db.add(driver)
            db.add(
                DriverAvailabilityLog(
                    driver_id=driver.id,
                    is_online=False,
                    is_available=False,
                    reason="PRESENCE_TIMEOUT",
                )
            )

        await db.commit()
        redis = get_redis_client()
        for driver in rows:
            await redis.publish(DRIVER_PRESENCE_CHANNEL, json.dumps({"type": "presence_changed", "driver_id": driver.id}))
        return expired_driver_ids

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    @classmethod
    def _expires_at(cls) -> str:
        return (cls._now() + timedelta(seconds=PRESENCE_TTL_SECONDS)).isoformat()

    @classmethod
    def _now_score(cls) -> float:
        return cls._now().timestamp()

    @classmethod
    def _expiry_score(cls) -> float:
        return cls._now_score() + PRESENCE_TTL_SECONDS


driver_presence_service = DriverPresenceService()
