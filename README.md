# RideConnect

> A production-grade, microservice-based ride-hailing platform — built for speed, designed for scale.

---

## What is RideConnect?

RideConnect is a full-stack ride-hailing MVP with a microservices backend, three separate frontends, and a complete local Docker Compose runtime. It ships with authentication, real-time dispatch, driver onboarding and KYC, admin workflows, and notification infrastructure — all wired together and ready to run.

---

## Architecture at a glance

```
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   Rider Web     │  │   Driver Web    │  │  Admin Panel    │
│  localhost:3001 │  │  localhost:3002 │  │ localhost:3003  │
└────────┬────────┘  └───────┬─────────┘  └────────┬────────┘
         │                   │                     │
         └───────────────────┼─────────────────────┘
                             │
                    ┌────────▼────────┐
                    │  API Gateway    │
                    │ localhost:8000  │
                    └────────┬────────┘
         ┌──────────┬────────┴────────┬──────────────┐
         │          │                 │              │
    ┌────▼───┐ ┌────▼──────┐  ┌────────▼──┐  ┌───────▼──────┐
    │  Auth  │ │Marketplace│  │Operations │  │Notification  │
    │ :8001  │ │  :8002    │  │  :8003    │  │   :8004      │
    └────────┘ └───────────┘  └───────────┘  └──────────────┘
                             │
                    ┌────────┴────────┐
                    │   PostgreSQL    │     Redis
                    │    :55432       │     :6379
                    └─────────────────┘
```

---

## Repository structure

```
rideconnect/
├── services/
│   ├── auth_service/           # Authentication, JWT, roles
│   ├── marketplace_service/    # Rides, dispatch, pricing, tracking, receipts
│   ├── operations_service/     # Onboarding, documents, admin workflows, audit logs
│   └── notification_service/   # Notification and event delivery
├── gateway/                    # API gateway
├── frontend/
│   ├── rider_web/              # Rider-facing app
│   ├── driver_web/             # Driver-facing app
│   └── admin_panel/            # Internal admin panel
├── infra/
│   └── scripts/                # Bootstrap, migrations, seed scripts
├── shared/                     # Shared Python utilities and schemas
└── docs/                       # PRD, SRD, and technical documentation
```

> **Important:** Use `services/*` for all backend work. The `backend/` folder is legacy and not used by the current Docker Compose stack.

---

## Prerequisites

Install before first run:

| Tool | Purpose |
|------|---------|
| [Git](https://git-scm.com) | Version control |
| [Docker Desktop](https://www.docker.com/products/docker-desktop) | Container runtime |
| Docker Compose | Multi-container orchestration |

**Recommended:** Windows 10/11 with Docker Desktop using Linux containers.

> Make sure Docker Desktop is open and the engine is running before starting the stack.

---

## Getting started

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd rideconnect
```

### 2. Create the environment file

```powershell
Copy-Item .env.example .env
```

The default values are pre-configured for local Docker Compose — no edits needed for first run.

### 3. Start the full stack

```bash
docker compose up -d --build --force-recreate
```

This single command handles everything:

- Starts PostgreSQL and Redis
- Waits for the database to be ready
- Runs all Alembic migrations
- Checks for schema drift
- Seeds test data
- Starts all backend services
- Starts the API gateway
- Starts all three frontend apps

### 4. Verify everything is running

```bash
docker compose ps
```

Expect these services to be healthy:

| Service | Status |
|---------|--------|
| `postgres` | Up |
| `redis` | Up |
| `bootstrap` | Exited (0) — completed successfully |
| `auth_service` | Up |
| `marketplace_service` | Up |
| `operations_service` | Up |
| `notification_service` | Up |
| `gateway` | Up |
| `rider_web` | Up |
| `driver_web` | Up |
| `admin_panel` | Up |

### 5. Open the apps

| App | URL |
|-----|-----|
| Rider app | http://localhost:3001 |
| Driver app | http://localhost:3002 |
| Admin panel | http://localhost:3003 |
| API gateway health | http://localhost:8000/health |

**Direct service health endpoints:**

```
http://localhost:8001/api/v1/health   # Auth
http://localhost:8002/api/v1/health   # Marketplace
http://localhost:8003/api/v1/health   # Operations
http://localhost:8004/api/v1/health   # Notification
```

---

## Seeded test credentials

The bootstrap process automatically creates these accounts via `infra/scripts/seed_test_users.py`.

| Role | Email | Password |
|------|-------|----------|
| Admin | `admin@rideconnect.com` | `ChangeMe123!` |
| Rider | `rider@rideconnect.com` | `RiderPass123!` |
| Driver | `driver@rideconnect.com` | `DriverPass123!` |

> **Note:** The seeded driver is pre-approved, has a vehicle registered, and is online — ready for end-to-end dispatch testing immediately.

---

## Common operations

### Reset to a clean state

```bash
docker compose down -v
docker compose up -d --build --force-recreate
```

This removes all PostgreSQL data, Redis data, and stored operations media, then rebuilds from scratch.

### Rebuild a single service

```bash
# Frontend apps
docker compose up -d --build --force-recreate rider_web
docker compose up -d --build --force-recreate driver_web
docker compose up -d --build --force-recreate admin_panel

# Backend services
docker compose up -d --build --force-recreate auth_service marketplace_service operations_service notification_service gateway
```

### Re-run seed scripts against an existing database

```bash
docker compose run --rm bootstrap sh -lc "python /app/infra/scripts/seed_test_users.py"
```

---

## Logs and troubleshooting

```bash
# Check all service statuses
docker compose ps

# Stream all logs
docker compose logs -f

# Inspect a specific service (last 200 lines)
docker compose logs --tail=200 marketplace_service
docker compose logs --tail=200 operations_service
docker compose logs --tail=200 gateway
```

### Docker Desktop not running

If you see this error:

```
failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine
```

Start Docker Desktop first, then rerun the compose command.

### Stale UI after a frontend rebuild

After rebuilding a frontend container, do a hard refresh in the browser. If the issue persists, clear site data and cache for that origin.

---

## Running backend tests

```bash
# Marketplace service tests
pytest services/marketplace_service/tests -q

# Operations service tests
pytest services/operations_service/tests -q
```

**Test coverage includes:**

- Driver onboarding and document upload
- KYC approval flow
- Ride dispatch
- Ride completion
- Admin workflows

---

## Infrastructure reference

### Bootstrap entrypoint

```
infra/scripts/bootstrap.sh
```

Runs in order: DB wait → stale Alembic cleanup → all service migrations → schema drift check → seed scripts.

### Migration script

```
infra/scripts/migrate_all.sh
```

### Seed script

```
infra/scripts/seed_all.sh
```

### Storage notes

| Store | Local port | Notes |
|-------|-----------|-------|
| PostgreSQL | `55432` | Primary data store |
| Redis | `6379` | Cache and queues |
| Driver documents | `operations_media` volume | Stores files; DB stores metadata and relative paths only |

---

## Port reference

| Service | Port |
|---------|------|
| Rider web | `3001` |
| Driver web | `3002` |
| Admin panel | `3003` |
| API gateway | `8000` |
| Auth service | `8001` |
| Marketplace service | `8002` |
| Operations service | `8003` |
| Notification service | `8004` |
| PostgreSQL | `55432` |
| Redis | `6379` |

---

## Key documentation

| Document | Path |
|----------|------|
| Product Requirements | `docs/PRD.md` |
| Software Requirements | `docs/SRD.md` |
| Test credentials | `docs/` |

---

## Development rules

- **Backend:** always use `services/*` — never `backend/`
- **Frontend:** use `frontend/rider_web`, `frontend/driver_web`, `frontend/admin_panel`
- **Requirements:** treat `docs/PRD.md` and `docs/SRD.md` as the single source of truth