#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\modules\stable_diffusion_xl_module\processor.py JUMLAH BARIS 120 
#######################################################################

from flowork_kernel.core import build_security
import os
import time
from flowork_kernel.api_contract import (
    BaseModule,
    IExecutable,
    IDataPreviewer,
)
from flowork_kernel.utils.payload_helper import get_nested_value
from flowork_kernel.utils.file_helper import sanitize_filename
from flowork_kernel.api_client import ApiClient
import shutil
class StableDiffusionXLModule(BaseModule, IExecutable, IDataPreviewer):
    """
    (REMASTERED V4 - Final) Acts as a smart manager that gathers all necessary parameters
    and delegates the image generation task to the central AIProviderManagerService,
    ensuring consistent, high-quality results.
    """
    TIER = "pro"
    def __init__(self, module_id, services):
        super().__init__(module_id, services)
        self.output_dir = os.path.join(self.kernel.data_path, "generated_images")
        os.makedirs(self.output_dir, exist_ok=True)
        self.ai_manager = self.kernel.get_service("ai_provider_manager_service")
    def _create_error_payload(self, payload, error_message):
        self.logger(error_message, "ERROR")
        if "data" not in payload or not isinstance(payload["data"], dict):
            payload["data"] = {}
        payload["data"]["error"] = error_message
        return {"payload": payload, "output_name": "error"}
    def execute(
        self, payload: dict, config: dict, status_updater, mode="EXECUTE", **kwargs
    ):  # ADD CODE
        model_folder_name = config.get("model_folder")
        endpoint_id = f"(Local Model) {model_folder_name}"
        prompt = (
            get_nested_value(payload, config.get("prompt_source_variable"))
            or get_nested_value(payload, "data.prompt")
            or config.get("prompt")
        )
        if not prompt:
            return self._create_error_payload(
                payload,
                "A prompt is required, either from a payload variable or manual input.",
            )  # English Hardcode
        generation_params = {
            "negative_prompt": config.get("negative_prompt", ""),
            "width": config.get("width", 1024),
            "height": config.get("height", 1024),
            "guidance_scale": config.get("guidance_scale", 7.5),
            "num_inference_steps": config.get("num_inference_steps", 30),
        }
        filename_prefix = config.get("output_filename_prefix", "")
        user_output_folder = config.get("output_folder", "").strip()
        save_dir = (
            user_output_folder
            if user_output_folder and os.path.isdir(user_output_folder)
            else self.output_dir
        )
        try:
            if not self.ai_manager:
                return self._create_error_payload(
                    payload, "AIProviderManagerService is not available."
                )  # English Hardcode
            status_updater(
                f"Delegating generation to {model_folder_name}...", "INFO"
            )  # English Log
            response = self.ai_manager.query_ai_by_task(
                "image", prompt, endpoint_id=endpoint_id, **generation_params
            )
            if "error" in response:
                return self._create_error_payload(payload, response["error"])
            image_path_from_service = response.get("data")
            if not image_path_from_service or not os.path.exists(
                image_path_from_service
            ):
                return self._create_error_payload(
                    payload, "AI Manager service did not return a valid image path."
                )  # English Hardcode
            sanitized_prefix = sanitize_filename(filename_prefix) or sanitize_filename(
                prompt[:20]
            )
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            final_filename = f"{sanitized_prefix}_{timestamp}.png"
            final_output_path = os.path.join(save_dir, final_filename)
            shutil.move(image_path_from_service, final_output_path)
            self.logger(
                f"Image moved to final destination: {final_output_path}", "INFO"
            )  # English Log
            status_updater("Image generated successfully!", "SUCCESS")  # English Log
            if "data" not in payload or not isinstance(payload["data"], dict):
                payload["data"] = {}
            payload["data"]["image_path"] = final_output_path
            return {"payload": payload, "output_name": "success"}
        except Exception as e:
            return self._create_error_payload(
                payload, f"An error occurred during image generation: {e}"
            )  # English Hardcode
    def get_dynamic_output_schema(self, config):
        return [
            {
                "name": "data.image_path",
                "type": "string",
                "description": "The full local path to the generated image file.",
            }
        ]  # English Hardcode
    def get_data_preview(self, config: dict):
        return [
            {
                "status": "preview_not_available",
                "reason": "Image generation is a heavy process.",
            }
        ]  # English Hardcode
