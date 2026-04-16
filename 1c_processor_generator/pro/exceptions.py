"""
Custom exceptions for PRO module licensing.
"""


class LicenseError(Exception):
    """Base exception for license-related errors."""

    def __init__(self, message: str, error_code: str = None):
        super().__init__(message)
        self.error_code = error_code


class ActivationError(LicenseError):
    """Raised when license activation fails."""

    pass


class VerificationError(LicenseError):
    """Raised when license verification fails."""

    pass


class MachineIdError(LicenseError):
    """Raised when machine ID generation fails."""

    pass


class TokenExpiredError(LicenseError):
    """Raised when JWT token has expired."""

    pass


class GracePeriodExpiredError(LicenseError):
    """Raised when offline grace period has expired."""

    pass


class MachineMismatchError(LicenseError):
    """Raised when machine ID doesn't match the license."""

    pass


class NetworkError(LicenseError):
    """Raised when license server is unreachable."""

    pass
