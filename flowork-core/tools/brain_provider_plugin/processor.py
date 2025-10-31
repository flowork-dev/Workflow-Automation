#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\tools\brain_provider_plugin\processor.py JUMLAH BARIS 33 
#######################################################################

from flowork_kernel.api_contract import BaseBrainProvider, IExecutable, IConfigurableUI, IDataPreviewer
from flowork_kernel.api_client import ApiClient
class BrainProviderPlugin(BaseBrainProvider, IExecutable, IConfigurableUI, IDataPreviewer):
    TIER = "pro"
    """
    A universal AI Brain provider for the Agent Host. It allows selecting any configured
    AI Provider to act as the agent's brain.
    """
    def __init__(self, module_id: str, services: dict):
        super().__init__(module_id, services)
        self.api_client = ApiClient(kernel=self.kernel)
        self.ai_manager = self.kernel.get_service("ai_provider_manager_service")
    def get_provider_name(self) -> str:
        return "AI Brain Provider"
    def is_ready(self) -> tuple[bool, str]:
        return (True, "")
    def think(self, objective: str, tools_string: str, history: list, last_observation: str) -> dict:
        self.logger("The 'think' method on a Brain Provider node should not be called directly.", "WARN")
        return {"error": "This node is a configuration provider for Agent Host and does not execute 'think' logic itself."}
    def execute(self, payload, config, status_updater, mode='EXECUTE', **kwargs): # ADD CODE
        status_updater("Brain Provider ready. Connect to an Agent Host.", "INFO")
        return {"payload": payload, "output_name": "brain_output"}
    def create_properties_ui(self, parent_frame, get_current_config, available_vars):
        pass
    def get_data_preview(self, config: dict):
        return [{'status': 'This is a brain node and has no direct data output to preview.'}]
