from __future__ import annotations

from datetime import datetime, timezone
from math import ceil

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import NotificationDeliveryLog, NotificationJob
from app.schemas.notifications import NotificationJobListItem, NotificationJobListResponse, PaginationResponse


EVENT_NOTIFICATION_RULES: dict[str, list[dict[str, str]]] = {
    "driver_offer_sent": [{"recipient_type": "DRIVER", "recipient_key": "driver_id", "channel": "IN_APP", "template": "driver_offer"}],
    "ride_assigned": [{"recipient_type": "RIDER", "recipient_key": "rider_id", "channel": "IN_APP", "template": "rider_assigned"}],
    "ride_redispatching": [
        {"recipient_type": "RIDER", "recipient_key": "rider_id", "channel": "IN_APP", "template": "ride_redispatching"},
        {"recipient_type": "DRIVER", "recipient_key": "previous_driver_id", "channel": "IN_APP", "template": "ride_reassigned"},
    ],
    "driver_en_route": [{"recipient_type": "RIDER", "recipient_key": "rider_id", "channel": "IN_APP", "template": "driver_en_route"}],
    "driver_arrived": [{"recipient_type": "RIDER", "recipient_key": "rider_id", "channel": "IN_APP", "template": "driver_arrived"}],
    "ride_completed": [
        {"recipient_type": "RIDER", "recipient_key": "rider_id", "channel": "IN_APP", "template": "ride_completed"},
        {"recipient_type": "DRIVER", "recipient_key": "driver_id", "channel": "IN_APP", "template": "ride_completed"},
    ],
    "onboarding_approved": [{"recipient_type": "DRIVER", "recipient_key": "driver_id", "channel": "IN_APP", "template": "onboarding_result"}],
    "onboarding_rejected": [{"recipient_type": "DRIVER", "recipient_key": "driver_id", "channel": "IN_APP", "template": "onboarding_result"}],
}


class NotificationService:
    async def create_jobs_from_event(self, db: AsyncSession, event_type: str, payload: dict) -> list[NotificationJob]:
        mappings = EVENT_NOTIFICATION_RULES.get(event_type, [])
        created: list[NotificationJob] = []
        for mapping in mappings:
            recipient_id = payload.get(mapping["recipient_key"])
            if not recipient_id:
                continue
            job = NotificationJob(
                event_type=event_type,
                recipient_type=mapping["recipient_type"],
                recipient_id=recipient_id,
                channel=mapping["channel"],
                subject=None,
                body_template=mapping["template"],
                payload_json=payload,
                status="SENT",
                sent_at=datetime.now(timezone.utc),
            )
            db.add(job)
            await db.flush()
            db.add(
                NotificationDeliveryLog(
                    notification_job_id=job.id,
                    provider="IN_APP",
                    provider_message_id=None,
                    delivery_status="SENT",
                    delivery_payload=payload,
                )
            )
            created.append(job)
        await db.commit()
        return created

    async def list_jobs(self, db: AsyncSession, page: int, page_size: int) -> NotificationJobListResponse:
        rows = (await db.execute(select(NotificationJob).order_by(NotificationJob.created_at.desc()))).scalars().all()
        total_items = len(rows)
        items = [
            NotificationJobListItem(
                id=row.id,
                event_type=row.event_type,
                recipient_type=row.recipient_type,
                channel=row.channel,
                status=row.status,
                created_at=row.created_at,
            )
            for row in rows[(page - 1) * page_size : page * page_size]
        ]
        return NotificationJobListResponse(
            items=items,
            pagination=PaginationResponse(
                page=page,
                page_size=page_size,
                total_items=total_items,
                total_pages=ceil(total_items / page_size) if page_size else 1,
            ),
        )


notification_service = NotificationService()
