#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\exceptions.py JUMLAH BARIS 37 
#######################################################################

"""
Central repository for all custom Flowork exceptions.
This allows for specific error handling and clearer debugging.
"""
class FloworkException(Exception):
    """Base exception for all custom errors in the application."""
    pass
class PresetNotFoundError(FloworkException):
    """Raised when a specified workflow preset cannot be found."""
    pass
class ModuleValidationError(FloworkException):
    """Raised when a module's property validation fails."""
    pass
class ApiKeyMissingError(FloworkException):
    """Raised when a required API key is not found in the Variable Manager."""
    pass
class DependencyError(FloworkException):
    """Raised when installing a module's requirements.txt fails."""
    pass
class SignatureVerificationError(FloworkException):
    """Raised when a digital signature from an online resource is invalid."""
    pass
class MandatoryUpdateRequiredError(FloworkException):
    """Raised by the StartupService when a mandatory update is detected."""
    def __init__(self, message, update_info=None):
        super().__init__(message)
        self.update_info = update_info or {}
class PermissionDeniedError(FloworkException):
    """Raised when an action is attempted without the required license tier or permission."""
    pass
