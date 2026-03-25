from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel


class DriverProfileResponse(BaseModel):
    id: str
    first_name: str
    last_name: str | None = None
    phone_number: str
    status: str
    is_online: bool
    is_available: bool
    is_approved: bool
    rating_avg: Decimal | None = None
    total_rides_completed: int
    reassigned_ride_id: str | None = None
    reassignment_notice: str | None = None
    reassignment_at: object | None = None


class DriverProfileUpdateRequest(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    phone_number: str | None = None


class DriverAvailabilityRequest(BaseModel):
    is_online: bool
    is_available: bool


class DriverAvailabilityResponse(BaseModel):
    driver_id: str
    is_online: bool
    is_available: bool


class DriverVehicleResponse(BaseModel):
    id: str
    driver_id: str
    make: str
    model: str
    year: int
    color: str | None = None
    plate_number: str
    vehicle_type: str
    seat_capacity: int
    fuel_type: str | None = None
    mileage_city: Decimal | None = None
    mileage_highway: Decimal | None = None
    is_active: bool


class DriverVehicleUpsertRequest(BaseModel):
    make: str | None = None
    model: str | None = None
    year: int | None = None
    color: str | None = None
    plate_number: str | None = None
    vehicle_type: str | None = None
    seat_capacity: int | None = None
    fuel_type: str | None = None
    mileage_city: Decimal | None = None
    mileage_highway: Decimal | None = None
    is_active: bool | None = None


class DriverRideHistoryItem(BaseModel):
    ride_id: str
    pickup_address: str
    dropoff_address: str
    status: str
    completed_at: object | None = None
    driver_payout_amount: Decimal | None = None


class DriverEarningsSummaryResponse(BaseModel):
    today_earnings: Decimal
    week_earnings: Decimal
    month_earnings: Decimal
    rides_completed_today: int


class DriverSuspendRequest(BaseModel):
    reason: str
