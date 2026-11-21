"""ViewStorm Domain Exceptions and Error Handlers."""

from typing import Any, Dict, Optional
from fastapi import Request, status
from fastapi.responses import JSONResponse


class ViewStormException(Exception):
    """Base exception for all ViewStorm domain errors."""
    def __init__(self, message: str, status_code: int = status.HTTP_400_BAD_REQUEST, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class SimulationNotFoundError(ViewStormException):
    """Raised when a requested simulation run is not found."""
    def __init__(self, run_id: str):
        super().__init__(
            message=f"Simulation run '{run_id}' not found.",
            status_code=status.HTTP_404_NOT_FOUND,
            details={"run_id": run_id}
        )


class SimulationNotActiveError(ViewStormException):
    """Raised when an action requires a running simulation but it is inactive."""
    def __init__(self, run_id: str, current_status: str):
        super().__init__(
            message=f"Simulation run '{run_id}' is not active (current status: '{current_status}'). Events can only be submitted to running simulations.",
            status_code=status.HTTP_409_CONFLICT,
            details={"run_id": run_id, "status": current_status}
        )


class SimulationInvalidStateTransitionError(ViewStormException):
    """Raised when an invalid state transition is requested."""
    def __init__(self, run_id: str, current_status: str, target_status: str):
        super().__init__(
            message=f"Cannot transition simulation '{run_id}' from '{current_status}' to '{target_status}'.",
            status_code=status.HTTP_400_BAD_REQUEST,
            details={"run_id": run_id, "current_status": current_status, "target_status": target_status}
        )


class UnauthorizedTargetError(ViewStormException):
    """Raised when an unauthorized target environment is requested."""
    def __init__(self, target: str, allowed: list):
        super().__init__(
            message=f"Target environment '{target}' is not permitted. Authorized targets are: {allowed}.",
            status_code=status.HTTP_403_FORBIDDEN,
            details={"target": target, "allowed": allowed}
        )


class ExceededUserLimitError(ViewStormException):
    """Raised when requested virtual users exceed allowed threshold."""
    def __init__(self, requested: int, maximum: int):
        super().__init__(
            message=f"Requested virtual users ({requested}) exceeds maximum permitted for this environment ({maximum}).",
            status_code=status.HTTP_400_BAD_REQUEST,
            details={"requested": requested, "maximum": maximum}
        )


async def viewstorm_exception_handler(request: Request, exc: ViewStormException) -> JSONResponse:
    """Handle custom ViewStorm domain exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "type": exc.__class__.__name__,
                "message": exc.message,
                "details": exc.details,
                "path": str(request.url.path),
            }
        }
    )
