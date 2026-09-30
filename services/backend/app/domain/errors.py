"""Domain errors for governed external event candidate review."""


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
