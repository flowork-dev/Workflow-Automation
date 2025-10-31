#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\ai_providers\BaseAIProvider.py JUMLAH BARIS 42 
#######################################################################

from abc import ABC, abstractmethod
class BaseAIProvider(ABC):
    """
    The abstract base class (contract) that all AI Providers must implement.
    [UPGRADED] Now holds its own manifest data.
    [UPGRADED V2] Now includes a standard readiness check method.
    """
    def __init__(self, kernel, manifest: dict):
        self.kernel = kernel
        self.loc = self.kernel.get_service("localization_manager")
        self.manifest = manifest
    @abstractmethod
    def get_provider_name(self) -> str:
        """
        Returns the display name of the provider.
        """
        raise NotImplementedError
    @abstractmethod
    def generate_response(self, prompt: str) -> dict:
        """
        Processes a prompt and returns a standardized dictionary.
        """
        raise NotImplementedError
    @abstractmethod
    def is_ready(self) -> tuple[bool, str]:
        """
        Checks if the provider is properly configured and ready to accept requests.
        Returns a tuple of (is_ready: bool, message: str).
        """
        raise NotImplementedError
    def get_manifest(self) -> dict:
        """
        Returns the manifest data for this provider.
        """
        return self.manifest
