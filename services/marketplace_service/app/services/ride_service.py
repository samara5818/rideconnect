from __future__ import annotations

from datetime import datetime, timezone
from math import ceil
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.enums import CancelledBy, OfferStatus, RideFeedbackStatus, RideStatus, RideType
from app.models import Driver, DriverOffer, FareEstimate, Ride, RideEvent, Rider, TrackingPing, Vehicle
from app.schemas.ride import (
    CancelRideRequest,
    CompleteRideRequest,
    InternalActiveRideItem,
    PaginationResponse,
    RideCancelledResponse,
    RideDetailResponse,
    RideDriverSummary,
    RideFareBreakdownResponse,
    RideHistoryItem,
    RideHistoryResponse,
    RideRequestCreate,
    RideRequestedResponse,
    RideStatusActionResponse,
    RideVehicleSummary,
    SubmitRideFeedbackRequest,
    UnmatchedRideReportItem,
    UnmatchedRideReportResponse,
)
from app.services.common import haversine_miles, to_decimal
from app.services.dispatch_service import dispatch_service
from shared.python.enums.roles import UserRole
from shared.python.events.streams import RIDE_EVENTS_STREAM, publish_event


def _uuid(value: str) -> UUID:
    return UUID(value)


def _display_name(first_name: str | None, last_name: str | None, fallback: str) -> str:
    full_name = " ".join(part for part in [first_name, last_name] if part).strip()
    return full_name or fallback


class RideService:
    legal_transitions = {
        RideStatus.REQUESTED: {RideStatus.MATCHING, RideStatus.CANCELLED},
        RideStatus.MATCHING: {RideStatus.DRIVER_ASSIGNED, RideStatus.NO_DRIVERS_FOUND, RideStatus.CANCELLED},
        RideStatus.NO_DRIVERS_FOUND: {RideStatus.MATCHING, RideStatus.CANCELLED},
        RideStatus.DRIVER_ASSIGNED: {RideStatus.MATCHING, RideStatus.DRIVER_EN_ROUTE, RideStatus.CANCELLED},
        RideStatus.DRIVER_EN_ROUTE: {RideStatus.MATCHING, RideStatus.DRIVER_ARRIVED, RideStatus.CANCELLED},
        RideStatus.DRIVER_ARRIVED: {RideStatus.MATCHING, RideStatus.RIDE_STARTED, RideStatus.CANCELLED},
        RideStatus.RIDE_STARTED: {RideStatus.RIDE_COMPLETED, RideStatus.CANCELLED},
    }

    async def log_event(self, db: AsyncSession, ride_id: str, event_type: str, event_payload: dict | None = None) -> None:
        db.add(RideEvent(ride_id=ride_id, event_type=event_type, event_payload=event_payload))
        await db.flush()

    async def ensure_rider_for_write(self, db: AsyncSession, user_id: str) -> Rider:
        rider = await db.scalar(select(Rider).where(Rider.user_id == _uuid(user_id)))
        if rider:
            return rider
        rider = Rider(user_id=_uuid(user_id), first_name="Rider")
        db.add(rider)
        await db.commit()
        await db.refresh(rider)
        return rider

    async def get_rider_or_404(self, db: AsyncSession, user_id: str) -> Rider:
        rider = await db.scalar(select(Rider).where(Rider.user_id == _uuid(user_id)))
        if not rider:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Rider profile not found. Complete rider setup before accessing rides.",
            )
        return rider

    async def create_ride(self, db: AsyncSession, rider_user_id: str, payload: RideRequestCreate) -> RideRequestedResponse:
        rider = await self.ensure_rider_for_write(db, rider_user_id)
        duplicate_ride = await db.scalar(
            select(Ride).where(
                Ride.rider_id == rider.id,
                Ride.pickup_address == payload.pickup_address,
                Ride.dropoff_address == payload.dropoff_address,
                Ride.ride_type == RideType(payload.ride_type),
                Ride.status.in_(
                    [
                        RideStatus.REQUESTED,
                        RideStatus.MATCHING,
                        RideStatus.NO_DRIVERS_FOUND,
                        RideStatus.DRIVER_ASSIGNED,
                        RideStatus.DRIVER_EN_ROUTE,
                        RideStatus.DRIVER_ARRIVED,
                        RideStatus.RIDE_STARTED,
                    ]
                ),
            ).order_by(Ride.requested_at.desc())
        )
        if duplicate_ride:
            return RideRequestedResponse(
                ride_id=duplicate_ride.id,
                status=duplicate_ride.status.value,
                requested_at=duplicate_ride.requested_at,
            )
        fare_estimate = await db.get(FareEstimate, payload.fare_estimate_id) if payload.fare_estimate_id else None
        ride = Ride(
            rider_id=rider.id,
            region_id=fare_estimate.region_id if fare_estimate else None,
            status=RideStatus.REQUESTED,
            ride_type=RideType(payload.ride_type),
            payment_method=payload.payment_method or rider.default_payment_method or "CASH",
            pickup_address=payload.pickup_address,
            pickup_latitude=payload.pickup_latitude,
            pickup_longitude=payload.pickup_longitude,
            dropoff_address=payload.dropoff_address,
            dropoff_latitude=payload.dropoff_latitude,
            dropoff_longitude=payload.dropoff_longitude,
            requested_at=datetime.now(timezone.utc),
            estimated_distance_miles=fare_estimate.distance_miles if fare_estimate else None,
            estimated_duration_minutes=fare_estimate.duration_minutes if fare_estimate else None,
            fare_estimate_id=fare_estimate.id if fare_estimate else None,
        )
        db.add(ride)
        await db.flush()
        if fare_estimate:
            fare_estimate.ride_id = ride.id
            db.add(fare_estimate)
        await self.log_event(db, ride.id, "RIDE_REQUESTED")
        await self.transition(db, ride, RideStatus.MATCHING, actor_id=rider.id, publish=False)
        await self.log_event(db, ride.id, "MATCHING_STARTED")
        await db.commit()

        await dispatch_service.find_candidates(db, ride.id)
        return RideRequestedResponse(ride_id=ride.id, status=ride.status.value, requested_at=ride.requested_at)

    async def transition(self, db: AsyncSession, ride: Ride, new_status: RideStatus, actor_id: str, publish: bool = True) -> Ride:
        allowed = self.legal_transitions.get(ride.status, {RideStatus.CANCELLED})
        if new_status not in allowed:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Invalid ride status transition")
        ride.status = new_status
        now = datetime.now(timezone.utc)
        if new_status == RideStatus.DRIVER_ASSIGNED:
            ride.assigned_at = now
        elif new_status == RideStatus.MATCHING:
            ride.driver_id = None
            ride.vehicle_id = None
            ride.assigned_at = None
            ride.driver_en_route_at = None
            ride.driver_arrived_at = None
            ride.started_at = None
        elif new_status == RideStatus.DRIVER_EN_ROUTE:
            ride.driver_en_route_at = now
        elif new_status == RideStatus.DRIVER_ARRIVED:
            ride.driver_arrived_at = now
        elif new_status == RideStatus.RIDE_STARTED:
            ride.started_at = now
        elif new_status == RideStatus.RIDE_COMPLETED:
            ride.completed_at = now
        elif new_status == RideStatus.CANCELLED:
            ride.cancelled_at = now
        db.add(ride)
        await db.flush()
        if publish:
            await publish_event(RIDE_EVENTS_STREAM, new_status.value.lower(), {"ride_id": ride.id, "actor_id": actor_id})
        return ride

    async def get_ride_detail(self, db: AsyncSession, ride_id: str, actor_user_id: str, role: UserRole) -> RideDetailResponse:
        ride = await db.get(Ride, ride_id)
        if not ride:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ride not found")
        await self._enforce_access(db, ride, actor_user_id, role)
        driver_summary = None
        vehicle_summary = None
        if ride.driver_id:
            driver = await db.get(Driver, ride.driver_id)
            if driver:
                driver_summary = RideDriverSummary(id=driver.id, first_name=driver.first_name, last_name=driver.last_name, rating_avg=driver.rating_avg)
        if ride.vehicle_id:
            vehicle = await db.get(Vehicle, ride.vehicle_id)
            if vehicle:
                vehicle_summary = RideVehicleSummary(
                    make=vehicle.make,
                    model=vehicle.model,
                    plate_number=vehicle.plate_number,
                    vehicle_type=vehicle.vehicle_type,
                    color=vehicle.color,
                )
        fare_estimate = await db.get(FareEstimate, ride.fare_estimate_id) if ride.fare_estimate_id else None
        feedback_status = ride.feedback_status.value if ride.feedback_status else RideFeedbackStatus.PENDING.value
        receipt_available = ride.status == RideStatus.RIDE_COMPLETED and ride.final_fare_amount is not None
        can_rate_driver = (
            ride.status == RideStatus.RIDE_COMPLETED
            and ride.driver_id is not None
            and ride.rider_rating is None
            and ride.feedback_status != RideFeedbackStatus.SKIPPED
        )
        fare_breakdown = self._build_rider_fare_breakdown(ride, fare_estimate)
        return RideDetailResponse(
            id=ride.id,
            status=ride.status.value,
            ride_type=ride.ride_type.value,
            payment_method=ride.payment_method or "CASH",
            pickup_address=ride.pickup_address,
            dropoff_address=ride.dropoff_address,
            driver=driver_summary,
            vehicle=vehicle_summary,
            requested_at=ride.requested_at,
            assigned_at=ride.assigned_at,
            driver_en_route_at=ride.driver_en_route_at,
            driver_arrived_at=ride.driver_arrived_at,
            started_at=ride.started_at,
            completed_at=ride.completed_at,
            estimated_distance_miles=ride.estimated_distance_miles,
            estimated_duration_minutes=ride.estimated_duration_minutes,
            dispatch_retry_count=ride.dispatch_retry_count,
            actual_distance_miles=ride.actual_distance_miles,
            actual_duration_minutes=ride.actual_duration_minutes,
            final_fare_amount=ride.final_fare_amount,
            rider_rating=ride.rider_rating,
            rider_comment=ride.rider_comment,
            feedback_status=feedback_status,
            completion_acknowledged=ride.completion_acknowledged,
            payment_status="PROCESSED" if ride.final_fare_amount is not None else "PENDING",
            receipt_available=receipt_available,
            can_rate_driver=can_rate_driver,
            can_tip=False,
            fare_breakdown=fare_breakdown,
        )

    async def list_rider_history(self, db: AsyncSession, rider_user_id: str, page: int, page_size: int) -> RideHistoryResponse:
        rider = await self.get_rider_or_404(db, rider_user_id)
        rows = (await db.execute(select(Ride).where(Ride.rider_id == rider.id).order_by(Ride.requested_at.desc()))).scalars().all()
        total_items = len(rows)
        items = [
            RideHistoryItem(
                ride_id=ride.id,
                pickup_address=ride.pickup_address,
                dropoff_address=ride.dropoff_address,
                status=ride.status.value,
                completed_at=ride.completed_at,
                final_fare_amount=ride.final_fare_amount,
            )
            for ride in rows[(page - 1) * page_size : page * page_size]
        ]
        return RideHistoryResponse(
            items=items,
            pagination=PaginationResponse(
                page=page,
                page_size=page_size,
                total_items=total_items,
                total_pages=ceil(total_items / page_size) if page_size else 1,
            ),
        )

    async def cancel_ride(self, db: AsyncSession, ride_id: str, actor_user_id: str, role: UserRole, payload: CancelRideRequest) -> RideCancelledResponse:
        ride = await db.get(Ride, ride_id)
        if not ride:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ride not found")
        await self._enforce_access(db, ride, actor_user_id, role)
        if ride.status in {RideStatus.RIDE_COMPLETED, RideStatus.CANCELLED}:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Invalid ride status transition")
        if role == UserRole.DRIVER and ride.status in {RideStatus.DRIVER_ASSIGNED, RideStatus.DRIVER_EN_ROUTE, RideStatus.DRIVER_ARRIVED}:
            previous_driver_id = ride.driver_id
            driver = await db.scalar(select(Driver).where(Driver.user_id == _uuid(actor_user_id)))
            if driver:
                driver.is_available = True
                driver.is_online = True
                db.add(driver)
            await self.transition(db, ride, RideStatus.MATCHING, actor_id=actor_user_id, publish=False)
            ride.dispatch_retry_count += 1
            db.add(ride)
            await self.log_event(
                db,
                ride.id,
                "DRIVER_CANCELLED_REASSIGN",
                {"cancel_reason": payload.cancel_reason, "driver_id": previous_driver_id},
            )
            await db.commit()
            await publish_event(
                RIDE_EVENTS_STREAM,
                "ride_redispatching",
                {
                    "ride_id": ride.id,
                    "rider_id": ride.rider_id,
                    "previous_driver_id": previous_driver_id,
                    "reason": "driver_cancelled",
                    "dispatch_retry_count": ride.dispatch_retry_count,
                },
            )
            await dispatch_service.find_candidates(db, ride.id)
            return RideCancelledResponse(ride_id=ride.id, status=ride.status.value, cancelled_at=None)
        ride.cancel_reason = payload.cancel_reason
        ride.cancelled_by = CancelledBy(role.value)
        await self.transition(db, ride, RideStatus.CANCELLED, actor_id=actor_user_id, publish=False)
        await self.log_event(db, ride.id, "RIDE_CANCELLED", {"cancel_reason": payload.cancel_reason, "cancelled_by": role.value})
        if ride.driver_id:
            driver = await db.get(Driver, ride.driver_id)
            if driver:
                driver.is_available = True
                driver.is_online = True
                db.add(driver)
        await db.commit()
        return RideCancelledResponse(ride_id=ride.id, status=ride.status.value, cancelled_at=ride.cancelled_at)

    async def driver_status_action(self, db: AsyncSession, ride_id: str, driver_user_id: str, action: RideStatus) -> RideStatusActionResponse:
        ride = await db.get(Ride, ride_id)
        if not ride:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ride not found")
        driver = await db.scalar(select(Driver).where(Driver.user_id == _uuid(driver_user_id)))
        if not driver or ride.driver_id != driver.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        await self.transition(db, ride, action, actor_id=driver.id, publish=False)
        event_name = {
            RideStatus.DRIVER_EN_ROUTE: "DRIVER_EN_ROUTE",
            RideStatus.DRIVER_ARRIVED: "DRIVER_ARRIVED",
            RideStatus.RIDE_STARTED: "RIDE_STARTED",
        }[action]
        await self.log_event(db, ride.id, event_name)
        event_type = {
            RideStatus.DRIVER_EN_ROUTE: "driver_en_route",
            RideStatus.DRIVER_ARRIVED: "driver_arrived",
            RideStatus.RIDE_STARTED: "ride_started",
        }[action]
        await db.commit()
        await publish_event(RIDE_EVENTS_STREAM, event_type, {"ride_id": ride.id, "rider_id": ride.rider_id, "driver_id": driver.id})
        return RideStatusActionResponse(
            ride_id=ride.id,
            status=ride.status.value,
            dispatch_retry_count=ride.dispatch_retry_count,
            driver_en_route_at=ride.driver_en_route_at,
            driver_arrived_at=ride.driver_arrived_at,
            started_at=ride.started_at,
        )

    async def _derive_actual_distance_miles(self, db: AsyncSession, ride: Ride, driver_id: str) -> float:
        pings = (
            await db.execute(
                select(TrackingPing)
                .where(and_(TrackingPing.ride_id == ride.id, TrackingPing.driver_id == driver_id))
                .order_by(TrackingPing.recorded_at.asc())
            )
        ).scalars().all()

        if len(pings) >= 2:
            total_distance = 0.0
            for previous, current in zip(pings, pings[1:]):
                total_distance += haversine_miles(
                    float(previous.latitude),
                    float(previous.longitude),
                    float(current.latitude),
                    float(current.longitude),
                )
            if total_distance > 0:
                return total_distance

        return haversine_miles(
            float(ride.pickup_latitude),
            float(ride.pickup_longitude),
            float(ride.dropoff_latitude),
            float(ride.dropoff_longitude),
        )

    def _derive_actual_duration_minutes(self, ride: Ride) -> int:
        if not ride.started_at:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ride start time is missing; cannot complete ride.")
        elapsed_seconds = max((datetime.now(timezone.utc) - ride.started_at).total_seconds(), 60)
        return max(1, round(elapsed_seconds / 60))

    def _build_rider_fare_breakdown(self, ride: Ride, fare_estimate: FareEstimate | None) -> RideFareBreakdownResponse | None:
        if fare_estimate is None:
            if ride.final_fare_amount is None:
                return None
            total = to_decimal(ride.final_fare_amount)
            return RideFareBreakdownResponse(
                base_fare=total,
                distance_fare=to_decimal(0),
                time_fare=to_decimal(0),
                booking_fee=to_decimal(0),
                platform_fee=to_decimal(0),
                total=total,
            )

        estimate_total = float(fare_estimate.total_estimated_fare or 0)
        final_total = float(ride.final_fare_amount or fare_estimate.total_estimated_fare or 0)
        multiplier = final_total / estimate_total if estimate_total > 0 else 1.0

        return RideFareBreakdownResponse(
            base_fare=to_decimal(float(fare_estimate.base_fare) * multiplier),
            distance_fare=to_decimal(float(fare_estimate.distance_fare) * multiplier),
            time_fare=to_decimal(float(fare_estimate.time_fare) * multiplier),
            booking_fee=to_decimal(float(fare_estimate.booking_fee) * multiplier),
            platform_fee=to_decimal(float(fare_estimate.platform_fee) * multiplier),
            total=to_decimal(final_total),
        )

    async def complete_ride(self, db: AsyncSession, ride_id: str, driver_user_id: str, payload: CompleteRideRequest) -> RideStatusActionResponse:
        ride = await db.get(Ride, ride_id)
        if not ride:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ride not found")
        driver = await db.scalar(select(Driver).where(Driver.user_id == _uuid(driver_user_id)))
        if not driver or ride.driver_id != driver.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        fare_estimate = await db.get(FareEstimate, ride.fare_estimate_id) if ride.fare_estimate_id else None
        actual_distance_miles = float(payload.actual_distance_miles) if payload.actual_distance_miles is not None else await self._derive_actual_distance_miles(db, ride, driver.id)
        actual_duration_minutes = payload.actual_duration_minutes if payload.actual_duration_minutes is not None else self._derive_actual_duration_minutes(ride)
        ride.actual_distance_miles = to_decimal(actual_distance_miles)
        ride.actual_duration_minutes = actual_duration_minutes
        if fare_estimate:
            ratio_distance = actual_distance_miles / max(float(fare_estimate.distance_miles or 1), 1)
            ratio_duration = actual_duration_minutes / max(float(fare_estimate.duration_minutes or 1), 1)
            multiplier = max(1.0, (ratio_distance + ratio_duration) / 2)
            ride.final_fare_amount = to_decimal(float(fare_estimate.total_estimated_fare) * multiplier)
            ride.driver_payout_amount = to_decimal(float(fare_estimate.driver_payout_estimate or 0) * multiplier)
        ride.feedback_status = RideFeedbackStatus.PENDING
        ride.completion_acknowledged = False
        await self.transition(db, ride, RideStatus.RIDE_COMPLETED, actor_id=driver.id, publish=False)
        driver.is_available = True
        driver.is_online = True
        driver.total_rides_completed += 1
        db.add(driver)
        await self.log_event(db, ride.id, "RIDE_COMPLETED", {"driver_id": driver.id})
        await db.commit()
        await publish_event(RIDE_EVENTS_STREAM, "ride_completed", {"ride_id": ride.id, "rider_id": ride.rider_id, "driver_id": driver.id})
        return RideStatusActionResponse(
            ride_id=ride.id,
            status=ride.status.value,
            dispatch_retry_count=ride.dispatch_retry_count,
            completed_at=ride.completed_at,
            final_fare_amount=ride.final_fare_amount,
            driver_payout_amount=ride.driver_payout_amount,
        )

    async def submit_rider_feedback(
        self,
        db: AsyncSession,
        ride_id: str,
        rider_user_id: str,
        payload: SubmitRideFeedbackRequest,
    ) -> dict:
        ride = await db.get(Ride, ride_id)
        if not ride:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ride not found")
        await self._enforce_access(db, ride, rider_user_id, UserRole.RIDER)
        if ride.status != RideStatus.RIDE_COMPLETED:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ride is not completed")
        if not ride.driver_id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ride has no driver to rate")

        ride.rider_rating = payload.rating
        ride.rider_comment = payload.comment.strip() if payload.comment else None
        ride.feedback_status = RideFeedbackStatus.SUBMITTED
        ride.completion_acknowledged = True
        db.add(ride)

        driver = await db.get(Driver, ride.driver_id)
        if driver:
            rating_rows = (
                await db.execute(
                    select(Ride.rider_rating).where(
                        and_(Ride.driver_id == driver.id, Ride.rider_rating.is_not(None))
                    )
                )
            ).all()
            ratings = [int(row[0]) for row in rating_rows if row[0] is not None]
            if ratings:
                driver.rating_avg = to_decimal(sum(ratings) / len(ratings))
                db.add(driver)

        await self.log_event(db, ride.id, "RIDER_FEEDBACK_SUBMITTED", {"rating": payload.rating})
        await db.commit()
        return {
            "ride_id": ride.id,
            "feedback_status": ride.feedback_status.value,
            "completion_acknowledged": ride.completion_acknowledged,
            "rider_rating": ride.rider_rating,
            "rider_comment": ride.rider_comment,
        }

    async def acknowledge_completion(
        self,
        db: AsyncSession,
        ride_id: str,
        rider_user_id: str,
        feedback_status: str | None,
    ) -> dict:
        ride = await db.get(Ride, ride_id)
        if not ride:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ride not found")
        await self._enforce_access(db, ride, rider_user_id, UserRole.RIDER)
        if ride.status != RideStatus.RIDE_COMPLETED:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ride is not completed")

        ride.completion_acknowledged = True
        if feedback_status:
            try:
                next_status = RideFeedbackStatus(feedback_status)
            except ValueError as exc:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid feedback status") from exc
            if next_status == RideFeedbackStatus.SKIPPED and ride.rider_rating is None:
                ride.feedback_status = RideFeedbackStatus.SKIPPED
            elif next_status == RideFeedbackStatus.SUBMITTED and ride.rider_rating is not None:
                ride.feedback_status = RideFeedbackStatus.SUBMITTED
        db.add(ride)
        await self.log_event(
            db,
            ride.id,
            "RIDE_COMPLETION_ACKNOWLEDGED",
            {"feedback_status": ride.feedback_status.value},
        )
        await db.commit()
        return {
            "ride_id": ride.id,
            "completion_acknowledged": ride.completion_acknowledged,
            "feedback_status": ride.feedback_status.value,
        }

    async def generate_rider_receipt(self, db: AsyncSession, ride_id: str, rider_user_id: str) -> tuple[str, bytes]:
        ride = await db.get(Ride, ride_id)
        if not ride:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ride not found")
        await self._enforce_access(db, ride, rider_user_id, UserRole.RIDER)
        if ride.status != RideStatus.RIDE_COMPLETED or ride.final_fare_amount is None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Receipt unavailable for this ride")

        lines = [
            "RideConnect receipt",
            f"Ride ID: {ride.id}",
            f"Pickup: {ride.pickup_address}",
            f"Dropoff: {ride.dropoff_address}",
            f"Completed At: {ride.completed_at.isoformat() if ride.completed_at else ''}",
            f"Total: ${float(ride.final_fare_amount):.2f}",
        ]
        content = self._build_simple_pdf(lines)
        return f"receipt-{ride.id}.pdf", content

    def _build_simple_pdf(self, lines: list[str]) -> bytes:
        escaped = [line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)") for line in lines]
        commands = ["BT", "/F1 14 Tf", "50 760 Td"]
        for index, line in enumerate(escaped):
            if index == 0:
                commands.append(f"({line}) Tj")
            else:
                commands.append("0 -22 Td")
                commands.append(f"({line}) Tj")
        commands.append("ET")
        stream = "\n".join(commands).encode("latin-1")

        objects = [
            b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj",
            b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj",
            b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj",
            b"4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj",
            f"5 0 obj << /Length {len(stream)} >> stream\n".encode("latin-1") + stream + b"\nendstream endobj",
        ]

        pdf = bytearray(b"%PDF-1.4\n")
        offsets = [0]
        for obj in objects:
            offsets.append(len(pdf))
            pdf.extend(obj)
            pdf.extend(b"\n")
        xref_offset = len(pdf)
        pdf.extend(f"xref\n0 {len(offsets)}\n".encode("latin-1"))
        pdf.extend(b"0000000000 65535 f \n")
        for offset in offsets[1:]:
            pdf.extend(f"{offset:010d} 00000 n \n".encode("latin-1"))
        pdf.extend(
            f"trailer << /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF".encode("latin-1")
        )
        return bytes(pdf)

    async def list_active_for_admin(self, db: AsyncSession) -> list[InternalActiveRideItem]:
        rows = (
            await db.execute(
                select(Ride).where(Ride.status.in_([RideStatus.MATCHING, RideStatus.NO_DRIVERS_FOUND, RideStatus.DRIVER_ASSIGNED, RideStatus.DRIVER_EN_ROUTE, RideStatus.DRIVER_ARRIVED, RideStatus.RIDE_STARTED]))
            )
        ).scalars().all()
        items: list[InternalActiveRideItem] = []
        for ride in rows:
            rider = await db.get(Rider, ride.rider_id)
            driver = await db.get(Driver, ride.driver_id) if ride.driver_id else None
            vehicle = await db.get(Vehicle, ride.vehicle_id) if ride.vehicle_id else None
            fare_estimate = await db.get(FareEstimate, ride.fare_estimate_id) if ride.fare_estimate_id else None

            latest_ping = None
            if ride.driver_id:
                latest_ping = await db.scalar(
                    select(TrackingPing)
                    .where(TrackingPing.driver_id == ride.driver_id)
                    .order_by(TrackingPing.recorded_at.desc())
                    .limit(1)
                )

            rider_name = _display_name(
                rider.first_name if rider else None,
                rider.last_name if rider else None,
                f"Rider {ride.rider_id[:8]}",
            )
            driver_name = (
                _display_name(driver.first_name if driver else None, driver.last_name if driver else None, "Unassigned")
                if ride.driver_id
                else None
            )

            items.append(
                InternalActiveRideItem(
                    ride_id=ride.id,
                    status=ride.status.value,
                    pickup_address=ride.pickup_address,
                    dropoff_address=ride.dropoff_address,
                    rider_id=ride.rider_id,
                    rider_name=rider_name,
                    driver_id=ride.driver_id,
                    driver_name=driver_name,
                    region_id=ride.region_id,
                    region=ride.region_id,
                    requested_at=ride.requested_at,
                    eta_minutes=ride.actual_duration_minutes or ride.estimated_duration_minutes,
                    fare=ride.final_fare_amount or (fare_estimate.total_estimated_fare if fare_estimate else None),
                    product_type=(vehicle.vehicle_type if vehicle else None) or (fare_estimate.vehicle_type if fare_estimate else None),
                    driver_lat=latest_ping.latitude if latest_ping else None,
                    driver_lng=latest_ping.longitude if latest_ping else None,
                    dispatch_retry_count=ride.dispatch_retry_count,
                )
            )
        return items

    async def get_unmatched_rides_report(self, db: AsyncSession) -> UnmatchedRideReportResponse:
        rows = (
            await db.execute(
                select(Ride)
                .where(Ride.status == RideStatus.NO_DRIVERS_FOUND)
                .order_by(Ride.requested_at.desc())
            )
        ).scalars().all()

        items: list[UnmatchedRideReportItem] = []
        for ride in rows:
            rider = await db.get(Rider, ride.rider_id)
            latest_event = await db.scalar(
                select(RideEvent)
                .where(RideEvent.ride_id == ride.id)
                .order_by(RideEvent.created_at.desc())
                .limit(1)
            )
            items.append(
                UnmatchedRideReportItem(
                    ride_id=ride.id,
                    rider_name=_display_name(
                        rider.first_name if rider else None,
                        rider.last_name if rider else None,
                        f"Rider {ride.rider_id[:8]}",
                    ),
                    pickup_address=ride.pickup_address,
                    dropoff_address=ride.dropoff_address,
                    requested_at=ride.requested_at,
                    dispatch_retry_count=ride.dispatch_retry_count,
                    recent_activity=latest_event.event_type.replace("_", " ").title() if latest_event else "No recent activity",
                )
            )

        return UnmatchedRideReportResponse(
            total_unmatched_rides=len(items),
            max_dispatch_retries=settings.max_dispatch_retries,
            items=items,
        )

    async def _enforce_access(self, db: AsyncSession, ride: Ride, actor_user_id: str, role: UserRole) -> None:
        if role == UserRole.ADMIN:
            return
        if role == UserRole.RIDER:
            rider = await self.get_rider_or_404(db, actor_user_id)
            if ride.rider_id != rider.id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
            return
        if role == UserRole.DRIVER:
            driver = await db.scalar(select(Driver).where(Driver.user_id == _uuid(actor_user_id)))
            if not driver or ride.driver_id != driver.id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
            return
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


ride_service = RideService()
