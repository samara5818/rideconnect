from __future__ import annotations

from datetime import datetime, timedelta, timezone
import sys
from pathlib import Path

from sqlalchemy import text

SERVICE_ROOT = Path(__file__).resolve().parents[1]
SERVICES_ROOT = SERVICE_ROOT.parent
for path in list(sys.path):
    try:
        resolved = Path(path).resolve()
    except Exception:
        continue
    if resolved.parent == SERVICES_ROOT and resolved.name.endswith("_service"):
        sys.path.remove(path)
sys.path.insert(0, str(SERVICE_ROOT))

from app.core.enums import DriverStatus, OfferStatus, RideStatus, RideType

REGION_ID = "00000000-0000-0000-0000-000000000001"


async def _seed_rate_card(db_session, marketplace_objects):
    card = marketplace_objects["PricingRateCard"](
        region_id=REGION_ID,
        vehicle_type="ECONOMY",
        base_fare=3.50,
        per_mile_rate=1.00,
        per_minute_rate=0.50,
        minimum_fare=5.00,
        booking_fee=0.00,
        platform_fee=1.50,
        driver_payout_percent=80.00,
        is_active=True,
        effective_from=datetime.now(timezone.utc) - timedelta(days=1),
    )
    db_session.add(card)
    await db_session.commit()
    return card


async def test_fare_estimate_returns_correct_calculation(client, db_session, marketplace_objects):
    await _seed_rate_card(db_session, marketplace_objects)
    response = await client.post(
        "/api/v1/rides/estimate",
        json={
            "pickup_address": "Long Beach, CA",
            "pickup_latitude": 33.8041,
            "pickup_longitude": -118.1874,
            "dropoff_address": "LAX",
            "dropoff_latitude": 33.9416,
            "dropoff_longitude": -118.4085,
            "ride_type": "ON_DEMAND",
            "vehicle_type": "ECONOMY",
        },
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["vehicle_type"] == "ECONOMY"
    assert float(data["total_estimated_fare"]) >= 5.0


async def test_ride_request_creates_ride_in_requested_status(client, db_session, rider_auth, marketplace_objects):
    await _seed_rate_card(db_session, marketplace_objects)
    estimate = await client.post(
        "/api/v1/rides/estimate",
        json={
            "pickup_address": "Long Beach, CA",
            "pickup_latitude": 33.8041,
            "pickup_longitude": -118.1874,
            "dropoff_address": "LAX",
            "dropoff_latitude": 33.9416,
            "dropoff_longitude": -118.4085,
            "ride_type": "ON_DEMAND",
            "vehicle_type": "ECONOMY",
        },
    )
    response = await client.post(
        "/api/v1/rides/request",
        headers={"Authorization": rider_auth["Authorization"]},
        json={
            "pickup_address": "Long Beach, CA",
            "pickup_latitude": 33.8041,
            "pickup_longitude": -118.1874,
            "dropoff_address": "LAX",
            "dropoff_latitude": 33.9416,
            "dropoff_longitude": -118.4085,
            "ride_type": "ON_DEMAND",
            "vehicle_type": "ECONOMY",
            "fare_estimate_id": estimate.json()["data"]["estimate_id"],
        },
    )
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "MATCHING"


async def test_unapproved_driver_does_not_appear_in_dispatch_candidates(db_session, rider_auth, marketplace_objects):
    ride_service = marketplace_objects["ride_service"]
    dispatch_service = marketplace_objects["dispatch_service"]
    Ride = marketplace_objects["Ride"]
    Driver = marketplace_objects["Driver"]
    rider = await ride_service.ensure_rider_for_write(db_session, rider_auth["user_id"])
    await db_session.execute(
        text(
            """
            INSERT INTO auth_schema.users (id, email, password_hash, role, is_active, is_verified, created_at, updated_at)
            VALUES (:id, :email, 'x', 'DRIVER', true, true, now(), now())
            """
        ),
        {"id": "00000000-0000-0000-0000-000000000101", "email": "candidate1@test.local"},
    )
    ride = Ride(
        rider_id=rider.id,
        region_id=REGION_ID,
        status=RideStatus.MATCHING,
        ride_type="ON_DEMAND",
        pickup_address="A",
        pickup_latitude=1,
        pickup_longitude=1,
        dropoff_address="B",
        dropoff_latitude=2,
        dropoff_longitude=2,
        requested_at=datetime.now(timezone.utc),
    )
    db_session.add(ride)
    driver = Driver(
        user_id="00000000-0000-0000-0000-000000000101",
        first_name="Driver",
        phone_number="+1",
        region_id=REGION_ID,
        status=DriverStatus.ACTIVE,
        is_online=True,
        is_available=True,
        is_approved=False,
    )
    db_session.add(driver)
    await db_session.commit()
    await dispatch_service.find_candidates(db_session, ride.id)
    offers = (
        await db_session.execute(
            text("SELECT COUNT(*) FROM marketplace_schema.driver_offers WHERE ride_id = :ride_id"),
            {"ride_id": ride.id},
        )
    ).scalar_one()
    assert offers == 0


async def test_offline_driver_does_not_appear_in_dispatch_candidates(db_session, rider_auth, marketplace_objects):
    ride_service = marketplace_objects["ride_service"]
    dispatch_service = marketplace_objects["dispatch_service"]
    Ride = marketplace_objects["Ride"]
    Driver = marketplace_objects["Driver"]
    rider = await ride_service.ensure_rider_for_write(db_session, rider_auth["user_id"])
    await db_session.execute(
        text(
            """
            INSERT INTO auth_schema.users (id, email, password_hash, role, is_active, is_verified, created_at, updated_at)
            VALUES (:id, :email, 'x', 'DRIVER', true, true, now(), now())
            """
        ),
        {"id": "00000000-0000-0000-0000-000000000102", "email": "candidate2@test.local"},
    )
    ride = Ride(
        rider_id=rider.id,
        region_id=REGION_ID,
        status=RideStatus.MATCHING,
        ride_type="ON_DEMAND",
        pickup_address="A",
        pickup_latitude=1,
        pickup_longitude=1,
        dropoff_address="B",
        dropoff_latitude=2,
        dropoff_longitude=2,
        requested_at=datetime.now(timezone.utc),
    )
    db_session.add(ride)
    driver = Driver(
        user_id="00000000-0000-0000-0000-000000000102",
        first_name="Driver",
        phone_number="+1",
        region_id=REGION_ID,
        status=DriverStatus.ACTIVE,
        is_online=False,
        is_available=True,
        is_approved=True,
    )
    db_session.add(driver)
    await db_session.commit()
    await dispatch_service.find_candidates(db_session, ride.id)
    offers = (
        await db_session.execute(
            text("SELECT COUNT(*) FROM marketplace_schema.driver_offers WHERE ride_id = :ride_id"),
            {"ride_id": ride.id},
        )
    ).scalar_one()
    assert offers == 0


async def test_driver_accepting_offer_transitions_ride_to_driver_assigned(db_session, rider_auth, driver_auth, marketplace_objects):
    ride_service = marketplace_objects["ride_service"]
    driver_service = marketplace_objects["driver_service"]
    dispatch_service = marketplace_objects["dispatch_service"]
    Ride = marketplace_objects["Ride"]
    rider = await ride_service.ensure_rider_for_write(db_session, rider_auth["user_id"])
    driver = await driver_service.ensure_driver(db_session, driver_auth["user_id"])
    driver.is_approved = True
    driver.is_online = True
    driver.is_available = True
    driver.status = DriverStatus.ACTIVE
    driver.region_id = REGION_ID
    ride = Ride(
        rider_id=rider.id,
        region_id=REGION_ID,
        status=RideStatus.MATCHING,
        ride_type="ON_DEMAND",
        pickup_address="A",
        pickup_latitude=1,
        pickup_longitude=1,
        dropoff_address="B",
        dropoff_latitude=2,
        dropoff_longitude=2,
        requested_at=datetime.now(timezone.utc),
    )
    db_session.add_all([driver, ride])
    await db_session.commit()
    await dispatch_service.find_candidates(db_session, ride.id)
    offer_id = (
        await db_session.execute(
            text("SELECT id FROM marketplace_schema.driver_offers WHERE ride_id = :ride_id LIMIT 1"),
            {"ride_id": ride.id},
        )
    ).scalar_one()
    result = await dispatch_service.accept_offer(db_session, driver_auth["user_id"], offer_id)
    assert result["ride_status"] == "DRIVER_ASSIGNED"


async def test_ride_status_transition_enforcement(db_session, rider_auth, marketplace_objects):
    import pytest

    ride_service = marketplace_objects["ride_service"]
    Ride = marketplace_objects["Ride"]
    rider = await ride_service.ensure_rider_for_write(db_session, rider_auth["user_id"])
    ride = Ride(
        rider_id=rider.id,
        status=RideStatus.REQUESTED,
        ride_type="ON_DEMAND",
        pickup_address="A",
        pickup_latitude=1,
        pickup_longitude=1,
        dropoff_address="B",
        dropoff_latitude=2,
        dropoff_longitude=2,
        requested_at=datetime.now(timezone.utc),
    )
    db_session.add(ride)
    await db_session.commit()
    with pytest.raises(Exception):
        await ride_service.transition(db_session, ride, RideStatus.RIDE_STARTED, actor_id=rider.id)


async def test_offer_expiry_worker_marks_pending_offers_as_expired(db_session, rider_auth, driver_auth, marketplace_objects):
    ride_service = marketplace_objects["ride_service"]
    driver_service = marketplace_objects["driver_service"]
    dispatch_service = marketplace_objects["dispatch_service"]
    Ride = marketplace_objects["Ride"]
    DriverOffer = marketplace_objects["DriverOffer"]
    rider = await ride_service.ensure_rider_for_write(db_session, rider_auth["user_id"])
    driver = await driver_service.ensure_driver(db_session, driver_auth["user_id"])
    driver.is_approved = True
    driver.is_online = True
    driver.is_available = True
    driver.status = DriverStatus.ACTIVE
    ride = Ride(
        rider_id=rider.id,
        status=RideStatus.MATCHING,
        ride_type="ON_DEMAND",
        pickup_address="A",
        pickup_latitude=1,
        pickup_longitude=1,
        dropoff_address="B",
        dropoff_latitude=2,
        dropoff_longitude=2,
        requested_at=datetime.now(timezone.utc),
    )
    db_session.add_all([driver, ride])
    await db_session.flush()
    offer = DriverOffer(
        ride_id=ride.id,
        driver_id=driver.id,
        offer_status=OfferStatus.PENDING,
        offered_at=datetime.now(timezone.utc) - timedelta(minutes=2),
        expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
        created_at=datetime.now(timezone.utc) - timedelta(minutes=2),
    )
    db_session.add(offer)
    await db_session.commit()
    await dispatch_service.expire_elapsed_offers(db_session)
    refreshed_status = (
        await db_session.execute(
            text("SELECT offer_status FROM marketplace_schema.driver_offers WHERE id = :offer_id"),
            {"offer_id": offer.id},
        )
    ).scalar_one()
    assert refreshed_status == OfferStatus.EXPIRED.value


async def test_dispatch_exhaustion_marks_ride_unmatched_and_surfaces_in_report(db_session, rider_auth, driver_auth, marketplace_objects):
    ride_service = marketplace_objects["ride_service"]
    driver_service = marketplace_objects["driver_service"]
    dispatch_service = marketplace_objects["dispatch_service"]
    Ride = marketplace_objects["Ride"]
    rider = await ride_service.ensure_rider_for_write(db_session, rider_auth["user_id"])
    driver = await driver_service.ensure_driver(db_session, driver_auth["user_id"])
    driver.is_approved = True
    driver.is_online = True
    driver.is_available = True
    driver.status = DriverStatus.ACTIVE
    driver.region_id = REGION_ID
    ride = Ride(
        rider_id=rider.id,
        region_id=REGION_ID,
        status=RideStatus.MATCHING,
        ride_type="ON_DEMAND",
        pickup_address="A",
        pickup_latitude=1,
        pickup_longitude=1,
        dropoff_address="B",
        dropoff_latitude=2,
        dropoff_longitude=2,
        requested_at=datetime.now(timezone.utc),
    )
    db_session.add_all([driver, ride])
    await db_session.commit()

    await dispatch_service.find_candidates(db_session, ride.id)
    first_offer_id = (
        await db_session.execute(
            text(
                "SELECT id FROM marketplace_schema.driver_offers "
                "WHERE ride_id = :ride_id ORDER BY offered_at ASC LIMIT 1"
            ),
            {"ride_id": ride.id},
        )
    ).scalar_one()
    first_reject = await dispatch_service.reject_offer(db_session, driver_auth["user_id"], first_offer_id, "missed")
    assert first_reject["offer_status"] == "REJECTED"

    second_offer_id = (
        await db_session.execute(
            text(
                "SELECT id FROM marketplace_schema.driver_offers "
                "WHERE ride_id = :ride_id AND offer_status = 'PENDING' ORDER BY offered_at DESC LIMIT 1"
            ),
            {"ride_id": ride.id},
        )
    ).scalar_one()
    second_reject = await dispatch_service.reject_offer(db_session, driver_auth["user_id"], second_offer_id, "missed again")
    assert second_reject["offer_status"] == "REJECTED"

    ride_status = (
        await db_session.execute(
            text("SELECT status, dispatch_retry_count FROM marketplace_schema.rides WHERE id = :ride_id"),
            {"ride_id": ride.id},
        )
    ).mappings().one()
    report = await ride_service.get_unmatched_rides_report(db_session)
    assert ride_status["status"] == "NO_DRIVERS_FOUND"
    assert ride_status["dispatch_retry_count"] == 1
    assert report.total_unmatched_rides == 1
    assert report.items[0].ride_id == ride.id
    assert report.items[0].dispatch_retry_count == 1


async def test_ride_completion_receipt_and_rating_flow(client, db_session, rider_auth, driver_auth, marketplace_objects):
    ride_service = marketplace_objects["ride_service"]
    driver_service = marketplace_objects["driver_service"]
    FareEstimate = marketplace_objects["FareEstimate"]
    Ride = marketplace_objects["Ride"]
    Vehicle = marketplace_objects["Vehicle"]
    rider = await ride_service.ensure_rider_for_write(db_session, rider_auth["user_id"])
    driver = await driver_service.ensure_driver(db_session, driver_auth["user_id"])
    driver.is_approved = True
    driver.is_online = True
    driver.is_available = False
    driver.status = DriverStatus.ACTIVE
    driver.region_id = REGION_ID
    vehicle = Vehicle(
        driver_id=driver.id,
        make="Toyota",
        model="Camry",
        year=2022,
        color="Black",
        plate_number="TEST123",
        vehicle_type="ECONOMY",
        seat_capacity=4,
        is_active=True,
    )
    fare_estimate = FareEstimate(
        vehicle_type="ECONOMY",
        region_id=REGION_ID,
        distance_miles=10,
        duration_minutes=20,
        base_fare=3.50,
        distance_fare=10,
        time_fare=5,
        surge_multiplier=1,
        booking_fee=1,
        platform_fee=2,
        total_estimated_fare=21.50,
        driver_payout_estimate=17.20,
        pricing_snapshot={"vehicle_type": "ECONOMY"},
    )
    db_session.add_all([driver, vehicle, fare_estimate])
    await db_session.flush()
    ride = Ride(
        rider_id=rider.id,
        driver_id=driver.id,
        vehicle_id=vehicle.id,
        region_id=REGION_ID,
        status=RideStatus.RIDE_STARTED,
        ride_type=RideType.ON_DEMAND,
        pickup_address="A",
        pickup_latitude=1,
        pickup_longitude=1,
        dropoff_address="B",
        dropoff_latitude=2,
        dropoff_longitude=2,
        payment_method="CARD",
        requested_at=datetime.now(timezone.utc) - timedelta(minutes=30),
        assigned_at=datetime.now(timezone.utc) - timedelta(minutes=25),
        started_at=datetime.now(timezone.utc) - timedelta(minutes=15),
        fare_estimate_id=fare_estimate.id,
    )
    db_session.add(ride)
    await db_session.commit()

    complete_response = await client.post(
        f"/api/v1/rides/{ride.id}/complete",
        headers={"Authorization": driver_auth["Authorization"]},
        json={},
    )
    assert complete_response.status_code == 200
    assert complete_response.json()["data"]["status"] == "RIDE_COMPLETED"

    detail_response = await client.get(
        f"/api/v1/rides/{ride.id}",
        headers={"Authorization": rider_auth["Authorization"]},
    )
    assert detail_response.status_code == 200
    detail = detail_response.json()["data"]
    assert detail["status"] == "RIDE_COMPLETED"
    assert detail["feedback_status"] == "PENDING"
    assert detail["completion_acknowledged"] is False
    assert detail["receipt_available"] is True
    assert detail["can_rate_driver"] is True
    assert detail["payment_method"] == "CARD"

    receipt_response = await client.get(
        f"/api/v1/rider/rides/{ride.id}/receipt",
        headers={"Authorization": rider_auth["Authorization"]},
    )
    assert receipt_response.status_code == 200
    assert receipt_response.headers["content-type"] == "application/pdf"

    rating_response = await client.post(
        f"/api/v1/rider/rides/{ride.id}/rate",
        headers={"Authorization": rider_auth["Authorization"]},
        json={"rating": 5, "comment": "Smooth trip"},
    )
    assert rating_response.status_code == 200
    rating_payload = rating_response.json()["data"]
    assert rating_payload["feedback_status"] == "SUBMITTED"
    assert rating_payload["completion_acknowledged"] is True
    assert rating_payload["rider_rating"] == 5

    refreshed_ride = (
        await db_session.execute(
            text(
                "SELECT status, rider_rating, rider_comment, feedback_status, completion_acknowledged, final_fare_amount "
                "FROM marketplace_schema.rides WHERE id = :ride_id"
            ),
            {"ride_id": ride.id},
        )
    ).mappings().one()
    assert refreshed_ride["status"] == "RIDE_COMPLETED"
    assert refreshed_ride["rider_rating"] == 5
    assert refreshed_ride["rider_comment"] == "Smooth trip"
    assert refreshed_ride["feedback_status"] == "SUBMITTED"
    assert refreshed_ride["completion_acknowledged"] is True
    assert refreshed_ride["final_fare_amount"] is not None


async def test_driver_going_offline_cancels_unfinished_active_ride(client, db_session, rider_auth, driver_auth, marketplace_objects):
    ride_service = marketplace_objects["ride_service"]
    driver_service = marketplace_objects["driver_service"]
    Ride = marketplace_objects["Ride"]
    rider = await ride_service.ensure_rider_for_write(db_session, rider_auth["user_id"])
    driver = await driver_service.ensure_driver(db_session, driver_auth["user_id"])
    driver.is_approved = True
    driver.is_online = True
    driver.is_available = True
    driver.status = DriverStatus.ACTIVE
    driver.region_id = REGION_ID
    ride = Ride(
        rider_id=rider.id,
        driver_id=driver.id,
        region_id=REGION_ID,
        status=RideStatus.DRIVER_ASSIGNED,
        ride_type=RideType.ON_DEMAND,
        pickup_address="A",
        pickup_latitude=1,
        pickup_longitude=1,
        dropoff_address="B",
        dropoff_latitude=2,
        dropoff_longitude=2,
        payment_method="CARD",
        requested_at=datetime.now(timezone.utc) - timedelta(minutes=10),
        assigned_at=datetime.now(timezone.utc) - timedelta(minutes=5),
    )
    db_session.add_all([driver, ride])
    await db_session.commit()

    offline_response = await client.post(
        "/api/v1/drivers/me/availability",
        headers={"Authorization": driver_auth["Authorization"]},
        json={"is_online": False, "is_available": False},
    )
    assert offline_response.status_code == 200

    refreshed_ride = (
        await db_session.execute(
            text(
                "SELECT status, cancelled_by, cancel_reason, completed_at "
                "FROM marketplace_schema.rides WHERE id = :ride_id"
            ),
            {"ride_id": ride.id},
        )
    ).mappings().one()
    assert refreshed_ride["status"] == "CANCELLED"
    assert refreshed_ride["cancelled_by"] == "DRIVER"
    assert refreshed_ride["completed_at"] is None
    assert "offline" in refreshed_ride["cancel_reason"].lower()

    active_rides = await ride_service.list_active_for_admin(db_session)
    assert all(item.ride_id != ride.id for item in active_rides)
