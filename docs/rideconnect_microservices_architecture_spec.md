# RideConnect Microservices Architecture Specification

## Purpose

This document defines the planned microservices architecture for RideConnect, including:

- service boundaries
- responsibilities
- data ownership
- event flows
- API boundaries
- infrastructure layout
- folder structure
- MVP implementation approach

The goal is to build RideConnect in a way that is realistic, scalable, and cleanly structured for future growth, while still being practical for MVP delivery.

---

## 1. Architecture Strategy

RideConnect will follow a **modular microservice-ready architecture**.

Instead of putting all rider, driver, admin, pricing, tracking, and onboarding logic into one large backend, the system will be divided into business-focused services.

### Why this approach

RideConnect has several clearly different domains:

- rider booking
- driver workflow
- dispatch and assignment
- live tracking
- fare calculation
- onboarding and verification
- admin operations

These domains evolve differently and have different runtime behavior. Splitting them into services gives us:

- clearer ownership
- better maintainability
- easier debugging
- easier scaling
- cleaner APIs
- better real-time design

---

## 2. Recommended MVP Service Layout

For MVP, RideConnect should not start with too many independently deployed services.

The best approach is to build **4 main deployable services**:

1. **auth_service**
2. **marketplace_service**
3. **operations_service**
4. **notification_service**

This keeps the architecture clean and microservice-aligned without creating too much operational complexity too early.

---

## 3. High-Level System Diagram

```text
                    ┌──────────────────────────────┐
                    │         Frontend Apps        │
                    │------------------------------│
                    │ Rider Web / Rider App        │
                    │ Driver Web / Driver App      │
                    │ Admin Panel                  │
                    └──────────────┬───────────────┘
                                   │
                                   ▼
                         ┌────────────────────┐
                         │    API Gateway     │
                         └─────────┬──────────┘
                                   │
        ┌──────────────────────────┼──────────────────────────┐
        │                          │                          │
        ▼                          ▼                          ▼
┌─────────────────┐      ┌────────────────────┐      ┌────────────────────┐
│  auth_service   │      │ marketplace_service│      │ operations_service │
│-----------------│      │--------------------│      │--------------------│
│ login           │      │ rider profiles     │      │ admin dashboard    │
│ signup          │      │ driver profiles    │      │ onboarding         │
│ JWT / roles     │      │ ride lifecycle     │      │ region ops         │
│ access control  │      │ dispatch           │      │ audit logs         │
└────────┬────────┘      │ pricing            │      └────────┬───────────┘
         │               │ tracking           │               │
         │               └─────────┬──────────┘               │
         │                         │                          │
         ▼                         ▼                          ▼
   PostgreSQL                PostgreSQL + Redis         PostgreSQL

                                   │
                                   ▼
                         ┌────────────────────┐
                         │ notification_service│
                         │--------------------│
                         │ driver offers      │
                         │ rider alerts       │
                         │ admin alerts       │
                         └────────────────────┘
```

---

## 4. Service-by-Service Breakdown

## 4.1 auth_service

### Responsibility
Identity and access management.

### Handles
- rider login/signup
- driver login/signup
- admin login
- JWT token issuance
- password hashing
- role validation
- session/auth context

### Roles
- RIDER
- DRIVER
- ADMIN

### Key responsibilities
- authenticate users
- authorize protected routes
- expose current user identity
- centralize role-based access control

### Example endpoints
- `POST /api/v1/auth/signup`
- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`
- `POST /api/v1/admin/auth/login`

---

## 4.2 marketplace_service

### Responsibility
Core rider-driver marketplace behavior.

This is the heart of RideConnect.

### Handles
- rider profiles
- driver profiles
- ride creation
- ride lifecycle
- dispatch candidate selection
- driver offer acceptance
- pricing estimates
- trip completion
- live tracking state
- ride state transitions

### Internal domains inside marketplace_service
To keep the code clean, this service should still be modular internally:

- rider module
- driver module
- rides module
- dispatch module
- pricing module
- tracking module

### Key responsibilities
- create ride requests
- maintain ride status
- create and manage driver offers
- confirm driver assignment after accept
- update statuses like:
  - REQUESTED
  - MATCHING
  - DRIVER_ASSIGNED
  - DRIVER_EN_ROUTE
  - DRIVER_ARRIVED
  - RIDE_STARTED
  - RIDE_COMPLETED
  - CANCELLED
- calculate fare estimates and final fare
- store live driver location snapshots
- provide rider and driver active trip data

### Example endpoints
- `POST /api/v1/rides/estimate`
- `POST /api/v1/rides/request`
- `GET /api/v1/rides/{ride_id}`
- `POST /api/v1/driver/offers/{offer_id}/accept`
- `POST /api/v1/driver/offers/{offer_id}/reject`
- `POST /api/v1/rides/{ride_id}/arrived`
- `POST /api/v1/rides/{ride_id}/start`
- `POST /api/v1/rides/{ride_id}/complete`
- `POST /api/v1/tracking/location`

---

## 4.3 operations_service

### Responsibility
Administrative and operational workflows.

### Handles
- admin dashboard
- live ride monitoring
- driver onboarding review
- document verification
- region-based operations views
- driver approval and suspension
- audit logs
- admin metrics

### Key responsibilities
- show active rides
- show active drivers by region
- monitor onboarding queue
- approve/reject onboarding
- suspend/reactivate drivers
- track admin actions

### Example endpoints
- `GET /api/v1/admin/dashboard/summary`
- `GET /api/v1/admin/rides/active`
- `GET /api/v1/admin/drivers`
- `GET /api/v1/admin/onboarding/queue`
- `POST /api/v1/admin/onboarding/{driver_id}/approve`
- `POST /api/v1/admin/onboarding/{driver_id}/reject`
- `POST /api/v1/admin/drivers/{driver_id}/suspend`
- `GET /api/v1/admin/audit-logs`

---

## 4.4 notification_service

### Responsibility
Outbound notifications and event delivery.

### Handles
- driver ride offer notifications
- rider status notifications
- admin alerts
- email/SMS/push integration in future

### Key responsibilities
- send new ride offer to drivers
- notify riders when driver is assigned
- notify rider when driver arrives
- notify driver/admin on important system events
- centralize notification templates and channels

### Example notification events
- `ride_offer_sent`
- `driver_assigned`
- `driver_arrived`
- `ride_started`
- `ride_completed`
- `onboarding_approved`
- `admin_alert_raised`

---

## 5. Future Services (Later Expansion)

These can be split later when the platform grows:

### payments_service
- payment intent
- charge processing
- refunds
- payouts

### analytics_service
- BI dashboards
- historical trends
- operational analytics

### support_service
- disputes
- incident workflows
- support messaging

### geo_service
- routing abstraction
- ETA and geofence logic
- map provider integration

For MVP, these do not need to be separate.

---

## 6. Ride Lifecycle Flow

The main ride lifecycle should work like this:

```text
1. Rider requests a ride
2. marketplace_service creates ride with status REQUESTED
3. marketplace_service moves ride to MATCHING
4. dispatch module finds candidate drivers
5. notification_service sends ride offer to selected driver
6. driver sees offer and accepts
7. ride becomes DRIVER_ASSIGNED
8. driver begins heading to pickup
9. ride becomes DRIVER_EN_ROUTE
10. driver reaches pickup
11. ride becomes DRIVER_ARRIVED
12. driver starts trip
13. ride becomes RIDE_STARTED
14. trip progresses with live tracking updates
15. driver ends trip
16. ride becomes RIDE_COMPLETED
17. final fare and payout are stored
18. notifications are sent to rider and admin views refresh
```

---

## 7. Driver Acceptance Rule

RideConnect must follow this rule:

**A ride is not fully assigned until the driver accepts the offer.**

### Correct flow
```text
ride requested
→ candidate driver selected
→ driver receives offer
→ driver accepts
→ ride becomes DRIVER_ASSIGNED
→ driver heads to pickup
→ ride becomes DRIVER_EN_ROUTE
```

This is important for the driver app flow and the dispatch logic.

---

## 8. Driver Eligibility Rule

A driver must not receive ride offers unless all conditions are true:

```text
driver account is active
driver is approved through onboarding
all required documents are approved
driver is online
driver is available
driver belongs to the correct service region
```

This rule must be enforced by the dispatch module.

---

## 9. Data Ownership

Each service should have clear ownership of data.

## auth_service owns
- users
- credentials
- password hashes
- roles
- sessions/tokens metadata

## marketplace_service owns
- riders
- drivers
- vehicles
- rides
- ride events
- driver offers
- fare estimates
- completed trip data
- current tracking state

## operations_service owns
- regions
- onboarding records
- driver documents
- admin records
- audit logs

## notification_service owns
- notification jobs
- notification templates
- delivery logs

---

## 10. Database Strategy

For MVP, use **PostgreSQL + Redis**.

### PostgreSQL
Primary system of record.

### Redis
Used for:
- short-lived real-time state
- dispatch candidate caching
- event fan-out support
- rate limiting later
- short polling acceleration later

### Recommended initial database layout
Use one PostgreSQL instance, but separate by schema:

- `auth_schema`
- `marketplace_schema`
- `operations_schema`
- `notification_schema`

This gives service boundaries without needing many database instances on day one.

---

## 11. Communication Style

Services should communicate in two ways.

## 11.1 Synchronous API Calls
Use for direct request-response operations.

Examples:
- validate user token
- fetch current user
- get fare estimate
- fetch onboarding review details

## 11.2 Asynchronous Events
Use for state transitions and notifications.

Examples:
- ride_requested
- driver_offer_sent
- driver_accepted
- ride_assigned
- driver_arrived
- ride_started
- ride_completed
- onboarding_approved
- driver_suspended

---

## 12. Core Domain Events

Recommended event list:

```text
user_created
driver_created
driver_went_online
driver_went_offline
ride_requested
ride_matching_started
driver_offer_sent
driver_offer_accepted
driver_offer_rejected
ride_assigned
driver_en_route
driver_arrived
ride_started
ride_completed
ride_cancelled
onboarding_submitted
onboarding_approved
onboarding_rejected
driver_suspended
admin_action_logged
```

---

## 13. Frontend Applications

RideConnect will have three frontend surfaces.

## 13.1 Rider App / Rider Web
Used by riders to:
- request rides
- track rides
- manage profile
- see ride history

## 13.2 Driver App / Driver Web
Used by drivers to:
- log in
- go online/offline
- accept rides
- navigate to pickup
- start and complete rides
- view earnings
- manage profile

## 13.3 Admin Panel
Used by admins to:
- monitor rides
- approve drivers
- manage regions
- suspend drivers
- view live ops status

---

## 14. Recommended Folder Structure

```text
rideconnect/
├── README.md
├── docker-compose.yml
├── .env
├── .env.example
│
├── gateway/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── routes/
│   │   │   ├── auth_proxy.py
│   │   │   ├── marketplace_proxy.py
│   │   │   ├── operations_proxy.py
│   │   │   └── notification_proxy.py
│   │   └── middleware/
│   │       ├── auth_context.py
│   │       └── logging.py
│
├── services/
│   ├── auth_service/
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── alembic.ini
│   │   ├── alembic/
│   │   └── app/
│   │       ├── main.py
│   │       ├── config.py
│   │       ├── db/
│   │       │   ├── session.py
│   │       │   └── base.py
│   │       ├── models/
│   │       │   ├── user.py
│   │       │   └── role.py
│   │       ├── schemas/
│   │       │   ├── auth.py
│   │       │   └── user.py
│   │       ├── api/
│   │       │   ├── auth.py
│   │       │   └── admin_auth.py
│   │       ├── services/
│   │       │   ├── auth_service.py
│   │       │   ├── token_service.py
│   │       │   └── password_service.py
│   │       └── core/
│   │           ├── security.py
│   │           └── deps.py
│   │
│   ├── marketplace_service/
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── alembic.ini
│   │   ├── alembic/
│   │   └── app/
│   │       ├── main.py
│   │       ├── config.py
│   │       ├── db/
│   │       │   ├── session.py
│   │       │   └── base.py
│   │       ├── models/
│   │       │   ├── rider.py
│   │       │   ├── driver.py
│   │       │   ├── vehicle.py
│   │       │   ├── ride.py
│   │       │   ├── ride_event.py
│   │       │   ├── driver_offer.py
│   │       │   ├── tracking_ping.py
│   │       │   └── fare_estimate.py
│   │       ├── schemas/
│   │       │   ├── rider.py
│   │       │   ├── driver.py
│   │       │   ├── ride.py
│   │       │   ├── dispatch.py
│   │       │   ├── pricing.py
│   │       │   └── tracking.py
│   │       ├── api/
│   │       │   ├── riders.py
│   │       │   ├── drivers.py
│   │       │   ├── rides.py
│   │       │   ├── dispatch.py
│   │       │   ├── pricing.py
│   │       │   └── tracking.py
│   │       ├── services/
│   │       │   ├── rider_service.py
│   │       │   ├── driver_service.py
│   │       │   ├── ride_service.py
│   │       │   ├── dispatch_service.py
│   │       │   ├── pricing_service.py
│   │       │   └── tracking_service.py
│   │       ├── core/
│   │       │   ├── enums.py
│   │       │   └── deps.py
│   │       └── events/
│   │           ├── publishers.py
│   │           └── handlers.py
│   │
│   ├── operations_service/
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── alembic.ini
│   │   ├── alembic/
│   │   └── app/
│   │       ├── main.py
│   │       ├── config.py
│   │       ├── db/
│   │       │   ├── session.py
│   │       │   └── base.py
│   │       ├── models/
│   │       │   ├── admin.py
│   │       │   ├── region.py
│   │       │   ├── admin_region.py
│   │       │   ├── driver_onboarding_profile.py
│   │       │   ├── driver_document.py
│   │       │   └── admin_audit_log.py
│   │       ├── schemas/
│   │       │   ├── admin.py
│   │       │   ├── onboarding.py
│   │       │   ├── region.py
│   │       │   └── dashboard.py
│   │       ├── api/
│   │       │   ├── dashboard.py
│   │       │   ├── drivers.py
│   │       │   ├── onboarding.py
│   │       │   ├── regions.py
│   │       │   └── audit_logs.py
│   │       ├── services/
│   │       │   ├── dashboard_service.py
│   │       │   ├── onboarding_service.py
│   │       │   ├── driver_admin_service.py
│   │       │   ├── region_service.py
│   │       │   └── audit_service.py
│   │       └── core/
│   │           ├── deps.py
│   │           └── enums.py
│   │
│   └── notification_service/
│       ├── Dockerfile
│       ├── requirements.txt
│       └── app/
│           ├── main.py
│           ├── config.py
│           ├── api/
│           │   └── notifications.py
│           ├── services/
│           │   ├── notification_service.py
│           │   ├── email_service.py
│           │   └── push_service.py
│           ├── templates/
│           │   ├── driver_offer.html
│           │   ├── rider_assigned.html
│           │   └── onboarding_result.html
│           └── events/
│               ├── consumers.py
│               └── publishers.py
│
├── frontend/
│   ├── rider_web/
│   │   ├── package.json
│   │   ├── vite.config.ts
│   │   └── src/
│   │       ├── app/
│   │       ├── pages/
│   │       ├── components/
│   │       ├── api/
│   │       └── routes/
│   │
│   ├── driver_web/
│   │   ├── package.json
│   │   ├── vite.config.ts
│   │   └── src/
│   │       ├── app/
│   │       ├── pages/
│   │       ├── components/
│   │       ├── api/
│   │       └── routes/
│   │
│   └── admin_panel/
│       ├── package.json
│       ├── vite.config.ts
│       └── src/
│           ├── app/
│           ├── pages/
│           ├── components/
│           ├── api/
│           └── routes/
│
├── shared/
│   ├── python/
│   │   ├── enums/
│   │   ├── utils/
│   │   ├── contracts/
│   │   └── events/
│   └── docs/
│       ├── api_contracts/
│       ├── event_catalog/
│       └── architecture/
│
├── infra/
│   ├── docker/
│   │   ├── postgres/
│   │   ├── redis/
│   │   └── nginx/
│   ├── scripts/
│   │   ├── wait_for_db.sh
│   │   ├── seed_admin.sh
│   │   └── migrate_all.sh
│   └── compose/
│       ├── docker-compose.dev.yml
│       └── docker-compose.prod.yml
│
└── docs/
    ├── architecture/
    │   ├── microservices-overview.md
    │   ├── ride-lifecycle.md
    │   ├── dispatch-flow.md
    │   └── tracking-flow.md
    ├── api/
    └── wireframes/
```

---

## 15. Recommended Frontend App Responsibilities

## rider_web
- landing page
- ride booking
- ride tracking
- ride history
- profile

## driver_web
- driver login
- online/offline state
- ride offer accept/reject
- en route screen
- ride in progress
- earnings
- profile/documents

## admin_panel
- dashboard
- live rides
- drivers
- onboarding queue
- onboarding review
- regions
- audit logs

---

## 16. API Gateway Role

The API gateway should provide a single entry point for frontend apps.

### Responsibilities
- route requests to correct service
- attach auth identity if needed
- standardize headers
- unify public API base path
- allow easier frontend integration

### Example route mapping
- `/api/v1/auth/*` → auth_service
- `/api/v1/rides/*` → marketplace_service
- `/api/v1/driver/*` → marketplace_service
- `/api/v1/admin/*` → operations_service
- `/api/v1/notifications/*` → notification_service

---

## 17. MVP Service Boundaries

### auth_service
Own identity only.

### marketplace_service
Own everything about:
- booking
- ride state
- driver offer acceptance
- dispatch
- pricing
- tracking

### operations_service
Own everything about:
- onboarding
- admin dashboard
- admin moderation
- region visibility
- audit logs

### notification_service
Own outbound messaging only.

This is the implementation boundary for MVP.

---

## 18. Deployment Topology for MVP

Use Docker Compose for local development.

### Containers
- gateway
- auth_service
- marketplace_service
- operations_service
- notification_service
- postgres
- redis
- rider_web
- driver_web
- admin_panel

---

## 19. What We Are Building First

Recommended order of implementation:

### Phase 1
- auth_service
- marketplace_service core models
- operations_service core models
- PostgreSQL
- Redis
- Docker Compose

### Phase 2
- rider booking flow
- driver acceptance flow
- ride lifecycle status flow
- pricing estimate
- basic tracking

### Phase 3
- admin dashboard
- onboarding queue
- driver approval/rejection
- region filtering

### Phase 4
- live updates
- alerts
- audit logs
- richer analytics

---

## 20. Final Implementation Decision

RideConnect will be implemented as a **microservice-oriented platform** with these initial deployable units:

- auth_service
- marketplace_service
- operations_service
- notification_service

This provides a strong industry-style backend foundation while keeping MVP development manageable.

The codebase will be organized to keep domain boundaries clean from day one, so future scaling into more granular services remains straightforward.

---

## 21. Short Summary

RideConnect will use microservices because the platform has multiple distinct domains:

- identity
- rider/driver marketplace
- operations/admin
- notifications

Instead of building one large backend, RideConnect will start with 4 core services, each with clear ownership and folder boundaries.

This is the architecture we are going to build.
