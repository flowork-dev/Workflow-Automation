#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\core\permission_hook.py JUMLAH BARIS 48 
#######################################################################

import sys
from flowork_kernel.kernel import Kernel
from flowork_kernel.exceptions import PermissionDeniedError
_kernel_instance = None
def get_kernel():
    global _kernel_instance
    if _kernel_instance is None:
        _kernel_instance = Kernel.instance
    return _kernel_instance
class PermissionHook:
    """
    (REMASTERED - OPEN CORE) A Python Import Hook.
    In Open Core mode, this hook is effectively disabled and does nothing.
    """
    PROTECTED_MODULES = {
        "selenium": "web_scraping_advanced",
        "webdriver_manager": "web_scraping_advanced",
        "torch": "ai_local_models",
        "diffusers": "ai_local_models",
        "transformers": "ai_local_models",
        "llama_cpp": "ai_local_models",
        "moviepy": "video_processing",
    }
    def __init__(self):
        self._active = False # Tetap nonaktif secara default
        kernel = get_kernel()
        if kernel:
            event_bus = kernel.get_service("event_bus", is_system_call=True)
            if event_bus:
                event_bus.subscribe("event_all_services_started", "PermissionHookActivator", self.activate)
    def activate(self, event_data=None):
        """Activates the hook (log message only in Open Core)."""
        kernel = get_kernel()
        if kernel:
            kernel.write_to_log("PermissionHook: Activated (Open Core Mode - Checks Disabled).", "INFO") # English Hardcode
        self._active = True # Tandai aktif meskipun tidak melakukan apa-apa
    def find_spec(self, fullname, path, target=None):
        """
        (MODIFIED - OPEN CORE) Always returns None, effectively disabling the import check.
        """
        return None
