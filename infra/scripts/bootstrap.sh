#!/usr/bin/env bash
set -euo pipefail

sh /app/infra/scripts/wait_for_db.sh
python /app/infra/scripts/reset_stale_alembic_state.py
sh /app/infra/scripts/migrate_all.sh
python /app/infra/scripts/check_schema_drift.py
sh /app/infra/scripts/seed_all.sh
