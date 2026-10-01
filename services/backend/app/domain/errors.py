"""Domain errors for governed external event candidate review and calendar sync."""


class IntegrationNotFoundError(ValueError):
    """The calendar integration to sync no longer exists; retrying cannot succeed."""


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
