# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Development-only mail transport."""

from __future__ import annotations

import logging

from app.domain.ports.mail import MailService

logger = logging.getLogger(__name__)


class LogMailService(MailService):
    def send(self, to: list[str], subject: str, body: str) -> None:
        logger.info("Development email recipients=%s subject=%s body=%s", to, subject, body)
