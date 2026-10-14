# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Domain errors for governed external event candidate review and calendar sync."""


class IntegrationNotFoundError(ValueError):
    """The calendar integration to sync no longer exists; retrying cannot succeed."""


class UnsupportedCalendarTypeError(ValueError):
    """The calendar provider is not supported in this version (#467); retrying cannot succeed."""

    def __init__(self, calendar_type: str) -> None:
        super().__init__(
            f"Kalendertyp {calendar_type} wird in Version 1.0 nicht unterstützt. "
            "Unterstützt werden ICS und CalDAV."
        )


class CandidateReviewError(Exception):
    """Base error for candidate review conflicts."""


class CandidateAlreadyReviewedError(CandidateReviewError):
    """The candidate already has a terminal review decision."""


class CandidateInvalidPeriodError(CandidateReviewError):
    """Candidate start and end do not form a valid interval."""


class CandidateSlotNotAssignableError(CandidateReviewError):
    """The selected planning slot does not meet assignment requirements."""


class CandidateSlotAlreadyLinkedError(CandidateReviewError):
    """The planning slot is already linked or has unresolved local changes."""
