# RideConnect Implementation Roadmap

## Purpose

This roadmap turns the architecture, schema, and API planning into a practical execution sequence.

It is designed for the planned stack:

- FastAPI
- React
- PostgreSQL
- Redis
- SQLAlchemy 2.x
- Pydantic v2
- Alembic
- Docker Compose

The goal is to build RideConnect in a realistic order so that each phase produces something testable and usable.

---

# 1. Build Philosophy

RideConnect should be built in layers:

1. **foundation first**
2. **core backend models and auth**
3. **ride request + driver acceptance**
4. **tracking + admin operations**
5. **polish + production hardening**

This avoids building UI screens before the backend contracts and state transitions exist.

---

# 2. MVP Outcome

At the end of MVP, RideConnect should support:

- rider signup/login
- driver signup/login
- admin login
- driver onboarding submission
- admin approval of drivers
- rider fare estimate
- rider ride request
- driver sees offer
- driver accepts ride
- ride lifecycle updates
- live tracking basics
- admin sees active rides
- driver earnings/history basics

---

# 3. Recommended Delivery Phases

---

## Phase 0 — Project Foundation

### Goal
Create the base repo structure and local development environment.

### Deliverables
- monorepo structure created
- Docker Compose running
- PostgreSQL container running
- Redis container running
- API gateway shell created
- frontend app shells created
- shared environment config added

### Tasks
- create repository folders
- add `.env.example`
- create `docker-compose.yml`
- set up PostgreSQL service
- set up Redis service
- set up FastAPI app shells
- set up React app shells
- create base README

### Output
At the end of this phase, the whole project boots locally.

---

## Phase 1 — Auth Service

### Goal
Build identity and role-based login.

### Deliverables
- auth database schema
- signup/login endpoints
- JWT token generation
- current user endpoint
- admin login
- auth dependency helpers

### Tasks
- create `auth_schema`
- build `users` table
- build `refresh_tokens` table
- implement password hashing
- implement JWT access token logic
- create signup endpoint
- create login endpoint
- create `GET /auth/me`
- create admin login endpoint
- add auth middleware/dependencies

### Output
Rider, driver, and admin users can authenticate.

---

## Phase 2 — Operations Foundations

### Goal
Set up regions, admins, and onboarding models.

### Deliverables
- regions table
- admins table
- driver onboarding profile table
- driver documents table
- admin audit log table
- seed admin script
- seed default region

### Tasks
- create `operations_schema`
- create region model + migration
- create admin model + migration
- create onboarding profile model
- create document model
- create audit log model
- create seed admin command
- create seed region command

### Output
Admin backend foundations are ready.

---

## Phase 3 — Marketplace Foundations

### Goal
Create the rider, driver, vehicle, and pricing core models.

### Deliverables
- riders table
- drivers table
- vehicles table
- pricing rate cards table
- rider profile APIs
- driver profile APIs
- driver availability API

### Tasks
- create `marketplace_schema`
- create `riders` model
- create `drivers` model
- create `vehicles` model
- create `pricing_rate_cards` model
- create rider profile routes
- create driver profile routes
- create driver availability update endpoint

### Output
Core marketplace accounts exist and drivers can be toggled online/offline.

---

## Phase 4 — Onboarding Workflow

### Goal
Enable driver onboarding and admin approval.

### Deliverables
- submit onboarding endpoint
- upload document endpoint
- onboarding queue endpoint
- approve onboarding endpoint
- reject onboarding endpoint
- onboarding UI hooks

### Tasks
- implement driver onboarding submission
- implement driver document upload metadata endpoint
- build onboarding queue for admins
- build approve/reject actions
- update driver `is_approved` when onboarding is approved
- write audit logs on admin actions

### Output
Only approved drivers can participate in dispatch.

---

## Phase 5 — Pricing Engine MVP

### Goal
Return fare estimates before booking.

### Deliverables
- fare estimate logic
- fare estimate endpoint
- pricing snapshot storage
- basic payout estimate

### Tasks
- implement rate-card lookup by region + vehicle type
- calculate:
  - base fare
  - distance fare
  - time fare
  - platform fee
  - total estimate
  - driver payout estimate
- create fare estimate response models
- connect frontend search form to estimate endpoint

### Output
After entering pickup and dropoff, rider can see estimated fare.

---

## Phase 6 — Ride Request Flow

### Goal
Allow rider to request a ride.

### Deliverables
- rides table
- create ride request endpoint
- get ride details endpoint
- ride history endpoint
- ride events table
- basic cancel endpoint

### Tasks
- create `rides` table
- create `ride_events` table
- create `ride_stops` table if needed
- implement ride creation with `REQUESTED`
- log ride event timeline
- implement ride detail endpoint
- implement rider history endpoint
- implement ride cancellation rules

### Output
Rider can request rides and see ride records.

---

## Phase 7 — Dispatch and Driver Offers

### Goal
Implement the heart of the system: driver matching and acceptance.

### Deliverables
- driver offers table
- active offer endpoint for drivers
- accept offer endpoint
- reject offer endpoint
- ride assignment logic

### Tasks
- create `driver_offers` table
- build candidate selection logic:
  - only approved drivers
  - only online drivers
  - only available drivers
  - region-aware filtering
- create offer records
- implement offer expiry logic
- implement accept endpoint
- implement reject endpoint
- update ride to `DRIVER_ASSIGNED` only after accept
- mark driver unavailable once assigned

### Output
Driver accepts ride and assignment becomes official.

### Important rule
```text
REQUESTED → MATCHING → DRIVER_ASSIGNED
```

---

## Phase 8 — Driver Ride Actions

### Goal
Support the full trip lifecycle after acceptance.

### Deliverables
- mark driver en route
- mark arrived
- start ride
- complete ride
- complete ride payout/final fare

### Tasks
- implement `driver-en-route` endpoint
- implement `arrived` endpoint
- implement `start` endpoint
- implement `complete` endpoint
- calculate final fare and payout on completion
- append ride events on every transition

### Output
Ride progresses through all major statuses.

### Status flow
```text
DRIVER_ASSIGNED
→ DRIVER_EN_ROUTE
→ DRIVER_ARRIVED
→ RIDE_STARTED
→ RIDE_COMPLETED
```

---

## Phase 9 — Tracking Layer

### Goal
Handle live driver movement and rider tracking.

### Deliverables
- tracking pings table
- location ping endpoint
- live ride tracking endpoint
- Redis live location cache

### Tasks
- create `tracking_pings` table
- build `POST /tracking/location`
- update Redis latest driver location
- build `GET /tracking/rides/{ride_id}/live`
- compute ETA stub/basic ETA
- connect driver and rider UIs to polling or websocket-ready design

### Output
Rider sees driver moving on map, and admin can view live state.

---

## Phase 10 — Admin Dashboard MVP

### Goal
Give admins control and visibility.

### Deliverables
- dashboard summary endpoint
- active rides list endpoint
- drivers list endpoint
- suspend driver endpoint
- onboarding queue endpoint
- audit log listing basics

### Tasks
- implement dashboard metrics
- implement active ride queries
- implement drivers list filters
- implement suspend driver action
- show pending onboarding reviews
- expose audit logs

### Output
Admin control center becomes operational.

---

## Phase 11 — Notification Service MVP

### Goal
Track and send important platform notifications.

### Deliverables
- notification jobs table
- notification logging
- internal service hooks for ride lifecycle events

### Tasks
- create `notification_jobs`
- create `notification_delivery_logs`
- create notification service shell
- trigger notification jobs on:
  - ride offer sent
  - driver assigned
  - driver arrived
  - ride completed
  - onboarding approved/rejected

### Output
Notification pipeline exists, even if first version is log-only or in-app only.

---

## Phase 12 — Rider Frontend Integration

### Goal
Connect backend to rider booking UI.

### Screens to complete
- login/signup
- booking/search page
- fare result cards
- request ride action
- live tracking page
- ride history page
- profile page

### Tasks
- connect estimate flow
- connect ride request flow
- connect ride status polling
- connect tracking map
- connect ride history and profile

### Output
Rider end-to-end flow works.

---

## Phase 13 — Driver Frontend Integration

### Goal
Connect backend to driver workflow UI.

### Screens to complete
- login
- driver dashboard
- online/offline toggle
- new ride request screen
- accepted ride screen
- en route screen
- arrived screen
- ride in progress
- completed ride summary
- earnings/history
- profile

### Tasks
- connect active offer list
- connect accept/reject actions
- connect ride status actions
- connect location ping loop
- connect history and earnings views

### Output
Driver end-to-end flow works.

---

## Phase 14 — Admin Frontend Integration

### Goal
Connect admin control center to backend.

### Screens to complete
- admin login
- dashboard
- active rides
- drivers management
- onboarding queue
- onboarding review details
- region filter view
- audit logs

### Tasks
- connect admin dashboard summary
- connect active rides table/map
- connect onboarding queue actions
- connect driver suspend action

### Output
Admin users can operate the platform from UI.

---

## Phase 15 — Testing and Validation

### Goal
Make the system stable and predictable.

### Test categories
- unit tests
- API tests
- ride lifecycle tests
- pricing tests
- onboarding tests
- dispatch tests

### Critical test scenarios
- rider creates ride successfully
- unapproved driver does not get offers
- approved + online driver gets offer
- ride only assigns after accept
- ride status transitions are enforced
- ride can complete successfully
- admin can approve onboarding
- suspended driver cannot go online for dispatch

### Output
MVP becomes reliable.

---

## Phase 16 — Production Hardening

### Goal
Prepare for more realistic deployment.

### Tasks
- structured logging
- request tracing
- retry strategy for notifications
- rate limiting
- environment separation
- secure secrets handling
- CORS tightening
- pagination defaults
- validation cleanup
- better error codes
- health check endpoints

### Output
System is cleaner and closer to deployable quality.

---

# 4. Suggested Build Order by Week

This can be adjusted, but this is the recommended sequence.

## Week 1
- Phase 0
- Phase 1

## Week 2
- Phase 2
- Phase 3

## Week 3
- Phase 4
- Phase 5

## Week 4
- Phase 6

## Week 5
- Phase 7

## Week 6
- Phase 8
- Phase 9

## Week 7
- Phase 10
- Phase 11

## Week 8
- Phase 12
- Phase 13
- Phase 14

## Week 9
- Phase 15
- Phase 16

---

# 5. Suggested First Backend Milestone

The first strong backend milestone should be:

```text
Auth + Regions + Drivers + Riders + Vehicles + Pricing + Ride Request
```

That gives you:
- working auth
- user roles
- base entities
- price estimate
- ride creation

This is the correct point before dispatch.

---

# 6. Suggested First End-to-End Milestone

The first full system demo should be:

```text
Rider requests ride
→ Driver sees offer
→ Driver accepts
→ Ride assigned
→ Driver marks en route
→ Driver arrives
→ Driver starts ride
→ Driver completes ride
→ Admin sees ride status
```

That is the best MVP milestone.

---

# 7. Things We Should Not Overbuild Early

Avoid these too early:

- advanced surge pricing
- real payment gateway integration
- complex websocket infra before polling works
- multi-region optimization logic
- support tickets/disputes
- analytics warehouse
- recommendation engines
- route sharing/social features

Build the ride core first.

---

# 8. Technical Checklist Per Service

## auth_service
- [ ] models
- [ ] alembic migrations
- [ ] login/signup
- [ ] JWT
- [ ] auth dependencies
- [ ] tests

## marketplace_service
- [ ] riders/drivers/vehicles models
- [ ] pricing models
- [ ] rides models
- [ ] offers models
- [ ] tracking models
- [ ] ride lifecycle APIs
- [ ] dispatch service
- [ ] tests

## operations_service
- [ ] regions
- [ ] admins
- [ ] onboarding profiles
- [ ] documents
- [ ] audit logs
- [ ] admin APIs
- [ ] tests

## notification_service
- [ ] jobs table
- [ ] delivery logs
- [ ] event triggers
- [ ] tests

---

# 9. Final Recommendation

The implementation should begin with backend foundations before trying to fully finish every frontend screen.

Best order:

```text
Infrastructure
→ Auth
→ Core models
→ Onboarding
→ Pricing
→ Ride request
→ Dispatch
→ Ride lifecycle
→ Tracking
→ Admin
→ Frontend integration
→ Testing
```

This is the roadmap we should follow.

---

# 10. Short Summary

RideConnect should be built in phases, not all at once.

The platform foundation comes first, then the core ride lifecycle, then the live tracking and admin layer, and finally the frontend integration and hardening.

This roadmap is the build sequence we are going to follow.
