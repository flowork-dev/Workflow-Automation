#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\tools\prompt_template_plugin\processor.py JUMLAH BARIS 41 
#######################################################################

from flowork_kernel.api_contract import BaseModule, IExecutable, IConfigurableUI, IDataPreviewer
from flowork_kernel.api_client import ApiClient
class PromptTemplateModule(BaseModule, IExecutable, IConfigurableUI, IDataPreviewer):
    """
    (REMASTERED V2) This module now fetches a list of pre-saved templates
    from the PromptManagerService and allows the user to select one via a dropdown.
    """
    TIER = "free"
    def __init__(self, module_id, services):
        super().__init__(module_id, services)
        self.prompt_manager = services.get("prompt_manager_service")
    def execute(self, payload: dict, config: dict, status_updater, mode='EXECUTE', **kwargs): # ADD CODE
        selected_prompt_id = config.get('selected_prompt_id')
        if not selected_prompt_id:
            return {"payload": {"data": {"error": "No prompt template has been selected in the node properties."}}, "output_name": "error"}
        if not self.prompt_manager:
            raise RuntimeError("PromptManagerService is not available.")
        status_updater(f"Fetching prompt template (ID: {selected_prompt_id[:8]}...)", "INFO")
        prompt_data = self.prompt_manager.get_prompt(selected_prompt_id)
        if not prompt_data or 'content' not in prompt_data:
            return {"payload": {"data": {"error": f"Could not find or load the prompt template with ID: {selected_prompt_id}"}}, "output_name": "error"}
        template_content = prompt_data['content']
        if 'data' not in payload or not isinstance(payload['data'], dict):
            payload['data'] = {}
        payload['data']['prompt_template'] = template_content
        status_updater("Prompt template loaded successfully.", "SUCCESS")
        return {"payload": payload, "output_name": "success"}
    def create_properties_ui(self, parent_frame, get_current_config, available_vars):
        pass
    def get_data_preview(self, config: dict):
        selected_id = config.get('selected_prompt_id')
        if not selected_id:
            return [{'status': 'No prompt selected.'}]
        return [{'status': f"Will load the content of prompt template with ID: {selected_id[:8]}..."}]
