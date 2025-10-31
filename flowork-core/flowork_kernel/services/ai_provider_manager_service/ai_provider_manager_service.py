#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\services\ai_provider_manager_service\ai_provider_manager_service.py JUMLAH BARIS 484 
#######################################################################

import os
import json
import importlib.util
import subprocess
import sys
import importlib.metadata
import tempfile
import zipfile
import shutil
import traceback
import time
import hashlib
from ..base_service import BaseService
from flowork_kernel.utils.file_helper import sanitize_filename
try:
    import torch
    from diffusers import StableDiffusionXLPipeline, AutoencoderKL
    DIFFUSERS_AVAILABLE = True
except ImportError:
    DIFFUSERS_AVAILABLE = False
try:
    importlib.metadata.version("llama-cpp-python")
    LLAMA_CPP_AVAILABLE = True
except importlib.metadata.PackageNotFoundError:
    LLAMA_CPP_AVAILABLE = False
class AIProviderManagerService(BaseService):
    def __init__(self, kernel, service_id: str):
        super().__init__(kernel, service_id)
        self.providers_path = self.kernel.ai_providers_path
        os.makedirs(self.providers_path, exist_ok=True)
        self.loaded_providers = {}
        self.local_models = {}
        self.hf_pipelines = {}
        self.image_output_dir = os.path.join(
            self.kernel.data_path, "generated_images_by_service"
        )
        os.makedirs(self.image_output_dir, exist_ok=True)
        self.discover_and_load_endpoints()
    def discover_and_load_endpoints(self):
        self.kernel.write_to_log("--- PERFORMING AI ENDPOINT DISCOVERY ---", "WARN")
        self.loaded_providers.clear()
        self.local_models.clear()
        self.hf_pipelines.clear()
        self.kernel.write_to_log(
            f"Scanning for AI Providers in: {self.providers_path}", "DEBUG"
        )
        if self.providers_path not in sys.path:
            sys.path.insert(0, self.providers_path)
        for root, dirs, files in os.walk(self.providers_path):
            if "manifest.json" in files:
                provider_dir = root
                provider_id = os.path.basename(provider_dir)
                category_name = os.path.basename(os.path.dirname(provider_dir))
                if provider_dir == self.providers_path or "__pycache__" in provider_dir:
                    continue
                try:
                    manifest_path = os.path.join(provider_dir, "manifest.json")
                    with open(manifest_path, "r", encoding="utf-8") as f:
                        manifest = json.load(f)
                    provider_name = manifest.get("name", provider_id)
                    entry_point = manifest.get("entry_point")
                    if not entry_point or "." not in entry_point:
                        continue
                    vendor_path = os.path.join(provider_dir, "vendor")
                    is_path_added = False
                    if os.path.isdir(vendor_path):
                        sys.path.insert(0, vendor_path)
                        is_path_added = True
                    try:
                        module_filename, class_name = entry_point.split(".")
                        module_path = os.path.join(
                            provider_dir, f"{module_filename}.py"
                        )
                        if not os.path.exists(module_path):
                            continue
                        full_module_name = f"ai_providers.{category_name}.{provider_id}.{module_filename}"
                        spec = importlib.util.spec_from_file_location(
                            full_module_name, module_path
                        )
                        module_lib = importlib.util.module_from_spec(spec)
                        sys.modules[full_module_name] = module_lib
                        spec.loader.exec_module(module_lib)
                        ProviderClass = getattr(module_lib, class_name)
                        self.loaded_providers[provider_id] = ProviderClass(
                            self.kernel, manifest
                        )
                        self.kernel.write_to_log(
                            f"  -> AI Provider '{provider_name}' loaded.", "SUCCESS"
                        )
                    finally:
                        if is_path_added:
                            try:
                                sys.path.remove(vendor_path)
                            except ValueError:
                                pass
                except Exception as e:
                    self.kernel.write_to_log(
                        f"  -> CRITICAL FAILURE loading provider '{provider_id}'. Error: {e}",
                        "ERROR",
                    )
        ai_models_base_path = os.path.join(self.kernel.project_root_path, "ai_models")
        self.kernel.write_to_log(
            f"Recursively scanning for Local AI Models in: {ai_models_base_path}",
            "DEBUG",
        )
        if os.path.isdir(ai_models_base_path):
            for root, dirs, files in os.walk(ai_models_base_path):
                relative_path = os.path.relpath(root, ai_models_base_path)
                path_parts = relative_path.split(os.sep)
                category = (
                    path_parts[0] if path_parts and path_parts[0] != "." else None
                )
                if not category:
                    continue
                for filename in files:
                    if filename.lower().endswith(".gguf"):
                        item_path = os.path.join(root, filename)
                        item_name = os.path.splitext(filename)[0]
                        model_id = f"(Local Model) {item_name}"
                        self.local_models[model_id] = {
                            "full_path": item_path,
                            "type": "gguf",
                            "name": item_name,
                            "category": category,
                        }
                        self.logger(
                            f"  -> Found GGUF model '{item_name}' in category '{category}'",
                            "INFO",
                        )
                for dirname in list(dirs):
                    dir_path = os.path.join(root, dirname)
                    try:
                        dir_content = os.listdir(dir_path)
                        is_text_model = (
                            "config.json" in dir_content
                            and "tokenizer.json" in dir_content
                            and category == "text"
                        )
                        is_image_model = (
                            any(f.lower().endswith(".safetensors") for f in dir_content)
                            and category == "image"
                        )
                        if is_text_model:
                            model_id = f"(Local Model) {dirname}"
                            self.local_models[model_id] = {
                                "full_path": dir_path,
                                "type": "hf_text_folder",
                                "name": dirname,
                                "category": category,
                            }
                            self.logger(
                                f"  -> Found HF Text model '{dirname}' in category '{category}'",
                                "INFO",
                            )
                            dirs.remove(dirname)  # Hentikan os.walk masuk lebih dalam
                        elif is_image_model:
                            model_id = f"(Local Model) {dirname}"
                            self.local_models[model_id] = {
                                "full_path": dir_path,
                                "type": "hf_image_single_file",
                                "name": dirname,
                                "category": category,
                            }
                            self.logger(
                                f"  -> Found HF Image model '{dirname}' in category '{category}'",
                                "INFO",
                            )
                            dirs.remove(dirname)
                    except OSError:
                        continue
        self.kernel.write_to_log(f"--- AI ENDPOINT DISCOVERY FINISHED ---", "WARN")
        self.kernel.write_to_log(
            f"Total endpoints available: {len(self.loaded_providers) + len(self.local_models)}",
            "SUCCESS",
        )
    def _calculate_requirements_hash(self, file_path):
        sha256_hash = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except IOError:
            return None
    def get_provider(self, provider_id: str):
        return self.loaded_providers.get(provider_id)
    def get_available_providers(self) -> dict:
        provider_names = {}
        for provider_id, provider_instance in self.loaded_providers.items():
            provider_names[provider_id] = provider_instance.get_provider_name()
        for model_id, model_data in self.local_models.items():
            display_name = (
                f"{model_data.get('name')} ({model_data.get('type', 'local').upper()})"
            )
            provider_names[model_id] = display_name
        return provider_names
    def get_loaded_providers_info(self) -> list:
        providers_info = []
        for provider_id, provider_instance in self.loaded_providers.items():
            manifest = (
                provider_instance.get_manifest()
                if hasattr(provider_instance, "get_manifest")
                else {}
            )
            providers_info.append(
                {
                    "id": provider_id,
                    "name": manifest.get("name", provider_id),
                    "version": manifest.get("version", "N/A"),
                    "tier": getattr(provider_instance, "TIER", "free").lower(),
                }
            )
        return sorted(providers_info, key=lambda x: x["name"])
    def query_ai_by_task(
        self, task_type: str, prompt: str, endpoint_id: str = None, **kwargs
    ) -> dict:
        if endpoint_id:
            target_endpoint_id = endpoint_id
            self.kernel.write_to_log(
                f"AI Query by Task: Using specified endpoint '{target_endpoint_id}' for task '{task_type}'",
                "DEBUG",
            )
        else:
            setting_key = f"ai_model_for_{task_type}"
            target_endpoint_id = self.loc.get_setting(
                setting_key
            ) or self.loc.get_setting("ai_model_for_other")
            self.kernel.write_to_log(
                f"AI Query by Task: Using default endpoint '{target_endpoint_id}' for task '{task_type}'",
                "DEBUG",
            )
        if not target_endpoint_id:
            return {
                "error": f"No default or specified AI model is configured for task type '{task_type}'."
            }
        if target_endpoint_id in self.loaded_providers:
            provider = self.get_provider(target_endpoint_id)
            if provider:
                is_ready, msg = provider.is_ready()
                if is_ready:
                    return provider.generate_response(prompt, **kwargs)
                else:
                    return {
                        "error": f"Provider '{target_endpoint_id}' for task '{task_type}' is not ready: {msg}"
                    }
            else:
                return {
                    "error": f"Provider '{target_endpoint_id}' not found although it is in loaded_providers list."
                }
        elif target_endpoint_id.startswith("(Local Model)"):
            model_info = self.local_models.get(target_endpoint_id)
            if not model_info:
                return {
                    "error": f"Local model '{target_endpoint_id}' not found in the manager's index."
                }
            model_type = model_info.get("type")
            if model_type == "gguf":
                if not LLAMA_CPP_AVAILABLE:
                    return {
                        "error": "Library 'llama-cpp-python' is required to use local GGUF models."
                    }
                model_full_path = model_info.get("full_path")
                if not model_full_path or not os.path.exists(model_full_path):
                    return {
                        "error": f"Local model file not found at path: {model_full_path}"
                    }
                try:
                    worker_path = os.path.join(
                        self.kernel.project_root_path,
                        "flowork_kernel",
                        "workers",
                        "ai_worker.py",
                    )
                    gpu_layers_setting = self.loc.get_setting("ai_gpu_layers", 40)
                    command = [
                        sys.executable,
                        worker_path,
                        model_full_path,
                        str(gpu_layers_setting),
                    ]
                    self.kernel.write_to_log(
                        f"Delegating GGUF task to isolated AI worker for model '{os.path.basename(model_full_path)}'...",
                        "INFO",
                    )
                    timeout_seconds = self.loc.get_setting(
                        "ai_worker_timeout_seconds", 300
                    )
                    process = subprocess.run(
                        command,
                        input=prompt,
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        timeout=timeout_seconds,
                    )
                    if process.returncode == 0:
                        return {"type": "text", "data": process.stdout}
                    else:
                        return {
                            "type": "text",
                            "data": f"ERROR: AI Worker process failed: {process.stderr}",
                        }
                except Exception as e:
                    self.kernel.write_to_log(
                        f"Error calling local GGUF worker: {e}", "CRITICAL"
                    )
                    return {"error": str(e)}
            elif model_type == "hf_image_single_file":
                return self._run_single_file_image_model(model_info, prompt, **kwargs)
            else:
                return {
                    "error": f"Unsupported local model type '{model_type}' for endpoint '{target_endpoint_id}'."
                }
        else:
            return {
                "error": f"Unsupported or unknown AI endpoint type for task '{task_type}': {target_endpoint_id}"
            }
    def _run_single_file_image_model(self, model_info, prompt, **kwargs):
        if not DIFFUSERS_AVAILABLE:
            return {"error": "Libraries 'diffusers', 'torch', 'Pillow' are required."}
        model_folder_name = model_info.get("name")
        try:
            pipeline = self.hf_pipelines.get(model_folder_name)
            if not pipeline:
                self.kernel.write_to_log(
                    f"Loading HF pipeline for '{model_folder_name}' for the first time...",
                    "INFO",
                )
                model_path = model_info.get("full_path")
                device = "cuda" if torch.cuda.is_available() else "cpu"
                torch_dtype = torch.float16 if device == "cuda" else torch.float32
                vae_path = os.path.join(
                    self.kernel.project_root_path,
                    "ai_models",
                    "vae",
                    "sdxl-vae-fp16-fix",
                )
                if not os.path.isdir(vae_path):
                    raise FileNotFoundError(
                        "VAE folder 'sdxl-vae-fp16-fix' not found in 'ai_models/vae'. This is crucial for quality."
                    )
                vae = AutoencoderKL.from_pretrained(
                    vae_path, torch_dtype=torch_dtype
                ).to(device)
                safetensor_files = [
                    f for f in os.listdir(model_path) if f.endswith(".safetensors")
                ]
                if not safetensor_files:
                    raise FileNotFoundError(
                        f"No .safetensors file found in '{model_path}'"
                    )
                full_model_path = os.path.join(model_path, safetensor_files[0])
                pipeline = StableDiffusionXLPipeline.from_single_file(
                    full_model_path,
                    vae=vae,
                    torch_dtype=torch_dtype,
                    variant="fp16" if device == "cuda" else "fp32",
                ).to(device)
                if device == "cuda":
                    pipeline.enable_model_cpu_offload()
                self.hf_pipelines[model_folder_name] = pipeline
            self.kernel.write_to_log(
                f"Generating image with '{model_folder_name}'...", "INFO"
            )
            generation_params = {
                "prompt": prompt,
                "negative_prompt": kwargs.get(
                    "negative_prompt", "blurry, worst quality, low quality"
                ),
                "width": int(kwargs.get("width", 1024)),
                "height": int(kwargs.get("height", 1024)),
                "guidance_scale": float(kwargs.get("guidance_scale", 7.5)),
                "num_inference_steps": int(kwargs.get("num_inference_steps", 30)),
            }
            image = pipeline(**generation_params).images[0]
            sanitized_prefix = sanitize_filename(prompt[:25])
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"{sanitized_prefix}_{timestamp}.png"
            output_path = os.path.join(self.image_output_dir, filename)
            image.save(output_path)
            self.kernel.write_to_log(f"Image saved to: {output_path}", "SUCCESS")
            return {"type": "image", "data": output_path}
        except Exception as e:
            self.kernel.write_to_log(
                f"Error during local image generation: {e}\n{traceback.format_exc()}",
                "CRITICAL",
            )
            return {"error": str(e)}
    def get_default_provider(self):
        loc = self.kernel.get_service("localization_manager")
        if loc:
            saved_provider_id = loc.get_setting("ai_center_master_provider")
            if saved_provider_id and saved_provider_id in self.loaded_providers:
                return self.loaded_providers[saved_provider_id]
        if self.loaded_providers:
            first_provider_key = next(iter(self.loaded_providers))
            first_provider = self.loaded_providers[first_provider_key]
            self.kernel.write_to_log(
                f"AI Manager: No master provider set. Falling back to first available: {first_provider.get_provider_name()}",
                "WARN",
            )
            return first_provider
        return None
    def install_component(self, zip_filepath: str) -> (bool, str):
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                with zipfile.ZipFile(zip_filepath, "r") as zip_ref:
                    zip_ref.extractall(temp_dir)
                component_root_path = None
                if os.path.exists(os.path.join(temp_dir, "manifest.json")):
                    component_root_path = temp_dir
                else:
                    dir_items = [
                        d
                        for d in os.listdir(temp_dir)
                        if os.path.isdir(os.path.join(temp_dir, d))
                    ]
                    if len(dir_items) == 1:
                        potential_path = os.path.join(temp_dir, dir_items[0])
                        if os.path.exists(
                            os.path.join(potential_path, "manifest.json")
                        ):
                            component_root_path = potential_path
                if not component_root_path:
                    return (
                        False,
                        "manifest.json not found in the root of the zip archive or in a single subdirectory.",
                    )
                with open(
                    os.path.join(component_root_path, "manifest.json"),
                    "r",
                    encoding="utf-8",
                ) as f:
                    manifest = json.load(f)
                required_tier = manifest.get("tier", "free")
                if not self.kernel.is_tier_sufficient(required_tier):
                    error_msg = f"Installation failed. This AI Provider requires a '{required_tier.capitalize()}' license."
                    return False, error_msg
                component_id = manifest.get("id")
                if not component_id:
                    return False, "Component 'id' is missing from manifest.json."
                component_category = manifest.get("category", "specialized")
                category_path = os.path.join(self.providers_path, component_category)
                os.makedirs(category_path, exist_ok=True)
                final_path = os.path.join(category_path, component_id)
                if os.path.exists(final_path):
                    return False, f"AI Provider '{component_id}' is already installed."
                shutil.move(component_root_path, final_path)
                return (
                    True,
                    f"AI Provider '{manifest.get('name', component_id)}' installed successfully.",
                )
            except Exception as e:
                return False, f"An error occurred during AI Provider installation: {e}"
    def _find_component_path(self, component_id: str) -> str | None:
        for category_name in os.listdir(self.providers_path):
            category_path = os.path.join(self.providers_path, category_name)
            if os.path.isdir(category_path):
                potential_path = os.path.join(category_path, component_id)
                if os.path.isdir(potential_path):
                    return potential_path
        return None
    def uninstall_component(self, component_id: str) -> (bool, str):
        component_path = self._find_component_path(component_id)
        if not component_path:
            return (
                False,
                f"Path for AI Provider '{component_id}' not found in any category.",
            )
        try:
            shutil.rmtree(component_path)
            if component_id in self.loaded_providers:
                del self.loaded_providers[component_id]
            return True, f"AI Provider '{component_id}' uninstalled successfully."
        except Exception as e:
            return False, f"Could not delete AI Provider folder: {e}"
