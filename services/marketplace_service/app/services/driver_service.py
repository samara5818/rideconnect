from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from math import ceil
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import CancelledBy, DriverStatus, RideStatus
from app.models import Driver, DriverAvailabilityLog, Ride, RideEvent, Vehicle
from app.schemas.driver import (
    DriverAvailabilityRequest,
    DriverAvailabilityResponse,
    DriverEarningsSummaryResponse,
    DriverProfileResponse,
    DriverProfileUpdateRequest,
    DriverRideHistoryItem,
    DriverVehicleUpsertRequest,
    DriverVehicleResponse,
)
from app.schemas.ride import InternalAdminDriverItem, InternalAdminDriversResponse, PaginationResponse
from app.services.common import to_decimal
from app.services.driver_presence_service import driver_presence_service


def _uuid(value: str) -> UUID:
    return UUID(value)


class DriverService:
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

    async def ensure_driver(self, db: AsyncSession, user_id: str) -> Driver:
        driver = await db.scalar(select(Driver).where(Driver.user_id == _uuid(user_id)))
        if driver:
            return driver
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Driver profile not found")

    async def get_profile(self, db: AsyncSession, user_id: str) -> DriverProfileResponse:
        await driver_presence_service.reconcile_expired_presence(db)
        driver = await self.ensure_driver(db, user_id)
        snapshot = await driver_presence_service.get_snapshot([driver.id])
        presence = snapshot.get(driver.id)
        return DriverProfileResponse(
            id=driver.id,
            first_name=driver.first_name,
            last_name=driver.last_name,
            phone_number=driver.phone_number,
            status=driver.status.value,
            is_online=bool(presence.get("is_online")) if presence else False,
            is_available=bool(presence.get("is_available")) if presence else False,
            is_approved=driver.is_approved,
            rating_avg=driver.rating_avg,
            total_rides_completed=driver.total_rides_completed,
        )

    async def update_profile(self, db: AsyncSession, user_id: str, payload: DriverProfileUpdateRequest) -> DriverProfileResponse:
        driver = await self.ensure_driver(db, user_id)

        if payload.first_name is not None:
            next_first_name = payload.first_name.strip()
            if not next_first_name:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="First name is required")
            driver.first_name = next_first_name

        if payload.last_name is not None:
            next_last_name = payload.last_name.strip()
            driver.last_name = next_last_name or None

        if payload.phone_number is not None:
            next_phone = payload.phone_number.strip()
            if not next_phone:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Phone number is required")
            driver.phone_number = next_phone

        db.add(driver)
        await db.commit()
        await db.refresh(driver)
        return DriverProfileResponse.model_validate(driver, from_attributes=True)

    async def update_availability(
        self,
        db: AsyncSession,
        user_id: str,
        payload: DriverAvailabilityRequest,
    ) -> DriverAvailabilityResponse:
        driver = await self.ensure_driver(db, user_id)
        if not driver.is_approved and payload.is_online:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Driver not approved")
        if driver.status == DriverStatus.SUSPENDED:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Driver not available")
        driver.is_online = payload.is_online
        driver.is_available = payload.is_available and payload.is_online and driver.is_approved
        if driver.is_approved and driver.status != DriverStatus.SUSPENDED:
            driver.status = DriverStatus.ACTIVE
        if not payload.is_online:
            await self._cancel_unfinished_rides_for_driver(
                db,
                driver.id,
                "Driver went offline before completing the ride.",
            )
        db.add(driver)
        db.add(
            DriverAvailabilityLog(
                driver_id=driver.id,
                is_online=driver.is_online,
                is_available=driver.is_available,
                reason="DRIVER_TOGGLE",
            )
        )
        await db.commit()
        if driver.is_online:
            await driver_presence_service.mark_online(driver.id, driver.is_available)
        else:
            await driver_presence_service.mark_offline(driver.id)
        return DriverAvailabilityResponse(driver_id=driver.id, is_online=driver.is_online, is_available=driver.is_available)

    async def heartbeat_presence(self, db: AsyncSession, user_id: str) -> DriverAvailabilityResponse:
        await driver_presence_service.reconcile_expired_presence(db)
        driver = await self.ensure_driver(db, user_id)
        if not driver.is_online or not driver.is_approved or driver.status == DriverStatus.SUSPENDED:
            return DriverAvailabilityResponse(driver_id=driver.id, is_online=False, is_available=False)

        await driver_presence_service.mark_online(driver.id, driver.is_available)
        return DriverAvailabilityResponse(driver_id=driver.id, is_online=True, is_available=driver.is_available)

    async def get_vehicle(self, db: AsyncSession, user_id: str) -> DriverVehicleResponse:
        driver = await self.ensure_driver(db, user_id)
        vehicle = await db.scalar(
            select(Vehicle).where(and_(Vehicle.driver_id == driver.id, Vehicle.is_active.is_(True))).order_by(Vehicle.created_at.desc())
        )
        if not vehicle:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")
        return DriverVehicleResponse.model_validate(vehicle, from_attributes=True)

    async def create_vehicle(self, db: AsyncSession, user_id: str, payload: DriverVehicleUpsertRequest) -> DriverVehicleResponse:
        driver = await self.ensure_driver(db, user_id)
        if not payload.make or not payload.model or payload.year is None or not payload.plate_number or not payload.vehicle_type or payload.seat_capacity is None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Missing required vehicle fields")

        existing = (
            await db.execute(select(Vehicle).where(and_(Vehicle.driver_id == driver.id, Vehicle.is_active.is_(True))))
        ).scalars().all()
        for vehicle in existing:
            vehicle.is_active = False
            db.add(vehicle)

        vehicle = Vehicle(
            driver_id=driver.id,
            make=payload.make,
            model=payload.model,
            year=payload.year,
            color=payload.color,
            plate_number=payload.plate_number,
            vehicle_type=payload.vehicle_type,
            seat_capacity=payload.seat_capacity,
            fuel_type=payload.fuel_type,
            mileage_city=payload.mileage_city,
            mileage_highway=payload.mileage_highway,
            is_active=payload.is_active if payload.is_active is not None else True,
        )
        db.add(vehicle)
        await db.commit()
        await db.refresh(vehicle)
        return DriverVehicleResponse.model_validate(vehicle, from_attributes=True)

    async def update_vehicle(self, db: AsyncSession, user_id: str, payload: DriverVehicleUpsertRequest) -> DriverVehicleResponse:
        driver = await self.ensure_driver(db, user_id)
        vehicle = await db.scalar(
            select(Vehicle).where(and_(Vehicle.driver_id == driver.id, Vehicle.is_active.is_(True))).order_by(Vehicle.created_at.desc())
        )
        if not vehicle:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")

        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(vehicle, field, value)

        db.add(vehicle)
        await db.commit()
        await db.refresh(vehicle)
        return DriverVehicleResponse.model_validate(vehicle, from_attributes=True)

    async def list_driver_rides(self, db: AsyncSession, user_id: str, page: int, page_size: int):
        driver = await self.ensure_driver(db, user_id)
        rows = (
            await db.execute(
                select(Ride)
                .where(Ride.driver_id == driver.id)
                .order_by(Ride.requested_at.desc())
            )
        ).scalars().all()
        total_items = len(rows)
        items = [
            DriverRideHistoryItem(
                ride_id=ride.id,
                pickup_address=ride.pickup_address,
                dropoff_address=ride.dropoff_address,
                status=ride.status.value,
                completed_at=ride.completed_at,
                driver_payout_amount=ride.driver_payout_amount,
            )
            for ride in rows[(page - 1) * page_size : page * page_size]
        ]
        return {
            "items": items,
            "pagination": PaginationResponse(
                page=page,
                page_size=page_size,
                total_items=total_items,
                total_pages=ceil(total_items / page_size) if page_size else 1,
            ),
        }

    async def earnings_summary(self, db: AsyncSession, user_id: str) -> DriverEarningsSummaryResponse:
        driver = await self.ensure_driver(db, user_id)
        now = datetime.now(timezone.utc)
        today_start = datetime.combine(date.today(), datetime.min.time(), tzinfo=timezone.utc)
        week_start = now - timedelta(days=7)
        month_start = now - timedelta(days=30)
        rows = (
            await db.execute(select(Ride).where(and_(Ride.driver_id == driver.id, Ride.status == RideStatus.RIDE_COMPLETED)))
        ).scalars().all()
        today = sum((ride.driver_payout_amount or 0) for ride in rows if ride.completed_at and ride.completed_at >= today_start)
        week = sum((ride.driver_payout_amount or 0) for ride in rows if ride.completed_at and ride.completed_at >= week_start)
        month = sum((ride.driver_payout_amount or 0) for ride in rows if ride.completed_at and ride.completed_at >= month_start)
        rides_completed_today = sum(1 for ride in rows if ride.completed_at and ride.completed_at >= today_start)
        return DriverEarningsSummaryResponse(
            today_earnings=to_decimal(today),
            week_earnings=to_decimal(week),
            month_earnings=to_decimal(month),
            rides_completed_today=rides_completed_today,
        )

    async def list_for_admin(self, db: AsyncSession, page: int, page_size: int) -> InternalAdminDriversResponse:
        await driver_presence_service.reconcile_expired_presence(db)
        rows = (await db.execute(
            select(Driver).where(Driver.is_approved.is_(True)).order_by(Driver.created_at.desc())
        )).scalars().all()
        snapshot = await driver_presence_service.get_snapshot([row.id for row in rows])
        total_items = len(rows)
        items = [
            InternalAdminDriverItem(
                driver_id=row.id,
                first_name=row.first_name,
                last_name=row.last_name,
                status=row.status.value,
                is_online=bool(snapshot.get(row.id, {}).get("is_online", False)),
                is_available=bool(snapshot.get(row.id, {}).get("is_available", False)),
                is_approved=row.is_approved,
                total_rides_completed=row.total_rides_completed,
            )
            for row in rows[(page - 1) * page_size : page * page_size]
        ]
        return InternalAdminDriversResponse(
            items=items,
            pagination=PaginationResponse(
                page=page,
                page_size=page_size,
                total_items=total_items,
                total_pages=ceil(total_items / page_size) if page_size else 1,
            ),
        )

    async def admin_driver_stats(self, db: AsyncSession, driver_id: str) -> dict:
        now = datetime.now(timezone.utc)
        today_start = datetime.combine(date.today(), datetime.min.time(), tzinfo=timezone.utc)
        week_start = now - timedelta(days=7)
        month_start = now - timedelta(days=30)

        all_rides = (await db.execute(
            select(Ride).where(Ride.driver_id == driver_id)
        )).scalars().all()

        completed = [r for r in all_rides if r.status == RideStatus.RIDE_COMPLETED]

        total_miles = sum(float(r.actual_distance_miles or 0) for r in completed)
        total_payout = sum(float(r.driver_payout_amount or 0) for r in completed)
        today_payout = sum(
            float(r.driver_payout_amount or 0) for r in completed
            if r.completed_at and r.completed_at >= today_start
        )
        week_payout = sum(
            float(r.driver_payout_amount or 0) for r in completed
            if r.completed_at and r.completed_at >= week_start
        )
        month_payout = sum(
            float(r.driver_payout_amount or 0) for r in completed
            if r.completed_at and r.completed_at >= month_start
        )

        # Calculate total online hours from availability log pairs
        logs = (await db.execute(
            select(DriverAvailabilityLog)
            .where(DriverAvailabilityLog.driver_id == driver_id)
            .order_by(DriverAvailabilityLog.created_at)
        )).scalars().all()

        total_online_seconds = 0.0
        online_since: datetime | None = None
        for log in logs:
            if log.is_online and online_since is None:
                online_since = log.created_at
            elif not log.is_online and online_since is not None:
                total_online_seconds += (log.created_at - online_since).total_seconds()
                online_since = None
        if online_since is not None:
            total_online_seconds += (now - online_since).total_seconds()

        return {
            "total_rides": len(all_rides),
            "total_completed_rides": len(completed),
            "total_miles": round(total_miles, 1),
            "total_payout": round(total_payout, 2),
            "today_payout": round(today_payout, 2),
            "week_payout": round(week_payout, 2),
            "month_payout": round(month_payout, 2),
            "total_online_hours": round(total_online_seconds / 3600, 1),
        }

    async def admin_driver_rides(self, db: AsyncSession, driver_id: str, page: int, page_size: int) -> dict:
        all_rides = (await db.execute(
            select(Ride)
            .where(Ride.driver_id == driver_id)
            .order_by(Ride.requested_at.desc())
        )).scalars().all()

        total_items = len(all_rides)
        page_rides = all_rides[(page - 1) * page_size: page * page_size]

        items = [
            {
                "ride_id": r.id,
                "pickup_address": r.pickup_address,
                "dropoff_address": r.dropoff_address,
                "status": r.status.value,
                "requested_at": r.requested_at.isoformat() if r.requested_at else None,
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                "actual_distance_miles": float(r.actual_distance_miles) if r.actual_distance_miles else None,
                "actual_duration_minutes": r.actual_duration_minutes,
                "driver_payout_amount": float(r.driver_payout_amount) if r.driver_payout_amount else None,
            }
            for r in page_rides
        ]

        return {
            "items": items,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_items": total_items,
                "total_pages": ceil(total_items / page_size) if page_size else 1,
            },
        }

    async def suspend(self, db: AsyncSession, driver_id: str, reason: str) -> dict:
        driver = await db.get(Driver, driver_id)
        if not driver:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Driver not found")
        driver.status = DriverStatus.SUSPENDED
        driver.is_online = False
        driver.is_available = False
        db.add(driver)
        db.add(DriverAvailabilityLog(driver_id=driver.id, is_online=False, is_available=False, reason=reason))
        await db.commit()
        await driver_presence_service.mark_offline(driver.id)
        return {"driver_id": driver.id, "status": driver.status.value}


driver_service = DriverService()
