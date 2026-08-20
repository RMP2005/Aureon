"""Custom exception classes and error handlers."""

from fastapi import HTTPException, status


class AureonException(Exception):
    """Base exception for Aureon."""

    def __init__(self, message: str = "An unexpected error occurred") -> None:
        self.message = message
        super().__init__(self.message)


class EntityNotFoundError(AureonException):
    """Raised when a requested entity is not found."""

    def __init__(self, entity: str, entity_id: str) -> None:
        super().__init__(f"{entity} with id '{entity_id}' not found")


class SimulationError(AureonException):
    """Raised when a simulation operation fails."""


class MLPipelineError(AureonException):
    """Raised when an ML pipeline operation fails."""


def raise_not_found(entity: str, entity_id: str) -> None:
    """Raise a 404 HTTP exception."""
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"{entity} with id '{entity_id}' not found",
    )
