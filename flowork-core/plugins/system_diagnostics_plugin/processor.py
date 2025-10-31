#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\plugins\system_diagnostics_plugin\processor.py JUMLAH BARIS 19 
#######################################################################

from flowork_kernel.api_contract import BaseModule #, BaseUIProvider
class SystemDiagnosticsPlugin(BaseModule): # [REFACTORY] Removed BaseUIProvider inheritance
    """
    A lightweight UI provider plugin. Its sole responsibility is to register the
    Diagnostics Page with the main UI and act as a bridge to the DiagnosticsService.
    All core scanning logic resides in the DiagnosticsService.
    """
    def __init__(self, module_id, services):
        super().__init__(module_id, services)
        self.diagnostics_service = self.kernel.get_service("diagnostics_service")
    def execute(self, payload, config, status_updater, mode='EXECUTE', **kwargs):
        return payload
