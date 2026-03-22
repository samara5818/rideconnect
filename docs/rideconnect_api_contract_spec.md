# RideConnect API Contract Specification

## Purpose

This document defines the API contracts for RideConnect MVP across the planned services:

- `auth_service`
- `marketplace_service`
- `operations_service`
- `notification_service`

This spec is intended to align:

- React frontend apps
- FastAPI backend services
- Pydantic request/response models
- service boundaries
- future OpenAPI generation

The API style follows:

- REST-first endpoints
- JSON request/response bodies
- JWT auth
- predictable pagination
- explicit status transitions
- versioned routes under `/api/v1`

---

# 1. Global API Conventions

## Base path

```text
/api/v1
```

## Content type

```http
Content-Type: application/json
Accept: application/json
```

## Authentication

Protected routes use bearer tokens:

```http
Authorization: Bearer <jwt_token>
```

## Standard response envelope

RideConnect should keep responses consistent.

### Success response shape

```json
{
  "success": true,
  "message": "Optional message",
  "data": {}
}
```

### Error response shape

```json
{
  "success": false,
  "message": "Human-readable error",
  "error_code": "MACHINE_CODE",
  "details": {}
}
```

---

# 2. Auth Service Contracts

Base route:

```text
/api/v1/auth
```

---

## 2.1 Rider/Driver Signup

### Endpoint
`POST /api/v1/auth/signup`

### Request body
```json
{
  "email": "user@example.com",
  "phone_number": "+13237769433",
  "password": "StrongPassword123!",
  "role": "RIDER"
}
```

### Allowed roles
- `RIDER`
- `DRIVER`

### Response
```json
{
  "success": true,
  "message": "Account created successfully",
  "data": {
    "user_id": "uuid",
    "role": "RIDER"
  }
}
```

---

## 2.2 Login

### Endpoint
`POST /api/v1/auth/login`

### Request body
```json
{
  "email_or_phone": "user@example.com",
  "password": "StrongPassword123!"
}
```

### Response
```json
{
  "success": true,
  "message": "Login successful",
  "data": {
    "access_token": "jwt-token",
    "refresh_token": "refresh-token",
    "token_type": "bearer",
    "user": {
      "user_id": "uuid",
      "role": "RIDER",
      "is_active": true
    }
  }
}
```

---

## 2.3 Current User

### Endpoint
`GET /api/v1/auth/me`

### Auth
Required

### Response
```json
{
  "success": true,
  "data": {
    "user_id": "uuid",
    "email": "user@example.com",
    "phone_number": "+13237769433",
    "role": "RIDER",
    "is_active": true
  }
}
```

---

## 2.4 Admin Login

### Endpoint
`POST /api/v1/admin/auth/login`

### Request body
```json
{
  "email_or_phone": "admin@rideconnect.com",
  "password": "StrongPassword123!"
}
```

### Response
```json
{
  "success": true,
  "message": "Admin login successful",
  "data": {
    "access_token": "jwt-token",
    "refresh_token": "refresh-token",
    "token_type": "bearer",
    "user": {
      "user_id": "uuid",
      "role": "ADMIN"
    }
  }
}
```

---

# 3. Marketplace Service Contracts

Base route groups:

```text
/api/v1/riders
/api/v1/drivers
/api/v1/rides
/api/v1/driver
/api/v1/tracking
/api/v1/pricing
```

---

# 4. Rider APIs

---

## 4.1 Get Rider Profile

### Endpoint
`GET /api/v1/riders/me`

### Auth
RIDER required

### Response
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "user_id": "uuid",
    "first_name": "Sam",
    "last_name": "Reddy",
    "rating_avg": 4.8
  }
}
```

---

## 4.2 Update Rider Profile

### Endpoint
`PATCH /api/v1/riders/me`

### Request body
```json
{
  "first_name": "Sam",
  "last_name": "Reddy"
}
```

### Response
```json
{
  "success": true,
  "message": "Profile updated",
  "data": {
    "id": "uuid",
    "first_name": "Sam",
    "last_name": "Reddy"
  }
}
```

---

## 4.3 List Saved Places

### Endpoint
`GET /api/v1/riders/me/saved-places`

### Response
```json
{
  "success": true,
  "data": [
    {
      "id": "uuid",
      "label": "HOME",
      "address_line": "123 Main St, Long Beach, CA",
      "latitude": 33.8041,
      "longitude": -118.1874
    }
  ]
}
```

---

## 4.4 Create Saved Place

### Endpoint
`POST /api/v1/riders/me/saved-places`

### Request body
```json
{
  "label": "WORK",
  "address_line": "456 Office St, Long Beach, CA",
  "latitude": 33.80,
  "longitude": -118.19
}
```

### Response
```json
{
  "success": true,
  "message": "Saved place created",
  "data": {
    "id": "uuid",
    "label": "WORK"
  }
}
```

---

# 5. Driver APIs

---

## 5.1 Get Driver Profile

### Endpoint
`GET /api/v1/drivers/me`

### Auth
DRIVER required

### Response
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "first_name": "Ravi",
    "last_name": "Kumar",
    "phone_number": "+13237769433",
    "status": "ACTIVE",
    "is_online": false,
    "is_available": false,
    "is_approved": true,
    "rating_avg": 4.9,
    "total_rides_completed": 248
  }
}
```

---

## 5.2 Update Driver Availability

### Endpoint
`POST /api/v1/drivers/me/availability`

### Purpose
Driver toggles online/offline and availability.

### Request body
```json
{
  "is_online": true,
  "is_available": true
}
```

### Response
```json
{
  "success": true,
  "message": "Driver availability updated",
  "data": {
    "driver_id": "uuid",
    "is_online": true,
    "is_available": true
  }
}
```

---

## 5.3 Get Driver Vehicle

### Endpoint
`GET /api/v1/drivers/me/vehicle`

### Response
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "make": "Toyota",
    "model": "Camry",
    "year": 2020,
    "plate_number": "ABC1234",
    "vehicle_type": "ECONOMY",
    "seat_capacity": 4
  }
}
```

---

# 6. Pricing APIs

---

## 6.1 Fare Estimate

### Endpoint
`POST /api/v1/rides/estimate`

### Purpose
Used before requesting ride. Frontend uses it after pickup and dropoff are selected.

### Request body
```json
{
  "pickup_address": "Long Beach, CA",
  "pickup_latitude": 33.8041,
  "pickup_longitude": -118.1874,
  "dropoff_address": "LAX",
  "dropoff_latitude": 33.9416,
  "dropoff_longitude": -118.4085,
  "ride_type": "ON_DEMAND",
  "vehicle_type": "ECONOMY"
}
```

### Response
```json
{
  "success": true,
  "data": {
    "estimate_id": "uuid",
    "vehicle_type": "ECONOMY",
    "distance_miles": 21.4,
    "duration_minutes": 34,
    "base_fare": 3.5,
    "distance_fare": 18.2,
    "time_fare": 7.8,
    "booking_fee": 0.0,
    "platform_fee": 1.5,
    "surge_multiplier": 1.0,
    "total_estimated_fare": 31.0,
    "driver_payout_estimate": 24.8
  }
}
```

---

# 7. Ride Request and Lifecycle APIs

---

## 7.1 Create Ride Request

### Endpoint
`POST /api/v1/rides/request`

### Auth
RIDER required

### Request body
```json
{
  "pickup_address": "Long Beach, CA",
  "pickup_latitude": 33.8041,
  "pickup_longitude": -118.1874,
  "dropoff_address": "LAX",
  "dropoff_latitude": 33.9416,
  "dropoff_longitude": -118.4085,
  "ride_type": "ON_DEMAND",
  "vehicle_type": "ECONOMY",
  "fare_estimate_id": "uuid"
}
```

### Response
```json
{
  "success": true,
  "message": "Ride requested successfully",
  "data": {
    "ride_id": "uuid",
    "status": "REQUESTED",
    "requested_at": "2026-03-15T12:00:00Z"
  }
}
```

---

## 7.2 Get Ride Details

### Endpoint
`GET /api/v1/rides/{ride_id}`

### Auth
RIDER, DRIVER, ADMIN allowed based on ownership/permission

### Response
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "status": "DRIVER_EN_ROUTE",
    "ride_type": "ON_DEMAND",
    "pickup_address": "Long Beach, CA",
    "dropoff_address": "LAX",
    "driver": {
      "id": "uuid",
      "first_name": "Ravi",
      "last_name": "Kumar",
      "rating_avg": 4.9
    },
    "vehicle": {
      "make": "Toyota",
      "model": "Camry",
      "plate_number": "ABC1234",
      "vehicle_type": "ECONOMY"
    },
    "estimated_distance_miles": 21.4,
    "estimated_duration_minutes": 34,
    "final_fare_amount": null
  }
}
```

---

## 7.3 List Rider Ride History

### Endpoint
`GET /api/v1/rides/me/history?page=1&page_size=10`

### Response
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "ride_id": "uuid",
        "pickup_address": "Long Beach, CA",
        "dropoff_address": "LAX",
        "status": "RIDE_COMPLETED",
        "completed_at": "2026-03-14T18:30:00Z",
        "final_fare_amount": 32.5
      }
    ],
    "pagination": {
      "page": 1,
      "page_size": 10,
      "total_items": 24,
      "total_pages": 3
    }
  }
}
```

---

## 7.4 Cancel Ride

### Endpoint
`POST /api/v1/rides/{ride_id}/cancel`

### Auth
RIDER or DRIVER depending on current phase and policy

### Request body
```json
{
  "cancel_reason": "Changed plans"
}
```

### Response
```json
{
  "success": true,
  "message": "Ride cancelled",
  "data": {
    "ride_id": "uuid",
    "status": "CANCELLED",
    "cancelled_at": "2026-03-15T12:15:00Z"
  }
}
```

---

# 8. Driver Offer and Acceptance APIs

These are the most important for the driver workflow.

---

## 8.1 List Active Driver Offers

### Endpoint
`GET /api/v1/driver/offers/active`

### Auth
DRIVER required

### Response
```json
{
  "success": true,
  "data": [
    {
      "offer_id": "uuid",
      "ride_id": "uuid",
      "pickup_address": "Long Beach, CA",
      "dropoff_address": "LAX",
      "distance_to_pickup_miles": 3.8,
      "trip_distance_miles": 21.4,
      "estimated_payout": 24.8,
      "expires_at": "2026-03-15T12:00:20Z",
      "offer_status": "PENDING"
    }
  ]
}
```

---

## 8.2 Accept Driver Offer

### Endpoint
`POST /api/v1/driver/offers/{offer_id}/accept`

### Rule
This action confirms assignment.

### Response
```json
{
  "success": true,
  "message": "Ride offer accepted",
  "data": {
    "offer_id": "uuid",
    "ride_id": "uuid",
    "offer_status": "ACCEPTED",
    "ride_status": "DRIVER_ASSIGNED",
    "assigned_at": "2026-03-15T12:01:00Z"
  }
}
```

---

## 8.3 Reject Driver Offer

### Endpoint
`POST /api/v1/driver/offers/{offer_id}/reject`

### Request body
```json
{
  "reason": "Too far"
}
```

### Response
```json
{
  "success": true,
  "message": "Ride offer rejected",
  "data": {
    "offer_id": "uuid",
    "offer_status": "REJECTED"
  }
}
```

---

# 9. Driver Ride Action APIs

---

## 9.1 Mark Driver En Route

### Endpoint
`POST /api/v1/rides/{ride_id}/driver-en-route`

### Auth
DRIVER required

### Response
```json
{
  "success": true,
  "message": "Ride updated to driver en route",
  "data": {
    "ride_id": "uuid",
    "status": "DRIVER_EN_ROUTE",
    "driver_en_route_at": "2026-03-15T12:03:00Z"
  }
}
```

---

## 9.2 Mark Driver Arrived

### Endpoint
`POST /api/v1/rides/{ride_id}/arrived`

### Response
```json
{
  "success": true,
  "message": "Driver marked as arrived",
  "data": {
    "ride_id": "uuid",
    "status": "DRIVER_ARRIVED",
    "driver_arrived_at": "2026-03-15T12:12:00Z"
  }
}
```

---

## 9.3 Start Ride

### Endpoint
`POST /api/v1/rides/{ride_id}/start`

### Response
```json
{
  "success": true,
  "message": "Ride started",
  "data": {
    "ride_id": "uuid",
    "status": "RIDE_STARTED",
    "started_at": "2026-03-15T12:14:00Z"
  }
}
```

---

## 9.4 Complete Ride

### Endpoint
`POST /api/v1/rides/{ride_id}/complete`

### Request body
```json
{
  "actual_distance_miles": 21.9,
  "actual_duration_minutes": 37
}
```

### Response
```json
{
  "success": true,
  "message": "Ride completed",
  "data": {
    "ride_id": "uuid",
    "status": "RIDE_COMPLETED",
    "completed_at": "2026-03-15T12:51:00Z",
    "final_fare_amount": 33.75,
    "driver_payout_amount": 26.2
  }
}
```

---

# 10. Tracking APIs

---

## 10.1 Submit Driver Location Ping

### Endpoint
`POST /api/v1/tracking/location`

### Auth
DRIVER required

### Request body
```json
{
  "ride_id": "uuid",
  "latitude": 33.8123,
  "longitude": -118.2011,
  "heading": 185.0,
  "speed_mph": 24.3,
  "accuracy_meters": 8.5
}
```

### Response
```json
{
  "success": true,
  "message": "Location received",
  "data": {
    "driver_id": "uuid",
    "ride_id": "uuid",
    "recorded_at": "2026-03-15T12:05:00Z"
  }
}
```

---

## 10.2 Get Live Ride Tracking

### Endpoint
`GET /api/v1/tracking/rides/{ride_id}/live`

### Auth
RIDER, DRIVER, ADMIN based on permission

### Response
```json
{
  "success": true,
  "data": {
    "ride_id": "uuid",
    "status": "DRIVER_EN_ROUTE",
    "driver_location": {
      "latitude": 33.8123,
      "longitude": -118.2011,
      "heading": 185.0,
      "updated_at": "2026-03-15T12:05:00Z"
    },
    "pickup_location": {
      "latitude": 33.8041,
      "longitude": -118.1874
    },
    "dropoff_location": {
      "latitude": 33.9416,
      "longitude": -118.4085
    },
    "eta_minutes": 7
  }
}
```

---

# 11. Driver Earnings and Activity APIs

---

## 11.1 Driver Ride History

### Endpoint
`GET /api/v1/drivers/me/rides?page=1&page_size=10`

### Response
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "ride_id": "uuid",
        "pickup_address": "Long Beach, CA",
        "dropoff_address": "LAX",
        "status": "RIDE_COMPLETED",
        "completed_at": "2026-03-14T18:30:00Z",
        "driver_payout_amount": 26.2
      }
    ],
    "pagination": {
      "page": 1,
      "page_size": 10,
      "total_items": 42,
      "total_pages": 5
    }
  }
}
```

---

## 11.2 Driver Earnings Summary

### Endpoint
`GET /api/v1/drivers/me/earnings/summary`

### Response
```json
{
  "success": true,
  "data": {
    "today_earnings": 124.5,
    "week_earnings": 682.4,
    "month_earnings": 2410.75,
    "rides_completed_today": 6
  }
}
```

---

# 12. Operations/Admin APIs

Base route:

```text
/api/v1/admin
```

---

## 12.1 Admin Dashboard Summary

### Endpoint
`GET /api/v1/admin/dashboard/summary`

### Auth
ADMIN required

### Response
```json
{
  "success": true,
  "data": {
    "active_rides": 28,
    "online_drivers": 142,
    "pending_onboarding_reviews": 3,
    "active_regions": 1
  }
}
```

---

## 12.2 List Active Rides

### Endpoint
`GET /api/v1/admin/rides/active?region_id=<uuid>`

### Response
```json
{
  "success": true,
  "data": [
    {
      "ride_id": "uuid",
      "status": "DRIVER_EN_ROUTE",
      "rider_name": "John D.",
      "driver_name": "Ravi Kumar",
      "pickup_address": "Long Beach, CA",
      "dropoff_address": "LAX",
      "requested_at": "2026-03-15T12:00:00Z"
    }
  ]
}
```

---

## 12.3 List Drivers

### Endpoint
`GET /api/v1/admin/drivers?status=ACTIVE&region_id=<uuid>&page=1&page_size=20`

### Response
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "driver_id": "uuid",
        "first_name": "Ravi",
        "last_name": "Kumar",
        "status": "ACTIVE",
        "is_online": true,
        "is_available": true,
        "is_approved": true
      }
    ],
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total_items": 142,
      "total_pages": 8
    }
  }
}
```

---

## 12.4 Suspend Driver

### Endpoint
`POST /api/v1/admin/drivers/{driver_id}/suspend`

### Request body
```json
{
  "reason": "Document issue"
}
```

### Response
```json
{
  "success": true,
  "message": "Driver suspended",
  "data": {
    "driver_id": "uuid",
    "status": "SUSPENDED"
  }
}
```

---

# 13. Onboarding APIs

---

## 13.1 Submit Onboarding Profile

### Endpoint
`POST /api/v1/drivers/me/onboarding`

### Auth
DRIVER required

### Request body
```json
{
  "region_id": "uuid"
}
```

### Response
```json
{
  "success": true,
  "message": "Onboarding profile submitted",
  "data": {
    "status": "SUBMITTED"
  }
}
```

---

## 13.2 Upload Driver Document

### Endpoint
`POST /api/v1/drivers/me/documents`

### Note
May later become multipart/form-data. For MVP spec, metadata is shown as JSON.

### Request body
```json
{
  "document_type": "DRIVER_LICENSE",
  "file_url": "https://storage.example.com/license.pdf"
}
```

### Response
```json
{
  "success": true,
  "message": "Document uploaded",
  "data": {
    "document_id": "uuid",
    "document_type": "DRIVER_LICENSE",
    "verification_status": "SUBMITTED"
  }
}
```

---

## 13.3 List Onboarding Queue

### Endpoint
`GET /api/v1/admin/onboarding/queue?status=SUBMITTED&page=1&page_size=20`

### Response
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "driver_id": "uuid",
        "driver_name": "Ravi Kumar",
        "region_name": "Long Beach",
        "status": "SUBMITTED",
        "submitted_at": "2026-03-15T11:00:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total_items": 3,
      "total_pages": 1
    }
  }
}
```

---

## 13.4 Approve Onboarding

### Endpoint
`POST /api/v1/admin/onboarding/{driver_id}/approve`

### Request body
```json
{
  "review_notes": "All documents verified"
}
```

### Response
```json
{
  "success": true,
  "message": "Driver approved successfully",
  "data": {
    "driver_id": "uuid",
    "status": "APPROVED",
    "reviewed_at": "2026-03-15T12:10:00Z"
  }
}
```

---

## 13.5 Reject Onboarding

### Endpoint
`POST /api/v1/admin/onboarding/{driver_id}/reject`

### Request body
```json
{
  "rejection_reason": "Insurance document invalid"
}
```

### Response
```json
{
  "success": true,
  "message": "Driver onboarding rejected",
  "data": {
    "driver_id": "uuid",
    "status": "REJECTED"
  }
}
```

---

# 14. Notification APIs

Base route:

```text
/api/v1/notifications
```

For MVP, this service may be mostly internal. Still, define minimal admin visibility APIs.

---

## 14.1 List Notification Jobs

### Endpoint
`GET /api/v1/notifications/jobs?page=1&page_size=20`

### Auth
ADMIN required

### Response
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "uuid",
        "event_type": "driver_assigned",
        "recipient_type": "RIDER",
        "channel": "IN_APP",
        "status": "SENT",
        "created_at": "2026-03-15T12:00:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total_items": 120,
      "total_pages": 6
    }
  }
}
```

---

# 15. Pagination Standard

Any list endpoint should return:

```json
{
  "items": [],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_items": 100,
    "total_pages": 5
  }
}
```

Default query params:
- `page=1`
- `page_size=20`

Max `page_size`:
- `100`

---

# 16. HTTP Status Codes

Recommended usage:

- `200 OK` → normal success
- `201 Created` → new resource created
- `400 Bad Request` → invalid payload
- `401 Unauthorized` → missing/invalid auth
- `403 Forbidden` → wrong role or access denied
- `404 Not Found` → missing entity
- `409 Conflict` → invalid state transition
- `422 Unprocessable Entity` → semantic validation issue
- `500 Internal Server Error` → unexpected backend failure

---

# 17. Important State Transition Rules

The backend must enforce these:

## Ride request flow
```text
REQUESTED → MATCHING → DRIVER_ASSIGNED
```

## Driver movement flow
```text
DRIVER_ASSIGNED → DRIVER_EN_ROUTE → DRIVER_ARRIVED
```

## Trip execution flow
```text
DRIVER_ARRIVED → RIDE_STARTED → RIDE_COMPLETED
```

## Cancellation rule
Cancellation should not allow invalid backward transitions.

## Offer acceptance rule
Ride assignment happens only after:
```text
driver offer status = ACCEPTED
```

---

# 18. Suggested Pydantic Model Grouping

For implementation, create Pydantic schemas grouped as:

## auth_service
- `SignupRequest`
- `LoginRequest`
- `TokenResponse`
- `CurrentUserResponse`

## marketplace_service
- `FareEstimateRequest`
- `FareEstimateResponse`
- `CreateRideRequest`
- `RideDetailResponse`
- `DriverOfferResponse`
- `DriverAvailabilityRequest`
- `TrackingPingRequest`
- `LiveTrackingResponse`

## operations_service
- `DashboardSummaryResponse`
- `ApproveOnboardingRequest`
- `RejectOnboardingRequest`
- `DriverListResponse`
- `OnboardingQueueResponse`

## notification_service
- `NotificationJobResponse`
- `NotificationJobListResponse`

---

# 19. Frontend Mapping

## Rider frontend pages should call
- login
- profile
- fare estimate
- request ride
- ride tracking
- ride history
- cancel ride

## Driver frontend pages should call
- login
- driver profile
- online/offline toggle
- active offers
- accept/reject offer
- driver en route
- arrived
- start ride
- complete ride
- tracking ping
- earnings summary

## Admin frontend pages should call
- admin login
- dashboard summary
- active rides
- drivers list
- onboarding queue
- approve/reject onboarding
- suspend driver
- audit/notification views later

---

# 20. Final MVP API Scope

The minimum set needed to build end-to-end MVP is:

## Required first
- signup/login
- current user
- rider profile
- driver profile
- fare estimate
- create ride
- get ride detail
- driver offers list
- driver accept/reject offer
- driver availability update
- mark en route
- mark arrived
- start ride
- complete ride
- tracking ping
- admin dashboard summary
- onboarding queue
- approve/reject onboarding

This is the contract set the frontend and backend should implement first.

---

# 21. Short Summary

This API contract spec defines the request and response structure for RideConnect MVP.

It gives a clean interface between:
- React frontend apps
- FastAPI services
- database-backed domain logic

This is the API contract plan we should use for backend implementation and frontend integration.
