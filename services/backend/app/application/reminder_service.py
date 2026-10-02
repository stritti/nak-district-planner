"""Monthly reminder orchestration independent of Celery and HTTP."""

from __future__ import annotations

import logging
import re
import uuid
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.orm_models.district import DistrictORM
from app.adapters.db.orm_models.district_reminder_config import ReminderDeliveryORM
from app.adapters.db.orm_models.membership import MembershipORM
from app.adapters.db.orm_models.user import UserORM
from app.adapters.db.repositories.district_reminder_config import SqlDistrictReminderConfigRepository
from app.domain.models.district_reminder_config import DistrictReminderConfig
from app.domain.ports.mail import MailDeliveryError, MailService

logger = logging.getLogger(__name__)
BERLIN = ZoneInfo("Europe/Berlin")
MONTH_NAMES = (
    "", "Januar", "Februar", "März", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember",
)
PLACEHOLDER = re.compile(r"\{(district_name|month|year|day)\}")


def render_template(template: str, district_name: str, today: date) -> str:
    """Replace only supported placeholders; preserve unknown placeholders verbatim."""
    values = {
        "district_name": district_name,
        "month": MONTH_NAMES[today.month],
        "year": str(today.year),
        "day": str(today.day),
    }
    return PLACEHOLDER.sub(lambda match: values[match.group(1)], template)


async def recipient_emails(session: AsyncSession, config: DistrictReminderConfig) -> list[str]:
    """Resolve only exact district-scoped memberships with the configured role."""
    result = await session.execute(
        select(UserORM.email)
        .join(MembershipORM, MembershipORM.user_sub == UserORM.sub)
        .where(
            MembershipORM.scope_type == "DISTRICT",
            MembershipORM.scope_id == config.district_id,
            MembershipORM.role == config.recipient_role.value,
        )
        .distinct()
    )
    return sorted({email for email in result.scalars().all() if email})


async def dispatch_reminders(
    session: AsyncSession,
    mail_service: MailService,
    *,
    now: datetime | None = None,
) -> dict[str, int]:
    """Process each due reminder independently, with per-recipient monthly claims.

    Claims prevent concurrent beat invocations from dispatching the same message.
    A failed or uncertain send remains claimed: operators must explicitly
    reconcile it before re-dispatch to avoid duplicating an accepted SMTP mail.
    """
    local_now = (now or datetime.now(UTC)).astimezone(BERLIN)
    month = local_now.date().replace(day=1)
    repository = SqlDistrictReminderConfigRepository(session)
    configs = await repository.list_active()
    summary = {"evaluated": len(configs), "sent": 0, "skipped": 0, "failed": 0}
    for config in configs:
        if not config.is_due(local_now):
            summary["skipped"] += 1
            continue
        district = await session.get(DistrictORM, config.district_id)
        if district is None:
            logger.warning("Reminder %s refers to missing district", config.id)
            summary["skipped"] += 1
            continue
        recipients = await recipient_emails(session, config)
        if not recipients:
            logger.warning("Reminder %s has no recipients", config.id)
            summary["skipped"] += 1
            continue
        subject = render_template(config.subject_template, district.name, local_now.date())
        body = render_template(config.body_template, district.name, local_now.date())
        for recipient in recipients:
            # A unique database claim is the concurrency boundary. Commit it
            # before the external SMTP side effect to avoid double sends.
            claim = (
                insert(ReminderDeliveryORM)
                .values(
                    id=uuid.uuid4(), reminder_id=config.id, scheduled_month=month,
                    recipient=recipient, claimed_at=datetime.now(UTC),
                )
                .on_conflict_do_nothing(constraint="uq_reminder_delivery")
                .returning(ReminderDeliveryORM.id)
            )
            result = await session.execute(claim)
            claim_id = result.scalar_one_or_none()
            await session.commit()
            if claim_id is None:
                summary["skipped"] += 1
                continue
            try:
                mail_service.send([recipient], subject, body)
            except MailDeliveryError:
                logger.exception("Reminder %s delivery failed; claim %s requires review", config.id, claim_id)
                summary["failed"] += 1
                continue
            await session.execute(
                ReminderDeliveryORM.__table__.update()
                .where(ReminderDeliveryORM.id == claim_id)
                .values(sent_at=datetime.now(UTC))
            )
            await session.commit()
            summary["sent"] += 1
    logger.info("Monthly reminder check completed: %s", summary)
    return summary
