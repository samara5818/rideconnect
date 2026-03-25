from __future__ import annotations

from fastapi import APIRouter, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, require_role
from app.db.session import get_db_session
from app.schemas.driver import DriverAvailabilityRequest, DriverProfileUpdateRequest, DriverSuspendRequest, DriverVehicleUpsertRequest
from app.services.driver_service import driver_service
from shared.python.enums.roles import UserRole
from shared.python.schemas.responses import SuccessResponse

router = APIRouter(tags=["drivers"])


@router.get("/api/v1/drivers/me", response_model=SuccessResponse)
async def get_driver_profile(
    db: AsyncSession = Depends(get_db_session),
    user=Depends(require_role(UserRole.DRIVER)),
):
    return SuccessResponse(data=await driver_service.get_profile(db, user.user_id))


@router.patch("/api/v1/drivers/me", response_model=SuccessResponse)
async def update_driver_profile(
    payload: DriverProfileUpdateRequest,
    db: AsyncSession = Depends(get_db_session),
    user=Depends(require_role(UserRole.DRIVER)),
):
    return SuccessResponse(message="Driver profile updated", data=await driver_service.update_profile(db, user.user_id, payload))


@router.post("/api/v1/drivers/me/availability", response_model=SuccessResponse)
async def update_driver_availability(
    payload: DriverAvailabilityRequest,
    db: AsyncSession = Depends(get_db_session),
    user=Depends(require_role(UserRole.DRIVER)),
):
    return SuccessResponse(message="Driver availability updated", data=await driver_service.update_availability(db, user.user_id, payload))


@router.post("/api/v1/drivers/me/presence/heartbeat", response_model=SuccessResponse)
async def heartbeat_driver_presence(
    db: AsyncSession = Depends(get_db_session),
    user=Depends(require_role(UserRole.DRIVER)),
):
    return SuccessResponse(message="Driver presence heartbeat received", data=await driver_service.heartbeat_presence(db, user.user_id))


@router.get("/api/v1/drivers/me/vehicle", response_model=SuccessResponse)
async def get_driver_vehicle(
    db: AsyncSession = Depends(get_db_session),
    user=Depends(require_role(UserRole.DRIVER)),
):
    return SuccessResponse(data=await driver_service.get_vehicle(db, user.user_id))


@router.post("/api/v1/drivers/me/vehicle", response_model=SuccessResponse, status_code=201)
async def create_driver_vehicle(
    payload: DriverVehicleUpsertRequest,
    db: AsyncSession = Depends(get_db_session),
    user=Depends(require_role(UserRole.DRIVER)),
):
    return SuccessResponse(message="Vehicle created", data=await driver_service.create_vehicle(db, user.user_id, payload))


@router.patch("/api/v1/drivers/me/vehicle", response_model=SuccessResponse)
async def update_driver_vehicle(
    payload: DriverVehicleUpsertRequest,
    db: AsyncSession = Depends(get_db_session),
    user=Depends(require_role(UserRole.DRIVER)),
):
    return SuccessResponse(message="Vehicle updated", data=await driver_service.update_vehicle(db, user.user_id, payload))


@router.get("/api/v1/drivers/me/rides", response_model=SuccessResponse)
async def list_driver_rides(
    page: int = 1,
    page_size: int = 10,
    db: AsyncSession = Depends(get_db_session),
    user=Depends(require_role(UserRole.DRIVER)),
):
    return SuccessResponse(data=await driver_service.list_driver_rides(db, user.user_id, page, page_size))


@router.get("/api/v1/drivers/me/earnings/summary", response_model=SuccessResponse)
async def get_driver_earnings_summary(
    db: AsyncSession = Depends(get_db_session),
    user=Depends(require_role(UserRole.DRIVER)),
):
    return SuccessResponse(data=await driver_service.earnings_summary(db, user.user_id))


@router.get("/api/v1/internal/admin/drivers", response_model=SuccessResponse)
async def internal_admin_drivers(
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db_session),
    _admin=Depends(require_role(UserRole.ADMIN)),
):
    return SuccessResponse(data=await driver_service.list_for_admin(db, page, page_size))


@router.get("/api/v1/internal/admin/drivers/{driver_id}/stats", response_model=SuccessResponse)
async def internal_admin_driver_stats(
    driver_id: str,
    db: AsyncSession = Depends(get_db_session),
    _admin=Depends(require_role(UserRole.ADMIN)),
):
    return SuccessResponse(data=await driver_service.admin_driver_stats(db, driver_id))


@router.get("/api/v1/internal/admin/drivers/{driver_id}/rides", response_model=SuccessResponse)
async def internal_admin_driver_rides(
    driver_id: str,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db_session),
    _admin=Depends(require_role(UserRole.ADMIN)),
):
    return SuccessResponse(data=await driver_service.admin_driver_rides(db, driver_id, page, page_size))


@router.post("/api/v1/internal/admin/drivers/{driver_id}/suspend", response_model=SuccessResponse)
async def internal_suspend_driver(
    driver_id: str,
    payload: DriverSuspendRequest,
    db: AsyncSession = Depends(get_db_session),
    _admin=Depends(require_role(UserRole.ADMIN)),
):
    return SuccessResponse(message="Driver suspended", data=await driver_service.suspend(db, driver_id, payload.reason))
