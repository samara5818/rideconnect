from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.enums import DriverStatus, OfferStatus, RideStatus
from app.models import Driver, DriverOffer, Ride, RideEvent, TrackingPing, Vehicle
from app.services.common import haversine_miles, to_decimal
from shared.python.events.streams import RIDE_EVENTS_STREAM, get_redis_client, publish_event


def _uuid(value: str) -> UUID:
    return UUID(value)


class DispatchService:
    offer_timeout_seconds = 90
    max_dispatch_retries = 1

    async def _eligible_drivers(self, db: AsyncSession, ride: Ride) -> list[Driver]:
        drivers = (
            await db.execute(
                select(Driver)
                .where(
                    and_(
                        Driver.is_approved.is_(True),
                        Driver.is_online.is_(True),
                        Driver.is_available.is_(True),
                        Driver.status == DriverStatus.ACTIVE,
                        Driver.region_id == ride.region_id,
                    )
                )
            )
        ).scalars().all()
        if drivers:
            return drivers
        return (
            await db.execute(
                select(Driver).where(
                    and_(
                        Driver.is_approved.is_(True),
                        Driver.is_online.is_(True),
                        Driver.is_available.is_(True),
                        Driver.status == DriverStatus.ACTIVE,
                    )
                )
            )
        ).scalars().all()

    async def _refresh_candidates(self, db: AsyncSession, ride: Ride) -> list[str]:
        drivers = await self._eligible_drivers(db, ride)
        distance_map = await self._distance_from_driver_to_pickup(
            db,
            [driver.id for driver in drivers],
            float(ride.pickup_latitude),
            float(ride.pickup_longitude),
        )
        ranked = sorted(drivers, key=lambda driver: distance_map.get(driver.id, float("inf")))
        candidate_ids = [driver.id for driver in ranked]
        redis = get_redis_client()
        await redis.set(f"dispatch:candidates:{ride.id}", json.dumps(candidate_ids), ex=3600)
        return candidate_ids

    async def find_candidates(self, db: AsyncSession, ride_id: str) -> None:
        ride = await db.get(Ride, ride_id)
        if not ride:
            return
        await self._refresh_candidates(db, ride)
        await self.offer_next_candidate(db, ride_id)

    async def _distance_from_driver_to_pickup(
        self,
        db: AsyncSession,
        driver_ids: list[str],
        pickup_lat: float,
        pickup_lng: float,
    ) -> dict[str, float]:
        if not driver_ids:
            return {}

        latest_ping_times = (
            select(
                TrackingPing.driver_id.label("driver_id"),
                func.max(TrackingPing.recorded_at).label("latest_recorded_at"),
            )
            .where(TrackingPing.driver_id.in_(driver_ids))
            .group_by(TrackingPing.driver_id)
            .subquery()
        )
        rows = (
            await db.execute(
                select(TrackingPing)
                .join(
                    latest_ping_times,
                    and_(
                        TrackingPing.driver_id == latest_ping_times.c.driver_id,
                        TrackingPing.recorded_at == latest_ping_times.c.latest_recorded_at,
                    ),
                )
            )
        ).scalars().all()
        distance_map = {
            ping.driver_id: haversine_miles(float(ping.latitude), float(ping.longitude), pickup_lat, pickup_lng)
            for ping in rows
        }
        return distance_map

    async def offer_next_candidate(self, db: AsyncSession, ride_id: str) -> DriverOffer | None:
        ride = await db.get(Ride, ride_id)
        if not ride or ride.status in {RideStatus.CANCELLED, RideStatus.RIDE_COMPLETED, RideStatus.DRIVER_ASSIGNED, RideStatus.NO_DRIVERS_FOUND}:
            return None

        pending_offer = await db.scalar(
            select(DriverOffer).where(and_(DriverOffer.ride_id == ride_id, DriverOffer.offer_status == OfferStatus.PENDING))
        )
        if pending_offer:
            return pending_offer

        redis = get_redis_client()
        raw = await redis.get(f"dispatch:candidates:{ride_id}")
        candidate_ids = json.loads(raw) if raw else []
        if not candidate_ids:
            candidate_ids = await self._refresh_candidates(db, ride)
            if not candidate_ids:
                return None

        existing_offers = (
            await db.execute(select(DriverOffer).where(DriverOffer.ride_id == ride_id))
        ).scalars().all()
        attempted_driver_ids = {offer.driver_id for offer in existing_offers}
        next_driver_id = next((driver_id for driver_id in candidate_ids if driver_id not in attempted_driver_ids), None)
        if not next_driver_id:
            if ride.dispatch_retry_count >= self.max_dispatch_retries:
                await self._mark_no_drivers_found(db, ride)
                return None
            candidate_ids = await self._refresh_candidates(db, ride)
            ride.dispatch_retry_count += 1
            db.add(ride)
            await db.commit()
            await db.refresh(ride)
            blocking_driver_ids = {
                offer.driver_id
                for offer in existing_offers
                if offer.offer_status in {OfferStatus.PENDING, OfferStatus.ACCEPTED}
            }
            next_driver_id = next((driver_id for driver_id in candidate_ids if driver_id not in blocking_driver_ids), None)
        if not next_driver_id:
            await self._mark_no_drivers_found(db, ride)
            return None

        offer = DriverOffer(
            ride_id=ride_id,
            driver_id=next_driver_id,
            offer_status=OfferStatus.PENDING,
            offered_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=self.offer_timeout_seconds),
            created_at=datetime.now(timezone.utc),
        )
        db.add(offer)
        await db.commit()
        await db.refresh(offer)
        db.add(RideEvent(ride_id=ride_id, event_type="DRIVER_OFFER_SENT", event_payload={"driver_id": next_driver_id, "offer_id": offer.id}))
        await db.commit()
        await publish_event(RIDE_EVENTS_STREAM, "driver_offer_sent", {"ride_id": ride_id, "driver_id": next_driver_id, "offer_id": offer.id})
        return offer

    async def _mark_no_drivers_found(self, db: AsyncSession, ride: Ride) -> None:
        if ride.status == RideStatus.NO_DRIVERS_FOUND:
            return
        ride.status = RideStatus.NO_DRIVERS_FOUND
        ride.driver_id = None
        ride.vehicle_id = None
        db.add(ride)
        db.add(
            RideEvent(
                ride_id=ride.id,
                event_type="NO_DRIVERS_FOUND",
                event_payload={"dispatch_retry_count": ride.dispatch_retry_count},
            )
        )
        await db.commit()
        await publish_event(
            RIDE_EVENTS_STREAM,
            "no_drivers_found",
            {"ride_id": ride.id, "rider_id": ride.rider_id, "dispatch_retry_count": ride.dispatch_retry_count},
        )

    async def list_active_offers(self, db: AsyncSession, driver_user_id: str) -> list[dict]:
        driver = await db.scalar(select(Driver).where(Driver.user_id == _uuid(driver_user_id)))
        if not driver:
            return []
        rows = (
            await db.execute(
                select(DriverOffer, Ride)
                .join(Ride, Ride.id == DriverOffer.ride_id)
                .where(and_(DriverOffer.driver_id == driver.id, DriverOffer.offer_status == OfferStatus.PENDING))
                .order_by(DriverOffer.offered_at.desc())
            )
        ).all()
        return [
            {
                "offer_id": offer.id,
                "ride_id": ride.id,
                "pickup_address": ride.pickup_address,
                "dropoff_address": ride.dropoff_address,
                "distance_to_pickup_miles": to_decimal(0),
                "trip_distance_miles": ride.estimated_distance_miles or to_decimal(0),
                "estimated_payout": None,
                "expires_at": offer.expires_at,
                "offer_status": offer.offer_status.value,
            }
            for offer, ride in rows
        ]

    async def accept_offer(self, db: AsyncSession, driver_user_id: str, offer_id: str) -> dict:
        driver = await db.scalar(select(Driver).where(Driver.user_id == _uuid(driver_user_id)))
        if not driver:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Driver not found")
        offer = await db.get(DriverOffer, offer_id)
        if not offer or offer.driver_id != driver.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Offer not found")
        ride = await db.get(Ride, offer.ride_id)
        if not ride:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ride not found")
        if offer.offer_status == OfferStatus.ACCEPTED and ride.driver_id == driver.id:
            return {
                "offer_id": offer.id,
                "ride_id": ride.id,
                "offer_status": offer.offer_status.value,
                "ride_status": ride.status.value,
                "assigned_at": ride.assigned_at,
            }
        if offer.offer_status != OfferStatus.PENDING:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Offer already responded")
        if offer.expires_at < datetime.now(timezone.utc):
            offer.offer_status = OfferStatus.EXPIRED
            offer.responded_at = datetime.now(timezone.utc)
            db.add(offer)
            await db.commit()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Offer expired")
        offer.offer_status = OfferStatus.ACCEPTED
        offer.responded_at = datetime.now(timezone.utc)
        ride.status = RideStatus.DRIVER_ASSIGNED
        ride.driver_id = driver.id
        ride.assigned_at = datetime.now(timezone.utc)
        driver.is_available = False
        vehicle = await db.scalar(select(Vehicle).where(and_(Vehicle.driver_id == driver.id, Vehicle.is_active.is_(True))))
        ride.vehicle_id = vehicle.id if vehicle else None
        db.add_all([offer, ride, driver])
        db.add(RideEvent(ride_id=ride.id, event_type="DRIVER_ACCEPTED", event_payload={"driver_id": driver.id, "offer_id": offer.id}))
        db.add(RideEvent(ride_id=ride.id, event_type="RIDE_ASSIGNED", event_payload={"driver_id": driver.id}))
        other_offers = (
            await db.execute(
                select(DriverOffer).where(and_(DriverOffer.ride_id == ride.id, DriverOffer.id != offer.id, DriverOffer.offer_status == OfferStatus.PENDING))
            )
        ).scalars().all()
        for other in other_offers:
            other.offer_status = OfferStatus.EXPIRED
            other.responded_at = datetime.now(timezone.utc)
            db.add(other)
        await db.commit()
        await publish_event(RIDE_EVENTS_STREAM, "ride_assigned", {"ride_id": ride.id, "rider_id": ride.rider_id, "driver_id": driver.id})
        return {
            "offer_id": offer.id,
            "ride_id": ride.id,
            "offer_status": offer.offer_status.value,
            "ride_status": ride.status.value,
            "assigned_at": ride.assigned_at,
        }

    async def reject_offer(self, db: AsyncSession, driver_user_id: str, offer_id: str, reason: str | None) -> dict:
        driver = await db.scalar(select(Driver).where(Driver.user_id == _uuid(driver_user_id)))
        if not driver:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Driver not found")
        offer = await db.get(DriverOffer, offer_id)
        if not offer or offer.driver_id != driver.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Offer not found")
        if offer.offer_status != OfferStatus.PENDING:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Offer already responded")
        offer.offer_status = OfferStatus.REJECTED
        offer.responded_at = datetime.now(timezone.utc)
        db.add(offer)
        db.add(RideEvent(ride_id=offer.ride_id, event_type="DRIVER_REJECTED", event_payload={"driver_id": driver.id, "reason": reason}))
        await db.commit()
        await publish_event(RIDE_EVENTS_STREAM, "driver_offer_rejected", {"ride_id": offer.ride_id, "driver_id": driver.id, "reason": reason})
        await self.offer_next_candidate(db, offer.ride_id)
        return {"offer_id": offer.id, "offer_status": offer.offer_status.value}

    async def admin_redispatch_ride(self, db: AsyncSession, ride_id: str) -> dict:
        ride = await db.get(Ride, ride_id)
        if not ride:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ride not found")
        if ride.status not in {RideStatus.NO_DRIVERS_FOUND, RideStatus.MATCHING}:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ride cannot be redispatched")

        pending_offers = (
            await db.execute(
                select(DriverOffer).where(and_(DriverOffer.ride_id == ride.id, DriverOffer.offer_status == OfferStatus.PENDING))
            )
        ).scalars().all()
        for offer in pending_offers:
            offer.offer_status = OfferStatus.EXPIRED
            offer.responded_at = datetime.now(timezone.utc)
            db.add(offer)

        ride.status = RideStatus.MATCHING
        ride.driver_id = None
        ride.vehicle_id = None
        ride.assigned_at = None
        ride.driver_en_route_at = None
        ride.driver_arrived_at = None
        ride.started_at = None
        ride.dispatch_retry_count = 0
        db.add(ride)
        db.add(RideEvent(ride_id=ride.id, event_type="ADMIN_REDISPATCH_REQUESTED"))
        await db.commit()

        redis = get_redis_client()
        await redis.delete(f"dispatch:candidates:{ride.id}")
        await self.find_candidates(db, ride.id)

        return {
            "ride_id": ride.id,
            "status": ride.status.value,
            "dispatch_retry_count": ride.dispatch_retry_count,
        }

    async def auto_redispatch_stalled_prepickup_rides(self, db: AsyncSession) -> None:
        now = datetime.now(timezone.utc)
        redis = get_redis_client()
        rides = (
            await db.execute(
                select(Ride).where(Ride.status.in_([RideStatus.DRIVER_ASSIGNED, RideStatus.DRIVER_EN_ROUTE]))
            )
        ).scalars().all()

        for ride in rides:
            checkpoint = ride.driver_en_route_at or ride.assigned_at or ride.requested_at
            if checkpoint is None:
                continue
            if now - checkpoint < timedelta(minutes=settings.driver_pickup_timeout_minutes):
                continue

            driver = await db.get(Driver, ride.driver_id) if ride.driver_id else None
            if driver:
                driver.is_available = bool(driver.is_online and driver.is_approved and driver.status == DriverStatus.ACTIVE)
                db.add(driver)

            ride.status = RideStatus.MATCHING
            ride.driver_id = None
            ride.vehicle_id = None
            ride.assigned_at = None
            ride.driver_en_route_at = None
            ride.driver_arrived_at = None
            ride.dispatch_retry_count += 1
            db.add(ride)
            db.add(
                RideEvent(
                    ride_id=ride.id,
                    event_type="AUTO_REDISPATCH_REQUESTED",
                    event_payload={
                        "reason": "pickup_timeout",
                        "previous_driver_id": driver.id if driver else None,
                    },
                )
            )
            await db.commit()
            await publish_event(
                RIDE_EVENTS_STREAM,
                "ride_redispatching",
                {
                    "ride_id": ride.id,
                    "rider_id": ride.rider_id,
                    "previous_driver_id": driver.id if driver else None,
                    "reason": "pickup_timeout",
                    "dispatch_retry_count": ride.dispatch_retry_count,
                },
            )
            await redis.delete(f"dispatch:candidates:{ride.id}")
            await self.find_candidates(db, ride.id)

    async def expire_elapsed_offers(self, db: AsyncSession) -> None:
        expired = (
            await db.execute(
                select(DriverOffer).where(and_(DriverOffer.offer_status == OfferStatus.PENDING, DriverOffer.expires_at < datetime.now(timezone.utc)))
            )
        ).scalars().all()
        for offer in expired:
            offer.offer_status = OfferStatus.EXPIRED
            offer.responded_at = datetime.now(timezone.utc)
            db.add(offer)
            db.add(RideEvent(ride_id=offer.ride_id, event_type="DRIVER_OFFER_EXPIRED", event_payload={"driver_id": offer.driver_id, "offer_id": offer.id}))
            await publish_event(RIDE_EVENTS_STREAM, "driver_offer_expired", {"ride_id": offer.ride_id, "driver_id": offer.driver_id, "offer_id": offer.id})
        if expired:
            await db.commit()
            for offer in expired:
                await self.offer_next_candidate(db, offer.ride_id)

    async def recover_stale_matching_rides(self, db: AsyncSession) -> None:
        rides = (
            await db.execute(
                select(Ride).where(and_(Ride.status == RideStatus.MATCHING, Ride.driver_id.is_(None)))
            )
        ).scalars().all()
        for ride in rides:
            pending_offer = await db.scalar(
                select(DriverOffer).where(and_(DriverOffer.ride_id == ride.id, DriverOffer.offer_status == OfferStatus.PENDING))
            )
            if pending_offer:
                continue
            await self.offer_next_candidate(db, ride.id)


dispatch_service = DispatchService()
