# RideConnect Service-by-Service Database Schema Specification

## Purpose

This document defines the database schema plan for RideConnect, organized by service boundary.

It is designed to support:

- FastAPI
- Pydantic v2
- SQLAlchemy 2.x
- Alembic migrations
- PostgreSQL
- Redis for live state and caching

This spec follows the planned MVP microservices architecture:

- `auth_service`
- `marketplace_service`
- `operations_service`
- `notification_service`

---

# 1. Database Strategy

For MVP, RideConnect will use:

- **PostgreSQL** as the system of record
- **Redis** for live/ephemeral state and caching

## PostgreSQL layout

Use one PostgreSQL instance with separate schemas:

- `auth_schema`
- `marketplace_schema`
- `operations_schema`
- `notification_schema`

This keeps ownership clear while remaining practical for early development.

---

# 2. Common Standards

## Common columns

Most tables should include:

- `id` UUID primary key
- `created_at` timestamp with timezone
- `updated_at` timestamp with timezone

Where useful, also include:

- `deleted_at` for soft delete
- `created_by`
- `updated_by`

## Naming conventions

- table names: plural snake_case
- columns: snake_case
- foreign keys: `<entity>_id`
- enums: uppercase values in application layer, stored as PostgreSQL enums or constrained strings

## ID strategy

Use UUIDs for all core entities:
- user ids
- rider ids
- driver ids
- ride ids
- offer ids
- admin ids

---

# 3. auth_service Schema

Schema name: `auth_schema`

This service owns identity and role information.

## 3.1 users

Stores all platform identities.

### Columns
- `id` UUID PK
- `email` varchar(255) unique nullable
- `phone_number` varchar(32) unique nullable
- `password_hash` varchar(255) not null
- `role` varchar(32) not null
- `is_active` boolean default true
- `is_verified` boolean default false
- `last_login_at` timestamptz nullable
- `created_at` timestamptz not null
- `updated_at` timestamptz not null

### Role values
- `RIDER`
- `DRIVER`
- `ADMIN`

### Notes
- either email or phone number must be present
- admin login also uses this table

---

## 3.2 refresh_tokens

Stores refresh/session tokens if refresh token flow is used.

### Columns
- `id` UUID PK
- `user_id` UUID FK → `auth_schema.users.id`
- `token_hash` varchar(255) not null
- `expires_at` timestamptz not null
- `revoked_at` timestamptz nullable
- `created_at` timestamptz not null

---

## 3.3 password_reset_tokens

Optional but useful.

### Columns
- `id` UUID PK
- `user_id` UUID FK → `auth_schema.users.id`
- `token_hash` varchar(255) not null
- `expires_at` timestamptz not null
- `used_at` timestamptz nullable
- `created_at` timestamptz not null

---

# 4. marketplace_service Schema

Schema name: `marketplace_schema`

This is the core business schema.

It owns rider profiles, driver profiles, vehicles, rides, offers, pricing, and tracking.

---

## 4.1 riders

Rider business profile.

### Columns
- `id` UUID PK
- `user_id` UUID unique FK → `auth_schema.users.id`
- `first_name` varchar(100) not null
- `last_name` varchar(100) nullable
- `default_payment_method` varchar(64) nullable
- `rating_avg` numeric(3,2) nullable
- `created_at` timestamptz not null
- `updated_at` timestamptz not null

---

## 4.2 rider_saved_places

Saved rider locations.

### Columns
- `id` UUID PK
- `rider_id` UUID FK → `marketplace_schema.riders.id`
- `label` varchar(64) not null
- `address_line` varchar(255) not null
- `latitude` numeric(10,7) not null
- `longitude` numeric(10,7) not null
- `place_provider_id` varchar(128) nullable
- `created_at` timestamptz not null
- `updated_at` timestamptz not null

### Label examples
- `HOME`
- `WORK`
- `CUSTOM`

---

## 4.3 drivers

Driver business profile.

### Columns
- `id` UUID PK
- `user_id` UUID unique FK → `auth_schema.users.id`
- `first_name` varchar(100) not null
- `last_name` varchar(100) nullable
- `phone_number` varchar(32) not null
- `region_id` UUID nullable
- `status` varchar(32) not null
- `is_online` boolean default false
- `is_available` boolean default false
- `is_approved` boolean default false
- `rating_avg` numeric(3,2) nullable
- `total_rides_completed` integer default 0
- `created_at` timestamptz not null
- `updated_at` timestamptz not null

### Driver status values
- `PENDING_APPROVAL`
- `ACTIVE`
- `SUSPENDED`
- `INACTIVE`

### Notes
- `region_id` points logically to operations regions
- for early MVP this can be stored as UUID without strict DB FK across schemas if desired

---

## 4.4 vehicles

Driver vehicle information.

### Columns
- `id` UUID PK
- `driver_id` UUID FK → `marketplace_schema.drivers.id`
- `make` varchar(64) not null
- `model` varchar(64) not null
- `year` integer not null
- `color` varchar(32) nullable
- `plate_number` varchar(32) not null
- `vehicle_type` varchar(32) not null
- `seat_capacity` integer not null
- `fuel_type` varchar(32) nullable
- `mileage_city` numeric(6,2) nullable
- `mileage_highway` numeric(6,2) nullable
- `is_active` boolean default true
- `created_at` timestamptz not null
- `updated_at` timestamptz not null

### Vehicle type values
- `ECONOMY`
- `PREMIUM`
- `XL`

---

## 4.5 rides

Main ride entity.

### Columns
- `id` UUID PK
- `rider_id` UUID FK → `marketplace_schema.riders.id`
- `driver_id` UUID nullable FK → `marketplace_schema.drivers.id`
- `vehicle_id` UUID nullable FK → `marketplace_schema.vehicles.id`
- `region_id` UUID nullable
- `status` varchar(32) not null
- `ride_type` varchar(32) not null
- `pickup_address` varchar(255) not null
- `pickup_latitude` numeric(10,7) not null
- `pickup_longitude` numeric(10,7) not null
- `dropoff_address` varchar(255) not null
- `dropoff_latitude` numeric(10,7) not null
- `dropoff_longitude` numeric(10,7) not null
- `requested_at` timestamptz not null
- `assigned_at` timestamptz nullable
- `driver_en_route_at` timestamptz nullable
- `driver_arrived_at` timestamptz nullable
- `started_at` timestamptz nullable
- `completed_at` timestamptz nullable
- `cancelled_at` timestamptz nullable
- `cancelled_by` varchar(32) nullable
- `cancel_reason` text nullable
- `estimated_distance_miles` numeric(10,2) nullable
- `estimated_duration_minutes` integer nullable
- `actual_distance_miles` numeric(10,2) nullable
- `actual_duration_minutes` integer nullable
- `fare_estimate_id` UUID nullable
- `final_fare_amount` numeric(10,2) nullable
- `driver_payout_amount` numeric(10,2) nullable
- `created_at` timestamptz not null
- `updated_at` timestamptz not null

### Ride status values
- `REQUESTED`
- `MATCHING`
- `DRIVER_ASSIGNED`
- `DRIVER_EN_ROUTE`
- `DRIVER_ARRIVED`
- `RIDE_STARTED`
- `RIDE_COMPLETED`
- `CANCELLED`

### Ride type values
- `ON_DEMAND`
- `SCHEDULED`

---

## 4.6 ride_stops

Optional intermediate stops.

### Columns
- `id` UUID PK
- `ride_id` UUID FK → `marketplace_schema.rides.id`
- `stop_order` integer not null
- `address` varchar(255) not null
- `latitude` numeric(10,7) not null
- `longitude` numeric(10,7) not null
- `created_at` timestamptz not null

---

## 4.7 ride_events

Immutable ride timeline log.

### Columns
- `id` UUID PK
- `ride_id` UUID FK → `marketplace_schema.rides.id`
- `event_type` varchar(64) not null
- `event_payload` jsonb nullable
- `created_at` timestamptz not null

### Event type examples
- `RIDE_REQUESTED`
- `MATCHING_STARTED`
- `DRIVER_OFFER_SENT`
- `DRIVER_ACCEPTED`
- `DRIVER_REJECTED`
- `RIDE_ASSIGNED`
- `DRIVER_EN_ROUTE`
- `DRIVER_ARRIVED`
- `RIDE_STARTED`
- `RIDE_COMPLETED`
- `RIDE_CANCELLED`

---

## 4.8 driver_offers

Dispatch offers sent to drivers.

### Columns
- `id` UUID PK
- `ride_id` UUID FK → `marketplace_schema.rides.id`
- `driver_id` UUID FK → `marketplace_schema.drivers.id`
- `offer_status` varchar(32) not null
- `offered_at` timestamptz not null
- `responded_at` timestamptz nullable
- `expires_at` timestamptz not null
- `created_at` timestamptz not null

### Offer status values
- `PENDING`
- `ACCEPTED`
- `REJECTED`
- `EXPIRED`

### Important rule
A ride is not assigned until an offer is accepted.

---

## 4.9 fare_estimates

Stores pricing outputs.

### Columns
- `id` UUID PK
- `ride_id` UUID nullable FK → `marketplace_schema.rides.id`
- `vehicle_type` varchar(32) not null
- `region_id` UUID nullable
- `distance_miles` numeric(10,2) not null
- `duration_minutes` integer not null
- `base_fare` numeric(10,2) not null
- `distance_fare` numeric(10,2) not null
- `time_fare` numeric(10,2) not null
- `surge_multiplier` numeric(5,2) default 1.00
- `booking_fee` numeric(10,2) default 0.00
- `platform_fee` numeric(10,2) default 0.00
- `total_estimated_fare` numeric(10,2) not null
- `driver_payout_estimate` numeric(10,2) nullable
- `pricing_snapshot` jsonb nullable
- `created_at` timestamptz not null

---

## 4.10 pricing_rate_cards

Region and vehicle pricing rules.

### Columns
- `id` UUID PK
- `region_id` UUID not null
- `vehicle_type` varchar(32) not null
- `base_fare` numeric(10,2) not null
- `per_mile_rate` numeric(10,4) not null
- `per_minute_rate` numeric(10,4) not null
- `minimum_fare` numeric(10,2) not null
- `booking_fee` numeric(10,2) default 0.00
- `platform_fee` numeric(10,2) default 0.00
- `driver_payout_percent` numeric(5,2) nullable
- `is_active` boolean default true
- `effective_from` timestamptz not null
- `effective_to` timestamptz nullable
- `created_at` timestamptz not null
- `updated_at` timestamptz not null

---

## 4.11 tracking_pings

Historical location events from drivers during active flow.

### Columns
- `id` UUID PK
- `ride_id` UUID nullable FK → `marketplace_schema.rides.id`
- `driver_id` UUID FK → `marketplace_schema.drivers.id`
- `latitude` numeric(10,7) not null
- `longitude` numeric(10,7) not null
- `heading` numeric(6,2) nullable
- `speed_mph` numeric(6,2) nullable
- `accuracy_meters` numeric(6,2) nullable
- `recorded_at` timestamptz not null

---

## 4.12 driver_availability_logs

Online/offline and availability changes.

### Columns
- `id` UUID PK
- `driver_id` UUID FK → `marketplace_schema.drivers.id`
- `is_online` boolean not null
- `is_available` boolean not null
- `reason` varchar(64) nullable
- `created_at` timestamptz not null

---

# 5. operations_service Schema

Schema name: `operations_schema`

This schema supports admin operations and onboarding.

---

## 5.1 admins

Admin profile entity.

### Columns
- `id` UUID PK
- `user_id` UUID unique FK → `auth_schema.users.id`
- `display_name` varchar(100) not null
- `admin_role` varchar(32) not null
- `is_active` boolean default true
- `created_at` timestamptz not null
- `updated_at` timestamptz not null

### Admin role values
- `SUPER_ADMIN`
- `OPS_ADMIN`
- `ONBOARDING_ADMIN`
- `REGIONAL_ADMIN`

---

## 5.2 regions

Operational geography scope.

### Columns
- `id` UUID PK
- `code` varchar(64) unique not null
- `name` varchar(100) not null
- `city` varchar(100) nullable
- `state` varchar(100) nullable
- `country` varchar(100) not null
- `is_active` boolean default true
- `created_at` timestamptz not null
- `updated_at` timestamptz not null

---

## 5.3 admin_regions

Maps regional admins to regions.

### Columns
- `id` UUID PK
- `admin_id` UUID FK → `operations_schema.admins.id`
- `region_id` UUID FK → `operations_schema.regions.id`
- `created_at` timestamptz not null

---

## 5.4 driver_onboarding_profiles

Driver onboarding state.

### Columns
- `id` UUID PK
- `driver_id` UUID unique not null
- `region_id` UUID FK → `operations_schema.regions.id`
- `status` varchar(32) not null
- `submitted_at` timestamptz nullable
- `review_started_at` timestamptz nullable
- `reviewed_at` timestamptz nullable
- `reviewed_by_admin_id` UUID nullable FK → `operations_schema.admins.id`
- `review_notes` text nullable
- `rejection_reason` text nullable
- `created_at` timestamptz not null
- `updated_at` timestamptz not null

### Status values
- `DRAFT`
- `SUBMITTED`
- `UNDER_REVIEW`
- `DOCS_PENDING`
- `APPROVED`
- `REJECTED`

---

## 5.5 driver_documents

Onboarding uploaded documents.

### Columns
- `id` UUID PK
- `driver_id` UUID not null
- `document_type` varchar(32) not null
- `file_url` text not null
- `verification_status` varchar(32) not null
- `submitted_at` timestamptz not null
- `reviewed_at` timestamptz nullable
- `reviewed_by_admin_id` UUID nullable FK → `operations_schema.admins.id`
- `rejection_reason` text nullable
- `metadata_json` jsonb nullable
- `created_at` timestamptz not null
- `updated_at` timestamptz not null

### Document type values
- `GOVT_ID_FRONT`
- `GOVT_ID_BACK`
- `DRIVER_LICENSE`
- `VEHICLE_REGISTRATION`
- `INSURANCE`
- `PROFILE_PHOTO`

### Verification status values
- `SUBMITTED`
- `UNDER_REVIEW`
- `APPROVED`
- `REJECTED`

---

## 5.6 admin_audit_logs

Audit trail of admin actions.

### Columns
- `id` UUID PK
- `admin_id` UUID nullable FK → `operations_schema.admins.id`
- `action_type` varchar(64) not null
- `entity_type` varchar(64) not null
- `entity_id` UUID nullable
- `details_json` jsonb nullable
- `created_at` timestamptz not null

### Action examples
- `APPROVED_DRIVER`
- `REJECTED_DRIVER`
- `SUSPENDED_DRIVER`
- `REACTIVATED_DRIVER`
- `VIEWED_RIDE_DETAIL`

---

## 5.7 admin_alerts

System or ops alerts.

### Columns
- `id` UUID PK
- `region_id` UUID nullable FK → `operations_schema.regions.id`
- `alert_type` varchar(64) not null
- `severity` varchar(32) not null
- `title` varchar(255) not null
- `message` text not null
- `is_resolved` boolean default false
- `resolved_by_admin_id` UUID nullable FK → `operations_schema.admins.id`
- `resolved_at` timestamptz nullable
- `created_at` timestamptz not null

### Severity values
- `LOW`
- `MEDIUM`
- `HIGH`
- `CRITICAL`

---

# 6. notification_service Schema

Schema name: `notification_schema`

This service stores notification jobs and delivery history.

---

## 6.1 notification_jobs

Queued outbound notifications.

### Columns
- `id` UUID PK
- `event_type` varchar(64) not null
- `recipient_type` varchar(32) not null
- `recipient_id` UUID not null
- `channel` varchar(32) not null
- `subject` varchar(255) nullable
- `body_template` varchar(128) nullable
- `payload_json` jsonb nullable
- `status` varchar(32) not null
- `scheduled_for` timestamptz nullable
- `sent_at` timestamptz nullable
- `failed_at` timestamptz nullable
- `failure_reason` text nullable
- `created_at` timestamptz not null
- `updated_at` timestamptz not null

### Channel values
- `IN_APP`
- `EMAIL`
- `SMS`
- `PUSH`

### Status values
- `PENDING`
- `SENT`
- `FAILED`
- `CANCELLED`

---

## 6.2 notification_delivery_logs

Delivery tracking.

### Columns
- `id` UUID PK
- `notification_job_id` UUID FK → `notification_schema.notification_jobs.id`
- `provider` varchar(64) nullable
- `provider_message_id` varchar(128) nullable
- `delivery_status` varchar(32) not null
- `delivery_payload` jsonb nullable
- `created_at` timestamptz not null

---

# 7. Redis Usage

Redis should not be the source of truth.

Use Redis for:

## 7.1 live driver location cache
Key example:
- `driver:last_location:{driver_id}`

Value:
- latitude
- longitude
- heading
- speed
- updated_at

## 7.2 driver online availability cache
Key example:
- `driver:availability:{driver_id}`

## 7.3 ride live state cache
Key example:
- `ride:live:{ride_id}`

## 7.4 dispatch candidate queue
Key example:
- `dispatch:candidates:{ride_id}`

## 7.5 temporary offer timers
Key example:
- `offer:expiry:{offer_id}`

---

# 8. Most Important Relationships

## auth to rider
- `auth_schema.users.id` → `marketplace_schema.riders.user_id`

## auth to driver
- `auth_schema.users.id` → `marketplace_schema.drivers.user_id`

## auth to admin
- `auth_schema.users.id` → `operations_schema.admins.user_id`

## ride core relationships
- rider → rides
- driver → rides
- vehicle → rides
- ride → ride_events
- ride → driver_offers
- ride → tracking_pings
- ride → fare_estimates

## onboarding relationships
- driver → onboarding profile
- driver → driver documents
- admin → review actions
- region → onboarding and admin scope

---

# 9. Suggested Alembic Migration Order

## Step 1: auth schema
1. create `auth_schema`
2. create `users`
3. create `refresh_tokens`
4. create `password_reset_tokens`

## Step 2: operations schema foundations
1. create `operations_schema`
2. create `regions`
3. create `admins`
4. create `admin_regions`

## Step 3: marketplace schema foundations
1. create `marketplace_schema`
2. create `riders`
3. create `drivers`
4. create `vehicles`

## Step 4: ride system
1. create `rides`
2. create `ride_stops`
3. create `ride_events`
4. create `driver_offers`
5. create `fare_estimates`
6. create `pricing_rate_cards`
7. create `tracking_pings`
8. create `driver_availability_logs`

## Step 5: onboarding system
1. create `driver_onboarding_profiles`
2. create `driver_documents`
3. create `admin_audit_logs`
4. create `admin_alerts`

## Step 6: notifications
1. create `notification_schema`
2. create `notification_jobs`
3. create `notification_delivery_logs`

---

# 10. Seed Data Plan

## Regions seed
Create at least one default region:

- code: `long_beach_ca`
- name: `Long Beach`
- city: `Long Beach`
- state: `California`
- country: `USA`

## Admin seed
Create default super admin:

- email: `admin@rideconnect.com`
- password: `ChangeMe123!`
- role: `ADMIN`
- admin_role: `SUPER_ADMIN`

## Pricing rate card seed
Create base pricing rows for:
- Long Beach / ECONOMY
- Long Beach / PREMIUM
- Long Beach / XL

---

# 11. Initial API Ownership by Schema

## auth_service APIs use
- `users`
- `refresh_tokens`
- `password_reset_tokens`

## marketplace_service APIs use
- `riders`
- `rider_saved_places`
- `drivers`
- `vehicles`
- `rides`
- `ride_events`
- `driver_offers`
- `fare_estimates`
- `pricing_rate_cards`
- `tracking_pings`

## operations_service APIs use
- `admins`
- `regions`
- `admin_regions`
- `driver_onboarding_profiles`
- `driver_documents`
- `admin_audit_logs`
- `admin_alerts`

## notification_service APIs use
- `notification_jobs`
- `notification_delivery_logs`

---

# 12. Final Build Recommendation

Start implementation with these model groups first:

## First priority
- users
- regions
- admins
- riders
- drivers
- vehicles
- rides
- driver_offers
- driver_onboarding_profiles
- driver_documents
- pricing_rate_cards

## Second priority
- ride_events
- fare_estimates
- tracking_pings
- admin_audit_logs
- notification_jobs

That order supports:
- authentication
- rider booking
- driver onboarding
- driver acceptance
- ride lifecycle
- admin review

---

# 13. Short Summary

This schema spec gives RideConnect a clean database foundation for:

- role-based authentication
- rider and driver accounts
- ride lifecycle state management
- dispatch offers and acceptance
- pricing engine support
- live tracking support
- onboarding and admin workflows
- notification history

This is the schema plan we should build with SQLAlchemy models and Alembic migrations.
