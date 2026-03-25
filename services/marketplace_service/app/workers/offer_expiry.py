from __future__ import annotations

import asyncio

from app.db.session import AsyncSessionLocal
from app.services.dispatch_service import dispatch_service


async def run_offer_expiry_worker() -> None:
    while True:
        async with AsyncSessionLocal() as db:
            await dispatch_service.expire_elapsed_offers(db)
            await dispatch_service.recover_stale_matching_rides(db)
            await dispatch_service.auto_redispatch_stalled_prepickup_rides(db)
        await asyncio.sleep(15)
