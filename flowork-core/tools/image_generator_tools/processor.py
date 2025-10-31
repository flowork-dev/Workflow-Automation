#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\tools\image_generator_tools\processor.py JUMLAH BARIS 57 
#######################################################################

from flowork_kernel.api_contract import BaseModule, IExecutable, IConfigurableUI, IDataPreviewer
from flowork_kernel.utils.payload_helper import get_nested_value
class ImageGeneratorModule(BaseModule, IExecutable, IConfigurableUI, IDataPreviewer):
    """
    (REMASTERED V3) A tool to generate an image. It now simply delegates the task to the
    globally configured AI model for image generation via the smart AIProviderManager.
    """
    TIER = "pro"
    def __init__(self, module_id, services):
        super().__init__(module_id, services)
    def execute(self, payload: dict, config: dict, status_updater, mode='EXECUTE', **kwargs): # ADD CODE
        prompt_variable = config.get('prompt_source_variable', 'data.prompt_gambar')
        prompt_text = get_nested_value(payload, prompt_variable)
        if not prompt_text or not isinstance(prompt_text, str):
             prompt_text = get_nested_value(payload, 'data.prompt')
        if not prompt_text or not isinstance(prompt_text, str):
            return {"payload": {"data": {"error": f"Could not find a valid text prompt in payload. Checked '{prompt_variable}' and 'data.prompt'."}}, "output_name": "error"}
        status_updater("Sending image generation task to Kernel...", "INFO") # English Log
        self.logger(f"ImageGenerator: Delegating image generation task for prompt: '{prompt_text[:50]}...'", "INFO") # English Log
        ai_manager = self.kernel.get_service("ai_provider_manager_service")
        if not ai_manager:
            return {"payload": {"data": {"error": "AIProviderManagerService is not available."}}, "output_name": "error"}
        try:
            response = ai_manager.query_ai_by_task('image', prompt_text)
            if "error" in response:
                raise Exception(response["error"]) # This will be caught by the generic except block
            image_path = response.get('data')
            if not image_path:
                raise Exception("The AI did not return a valid image path.") # This will be caught
            if 'data' not in payload or not isinstance(payload['data'], dict):
                payload['data'] = {}
            payload['data']['generated_image_path'] = image_path
            status_updater("Image generated successfully.", "SUCCESS")
            return {"payload": payload, "output_name": "success"}
        except Exception as e:
            error_msg = f"Failed to generate image: {e}"
            self.logger(error_msg, "ERROR") # English Log
            if 'data' not in payload: payload['data'] = {}
            payload['data']['error'] = error_msg
            return {"payload": payload, "output_name": "error"}
    def create_properties_ui(self, parent_frame, get_current_config, available_vars):
        pass
    def get_dynamic_output_schema(self, config):
        return [{
            "name": "data.generated_image_path",
            "type": "string",
            "description": "The full local path to the generated image file."
        }]
    def get_data_preview(self, config: dict):
        return [{'status': 'preview_not_available', 'reason': 'AI image generation is a live process.'}]
