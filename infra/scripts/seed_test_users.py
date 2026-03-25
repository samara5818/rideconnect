from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import bcrypt
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


AUTH_DATABASE_URL = os.getenv("AUTH_DATABASE_URL", "postgresql+asyncpg://rideconnect:changeme@localhost:5432/rideconnect")
MARKETPLACE_DATABASE_URL = os.getenv(
    "MARKETPLACE_DATABASE_URL",
    "postgresql+asyncpg://rideconnect:changeme@localhost:5432/rideconnect",
)

ADMIN_EMAIL = "admin@rideconnect.com"
ADMIN_PASSWORD = "ChangeMe123!"
RIDER_EMAIL = "rider@rideconnect.com"
RIDER_PHONE = "+15550000001"
RIDER_PASSWORD = "RiderPass123!"
DRIVER_EMAIL = "driver@rideconnect.com"
DRIVER_PHONE = "+15550000002"
DRIVER_PASSWORD = "DriverPass123!"
SEEDED_DRIVERS = [
    {
        "email": DRIVER_EMAIL,
        "phone": DRIVER_PHONE,
        "password": DRIVER_PASSWORD,
        "first_name": "Test",
        "last_name": "Driver",
        "plate_number": "TEST-DRIVER-1",
        "make": "Toyota",
        "model": "Camry",
        "year": 2022,
        "color": "Silver",
        "vehicle_type": "ECONOMY",
        "seat_capacity": 4,
        "fuel_type": "Hybrid",
        "mileage_city": Decimal("42.00"),
        "mileage_highway": Decimal("48.00"),
        "rating_avg": Decimal("4.95"),
        "total_rides_completed": 24,
        "latitude": Decimal("37.7751000"),
        "longitude": Decimal("-122.4183000"),
        "heading": Decimal("90.00"),
        "speed_mph": Decimal("18.50"),
        "accuracy_meters": Decimal("4.00"),
    },
    {
        "email": "driver2@rideconnect.com",
        "phone": "+15550000003",
        "password": DRIVER_PASSWORD,
        "first_name": "Alex",
        "last_name": "Lane",
        "plate_number": "TEST-DRIVER-2",
        "make": "Honda",
        "model": "Accord",
        "year": 2021,
        "color": "Black",
        "vehicle_type": "ECONOMY",
        "seat_capacity": 4,
        "fuel_type": "Gasoline",
        "mileage_city": Decimal("30.00"),
        "mileage_highway": Decimal("38.00"),
        "rating_avg": Decimal("4.91"),
        "total_rides_completed": 41,
        "latitude": Decimal("37.7768000"),
        "longitude": Decimal("-122.4161000"),
        "heading": Decimal("180.00"),
        "speed_mph": Decimal("12.00"),
        "accuracy_meters": Decimal("5.00"),
    },
    {
        "email": "driver3@rideconnect.com",
        "phone": "+15550000004",
        "password": DRIVER_PASSWORD,
        "first_name": "Maya",
        "last_name": "Brooks",
        "plate_number": "TEST-DRIVER-3",
        "make": "Hyundai",
        "model": "Elantra",
        "year": 2023,
        "color": "Blue",
        "vehicle_type": "ECONOMY",
        "seat_capacity": 4,
        "fuel_type": "Hybrid",
        "mileage_city": Decimal("37.00"),
        "mileage_highway": Decimal("44.00"),
        "rating_avg": Decimal("4.88"),
        "total_rides_completed": 17,
        "latitude": Decimal("37.7734000"),
        "longitude": Decimal("-122.4205000"),
        "heading": Decimal("45.00"),
        "speed_mph": Decimal("9.50"),
        "accuracy_meters": Decimal("3.50"),
    },
    {
        "email": "driver4@rideconnect.com",
        "phone": "+15550000005",
        "password": DRIVER_PASSWORD,
        "first_name": "Jordan",
        "last_name": "Reed",
        "plate_number": "TEST-DRIVER-4",
        "make": "Nissan",
        "model": "Altima",
        "year": 2020,
        "color": "White",
        "vehicle_type": "ECONOMY",
        "seat_capacity": 4,
        "fuel_type": "Gasoline",
        "mileage_city": Decimal("28.00"),
        "mileage_highway": Decimal("39.00"),
        "rating_avg": Decimal("4.84"),
        "total_rides_completed": 58,
        "latitude": Decimal("37.7784000"),
        "longitude": Decimal("-122.4147000"),
        "heading": Decimal("270.00"),
        "speed_mph": Decimal("15.00"),
        "accuracy_meters": Decimal("6.00"),
    },
]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


async def upsert_auth_user(conn, *, email: str, phone_number: str | None, password: str, role: str) -> str:
    existing = await conn.execute(
        text("SELECT id FROM auth_schema.users WHERE email = :email"),
        {"email": email},
    )
    user_id = existing.scalar()
    now = datetime.now(timezone.utc)
    if user_id:
        await conn.execute(
            text(
                """
                UPDATE auth_schema.users
                SET phone_number = :phone_number,
                    password_hash = :password_hash,
                    role = :role,
                    is_active = true,
                    is_verified = true,
                    updated_at = :updated_at
                WHERE id = :id
                """
            ),
            {
                "id": user_id,
                "phone_number": phone_number,
                "password_hash": hash_password(password),
                "role": role,
                "updated_at": now,
            },
        )
        return str(user_id)

    user_id = str(uuid4())
    await conn.execute(
        text(
            """
            INSERT INTO auth_schema.users (
                id, email, phone_number, password_hash, role, is_active, is_verified, created_at, updated_at
            ) VALUES (
                :id, :email, :phone_number, :password_hash, :role, true, true, :created_at, :updated_at
            )
            """
        ),
        {
            "id": user_id,
            "email": email,
            "phone_number": phone_number,
            "password_hash": hash_password(password),
            "role": role,
            "created_at": now,
            "updated_at": now,
        },
    )
    return user_id


async def upsert_rider_profile(conn, *, user_id: str, first_name: str, last_name: str | None) -> None:
    existing = await conn.execute(
        text("SELECT id FROM marketplace_schema.riders WHERE user_id = :user_id"),
        {"user_id": user_id},
    )
    rider_id = existing.scalar()
    now = datetime.now(timezone.utc)
    if rider_id:
        await conn.execute(
            text(
                """
                UPDATE marketplace_schema.riders
                SET first_name = :first_name,
                    last_name = :last_name,
                    updated_at = :updated_at
                WHERE id = :id
                """
            ),
            {
                "id": rider_id,
                "first_name": first_name,
                "last_name": last_name,
                "updated_at": now,
            },
        )
        return

    await conn.execute(
        text(
            """
            INSERT INTO marketplace_schema.riders (
                id, user_id, first_name, last_name, default_payment_method, rating_avg, created_at, updated_at
            ) VALUES (
                :id, :user_id, :first_name, :last_name, :default_payment_method, :rating_avg, :created_at, :updated_at
            )
            """
        ),
        {
            "id": str(uuid4()),
            "user_id": user_id,
            "first_name": first_name,
            "last_name": last_name,
            "default_payment_method": "card_visa",
            "rating_avg": Decimal("4.80"),
            "created_at": now,
            "updated_at": now,
        },
    )


async def upsert_driver_profile(
    conn,
    *,
    user_id: str,
    first_name: str,
    last_name: str | None,
    phone_number: str,
    rating_avg: Decimal,
    total_rides_completed: int,
) -> str:
    existing = await conn.execute(
        text("SELECT id FROM marketplace_schema.drivers WHERE user_id = :user_id"),
        {"user_id": user_id},
    )
    driver_id = existing.scalar()
    now = datetime.now(timezone.utc)
    if driver_id:
        await conn.execute(
            text(
                """
                UPDATE marketplace_schema.drivers
                SET first_name = :first_name,
                    last_name = :last_name,
                    phone_number = :phone_number,
                    status = 'ACTIVE',
                    is_online = false,
                    is_available = false,
                    is_approved = true,
                    rating_avg = :rating_avg,
                    total_rides_completed = :total_rides_completed,
                    updated_at = :updated_at
                WHERE id = :id
                """
            ),
            {
                "id": driver_id,
                "first_name": first_name,
                "last_name": last_name,
                "phone_number": phone_number,
                "rating_avg": rating_avg,
                "total_rides_completed": total_rides_completed,
                "updated_at": now,
            },
        )
        return str(driver_id)

    driver_id = str(uuid4())
    await conn.execute(
        text(
            """
            INSERT INTO marketplace_schema.drivers (
                id, user_id, first_name, last_name, phone_number, region_id, status,
                is_online, is_available, is_approved, rating_avg, total_rides_completed, created_at, updated_at
            ) VALUES (
                :id, :user_id, :first_name, :last_name, :phone_number, NULL, 'ACTIVE',
                false, false, true, :rating_avg, :total_rides_completed, :created_at, :updated_at
            )
            """
        ),
        {
            "id": driver_id,
            "user_id": user_id,
            "first_name": first_name,
            "last_name": last_name,
            "phone_number": phone_number,
            "rating_avg": rating_avg,
            "total_rides_completed": total_rides_completed,
            "created_at": now,
            "updated_at": now,
        },
    )
    return driver_id


async def upsert_vehicle(
    conn,
    *,
    driver_id: str,
    plate_number: str,
    make: str,
    model: str,
    year: int,
    color: str,
    vehicle_type: str,
    seat_capacity: int,
    fuel_type: str,
    mileage_city: Decimal,
    mileage_highway: Decimal,
) -> None:
    now = datetime.now(timezone.utc)
    await conn.execute(
        text(
            """
            UPDATE marketplace_schema.vehicles
            SET is_active = false, updated_at = :updated_at
            WHERE driver_id = :driver_id
            """
        ),
        {
            "driver_id": driver_id,
            "updated_at": now,
        },
    )
    existing = await conn.execute(
        text(
            """
            SELECT id FROM marketplace_schema.vehicles
            WHERE driver_id = :driver_id AND plate_number = :plate_number
            ORDER BY created_at DESC
            LIMIT 1
            """
        ),
        {
            "driver_id": driver_id,
            "plate_number": plate_number,
        },
    )
    vehicle_id = existing.scalar()
    if vehicle_id:
        await conn.execute(
            text(
                """
                UPDATE marketplace_schema.vehicles
                SET make = :make,
                    model = :model,
                    year = :year,
                    color = :color,
                    vehicle_type = :vehicle_type,
                    seat_capacity = :seat_capacity,
                    fuel_type = :fuel_type,
                    is_active = true,
                    updated_at = :updated_at
                WHERE id = :id
                """
            ),
            {
                "id": vehicle_id,
                "make": make,
                "model": model,
                "year": year,
                "color": color,
                "vehicle_type": vehicle_type,
                "seat_capacity": seat_capacity,
                "fuel_type": fuel_type,
                "updated_at": now,
            },
        )
        return

    await conn.execute(
        text(
            """
            INSERT INTO marketplace_schema.vehicles (
                id, driver_id, make, model, year, color, plate_number,
                vehicle_type, seat_capacity, fuel_type, mileage_city, mileage_highway, is_active, created_at, updated_at
            ) VALUES (
                :id, :driver_id, :make, :model, :year, :color, :plate_number,
                :vehicle_type, :seat_capacity, :fuel_type, :mileage_city, :mileage_highway, true, :created_at, :updated_at
            )
            """
        ),
        {
            "id": str(uuid4()),
            "driver_id": driver_id,
            "make": make,
            "model": model,
            "year": year,
            "color": color,
            "plate_number": plate_number,
            "vehicle_type": vehicle_type,
            "seat_capacity": seat_capacity,
            "fuel_type": fuel_type,
            "mileage_city": mileage_city,
            "mileage_highway": mileage_highway,
            "created_at": now,
            "updated_at": now,
        },
    )


async def upsert_driver_tracking_ping(
    conn,
    *,
    driver_id: str,
    latitude: Decimal,
    longitude: Decimal,
    heading: Decimal,
    speed_mph: Decimal,
    accuracy_meters: Decimal,
) -> None:
    await conn.execute(
        text("DELETE FROM marketplace_schema.tracking_pings WHERE ride_id IS NULL AND driver_id = :driver_id"),
        {"driver_id": driver_id},
    )
    now = datetime.now(timezone.utc)
    await conn.execute(
        text(
            """
            INSERT INTO marketplace_schema.tracking_pings (
                id, ride_id, driver_id, latitude, longitude, heading, speed_mph, accuracy_meters, recorded_at
            ) VALUES (
                :id, NULL, :driver_id, :latitude, :longitude, :heading, :speed_mph, :accuracy_meters, :recorded_at
            )
            """
        ),
        {
            "id": str(uuid4()),
            "driver_id": driver_id,
            "latitude": latitude,
            "longitude": longitude,
            "heading": heading,
            "speed_mph": speed_mph,
            "accuracy_meters": accuracy_meters,
            "recorded_at": now,
        },
    )


async def main() -> None:
    auth_engine = create_async_engine(AUTH_DATABASE_URL)
    marketplace_engine = create_async_engine(MARKETPLACE_DATABASE_URL)

    async with auth_engine.begin() as auth_conn:
        await upsert_auth_user(
            auth_conn,
            email=ADMIN_EMAIL,
            phone_number=None,
            password=ADMIN_PASSWORD,
            role="ADMIN",
        )
        rider_user_id = await upsert_auth_user(
            auth_conn,
            email=RIDER_EMAIL,
            phone_number=RIDER_PHONE,
            password=RIDER_PASSWORD,
            role="RIDER",
        )
        driver_users: list[tuple[dict, str]] = []
        for driver in SEEDED_DRIVERS:
            driver_user_id = await upsert_auth_user(
                auth_conn,
                email=driver["email"],
                phone_number=driver["phone"],
                password=driver["password"],
                role="DRIVER",
            )
            driver_users.append((driver, driver_user_id))

    async with marketplace_engine.begin() as marketplace_conn:
        await upsert_rider_profile(
            marketplace_conn,
            user_id=rider_user_id,
            first_name="Test",
            last_name="Rider",
        )
        for driver, driver_user_id in driver_users:
            driver_id = await upsert_driver_profile(
                marketplace_conn,
                user_id=driver_user_id,
                first_name=driver["first_name"],
                last_name=driver["last_name"],
                phone_number=driver["phone"],
                rating_avg=driver["rating_avg"],
                total_rides_completed=driver["total_rides_completed"],
            )
            await upsert_vehicle(
                marketplace_conn,
                driver_id=driver_id,
                plate_number=driver["plate_number"],
                make=driver["make"],
                model=driver["model"],
                year=driver["year"],
                color=driver["color"],
                vehicle_type=driver["vehicle_type"],
                seat_capacity=driver["seat_capacity"],
                fuel_type=driver["fuel_type"],
                mileage_city=driver["mileage_city"],
                mileage_highway=driver["mileage_highway"],
            )
            await upsert_driver_tracking_ping(
                marketplace_conn,
                driver_id=driver_id,
                latitude=driver["latitude"],
                longitude=driver["longitude"],
                heading=driver["heading"],
                speed_mph=driver["speed_mph"],
                accuracy_meters=driver["accuracy_meters"],
            )

    await auth_engine.dispose()
    await marketplace_engine.dispose()

    print("Seeded test accounts:")
    print(f"ADMIN  {ADMIN_EMAIL} / {ADMIN_PASSWORD}")
    print(f"RIDER  {RIDER_EMAIL} / {RIDER_PASSWORD}")
    for driver in SEEDED_DRIVERS:
        print(f"DRIVER {driver['email']} / {driver['password']}")


if __name__ == "__main__":
    asyncio.run(main())
