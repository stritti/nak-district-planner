"""Domain exceptions for governed external-event review."""


class CandidateReviewError(Exception):
    """Base class for candidate review conflicts."""


class CandidateAlreadyReviewedError(CandidateReviewError):
    """Raised when a terminal candidate is reviewed again."""


class CandidateInvalidPeriodError(CandidateReviewError):
    """Raised when the candidate has an invalid time interval."""


class CandidateSlotNotAssignableError(CandidateReviewError):
    """Raised when a target slot cannot be assigned to the candidate."""


class CandidateSlotAlreadyLinkedError(CandidateReviewError):
    """Raised when the target slot is already externally linked or locally dirty."""
