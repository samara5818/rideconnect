#!/usr/bin/env bash 
set -euo pipefail

python /app/infra/scripts/seed_region.py
python /app/infra/scripts/seed_admin.py
python /app/infra/scripts/seed_pricing.py
python /app/infra/scripts/seed_test_users.py
