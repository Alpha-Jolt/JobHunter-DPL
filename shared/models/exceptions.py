"""Custom exceptions for the shared data persistence layer."""


class SharedLayerError(Exception):
    """Base exception for all shared layer errors."""

    def __init__(self, message: str, context: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.context = context or {}

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.message!r})"


class RegistryError(SharedLayerError):
    """Base exception for all registry-level errors."""


class JobNotFoundError(SharedLayerError):
    """Raised when a job query returns no results."""


class VariantNotFoundError(SharedLayerError):
    """Raised when a variant query returns no results."""


class ApplicationNotFoundError(SharedLayerError):
    """Raised when an application query returns no results."""


class ApprovalRequiredError(SharedLayerError):
    """Raised when attempting to use an unapproved variant."""


class DeserializationError(SharedLayerError):
    """Raised when from_dict() fails validation."""
