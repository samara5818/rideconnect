# RideConnect Test Login Credentials

These credentials are created by `infra/scripts/seed_test_users.py`.

## Admin Panel

- App: `frontend/admin_panel`
- Login: `admin@rideconnect.com`
- Password: `ChangeMe123!`

## Rider Web

- App: `frontend/rider_web`
- Login: `rider@rideconnect.com`
- Password: `RiderPass123!`

## Driver Web

- App: `frontend/driver_web`
- Login: `driver@rideconnect.com`
- Password: `DriverPass123!`
- Login: `driver2@rideconnect.com`
- Password: `DriverPass123!`
- Login: `driver3@rideconnect.com`
- Password: `DriverPass123!`
- Login: `driver4@rideconnect.com`
- Password: `DriverPass123!`

Notes:

 - The seeded drivers are marketplace-approved and each has an active vehicle record plus a recent tracking ping for dispatch ranking.
 - Seeded drivers start offline and only count as active in the admin dashboard after they sign in and go online.
- If you need to re-apply these accounts to an existing local database, run:
  - `docker compose exec bootstrap python /app/infra/scripts/seed_test_users.py`
