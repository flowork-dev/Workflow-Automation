#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\api_client.py JUMLAH BARIS 844 
#######################################################################

import requests
import json
import os
import threading
import time
import random
from flowork_kernel.kernel import Kernel
class ApiClient:
    """
    (REMASTERED) A client to interact with the local and remote Flowork APIs.
    This client is responsible for all internal communications between services and the API server.
    It retrieves the license tier directly from the Kernel's state.
    """
    def __init__(self, base_url="http://localhost:8989/api/v1", kernel=None):
        self.local_base_url = base_url
        self.kernel = kernel or Kernel.instance
        self._loc_cache = None  # ADDED: Cache for the new lazy-loaded property.
        self.cache = {}
        self.cache_lock = threading.Lock()
    @property
    def loc(self):
        """
        Lazy-loads the localization manager service to prevent startup order issues.
        """
        if self._loc_cache is None:
            if self.kernel:
                self._loc_cache = self.kernel.get_service("localization_manager")
        return self._loc_cache
    def _get_variable(self, var_name):
        if self.kernel:
            variable_manager = self.kernel.get_service("variable_manager")
            if variable_manager:
                return variable_manager.get_variable(var_name)
        return None
    def _get_local_auth_headers(self):
        headers = {}
        api_key = self._get_variable("FLOWORK_API_KEY")
        if api_key:
            headers["X-API-Key"] = api_key
        return headers
    def _handle_response(self, response):
        if 200 <= response.status_code < 300:
            if response.status_code == 204 or not response.content:
                return True, {}
            return True, response.json()
        else:
            try:
                error_data = response.json()
                message = (
                    error_data.get("message")
                    or error_data.get("msg")
                    or error_data.get("error_description")
                    or error_data.get("error", "Unknown API error")
                )
            except json.JSONDecodeError:
                message = response.text
            return False, message
    def register_user(self, username, email, password):
        return False, "User registration must be handled by the Gateway."
    def forgot_password(self, email: str):
        return False, "Forgot password must be handled by the Gateway."
    def login_user(self, email, password):
        return False, "User login must be handled by the Gateway."
    def get_user_profile_by_token(self, session_token: str):
        """
        [MODIFIKASI FINAL] Core TIDAK VALIDASI TOKEN. Core hanya mengembalikan
        informasi Tier/Lisensi yang sudah di-cache saat Core berjalan.
        Asumsi: Jika Core dipanggil dengan token, user sudah divalidasi oleh Gateway.
        """
        if not self.kernel.current_user:
            return (
                False,
                "User profile not found in Kernel state. Authentication failed.",
            )
        license_manager = self.kernel.get_service("license_manager_service")
        user_data = self.kernel.current_user.copy()  # Gunakan copy agar aman
        user_data["message"] = "Profile check successful (internal cache)."
        user_data["tier"] = self.kernel.license_tier  # Ambil dari Kernel
        user_data["license_expires_at"] = (
            license_manager.license_data.get("expiry_date")
            if license_manager and license_manager.license_data
            else None
        )
        return True, user_data
    def validate_license_activation(self, license_key: str, machine_id: str):
        self.kernel.write_to_log(
            "External license validation is deprecated. Using local checks.", "WARN"
        )
        return False, "External validation is deprecated. Use local activation file."
    def activate_license(self, license_content: dict):
        self.kernel.write_to_log(
            "External license activation is deprecated. Using local activation file.",
            "WARN",
        )
        return False, "External activation is deprecated. Use local activation file."
    def deactivate_license(self):
        self.kernel.write_to_log("External license deactivation is deprecated.", "WARN")
        return False, "External deactivation is deprecated."
    def restart_application(self):
        try:
            response = requests.post(
                f"{self.local_base_url}/system/actions/restart",
                headers=self._get_local_auth_headers(),
            )
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, f"Connection to API server failed: {e}"
    def get_all_settings(self):
        try:
            response = requests.get(
                f"{self.local_base_url}/settings",
                headers=self._get_local_auth_headers(),
            )
            return self._handle_response(response)
        except requests.exceptions.ConnectionError as e:
            return False, f"Connection to API server failed: {e}"
    def save_settings(self, settings_data: dict):
        try:
            response = requests.patch(
                f"{self.local_base_url}/settings",
                json=settings_data,
                headers=self._get_local_auth_headers(),
            )
            return self._handle_response(response)
        except requests.exceptions.ConnectionError as e:
            return False, f"Connection to API server failed: {e}"
    def list_datasets(self):
        try:
            response = requests.get(
                f"{self.local_base_url}/datasets",
                headers=self._get_local_auth_headers(),
            )
            return self._handle_response(response)
        except requests.exceptions.ConnectionError as e:
            return False, f"Connection to API server failed: {e}"
    def get_dataset_data(self, dataset_name: str):
        try:
            response = requests.get(
                f"{self.local_base_url}/datasets/{dataset_name}/data",
                headers=self._get_local_auth_headers(),
            )
            return self._handle_response(response)
        except requests.exceptions.ConnectionError as e:
            return False, f"Connection to API server failed: {e}"
    def create_dataset(self, name: str):
        try:
            payload = {"name": name}
            response = requests.post(
                f"{self.local_base_url}/datasets",
                json=payload,
                headers=self._get_local_auth_headers(),
            )
            return self._handle_response(response)
        except requests.exceptions.ConnectionError as e:
            return False, f"Connection to API server failed: {e}"
    def add_data_to_dataset(self, dataset_name: str, data_list: list):
        try:
            payload = {"data": data_list}
            response = requests.post(
                f"{self.local_base_url}/datasets/{dataset_name}/data",
                json=payload,
                headers=self._get_local_auth_headers(),
            )
            return self._handle_response(response)
        except requests.exceptions.ConnectionError as e:
            return False, f"Connection to API server failed: {e}"
    def start_training_job(
        self, base_model_id, dataset_name, new_model_name, training_args
    ):
        try:
            payload = {
                "base_model_id": base_model_id,
                "dataset_name": dataset_name,
                "new_model_name": new_model_name,
                "training_args": training_args,
            }
            response = requests.post(
                f"{self.local_base_url}/training/start",
                json=payload,
                headers=self._get_local_auth_headers(),
            )
            return self._handle_response(response)
        except requests.exceptions.ConnectionError as e:
            return False, f"Connection to API server failed: {e}"
    def get_training_job_status(self, job_id: str):
        try:
            response = requests.get(
                f"{self.local_base_url}/training/status/{job_id}",
                headers=self._get_local_auth_headers(),
            )
            return self._handle_response(response)
        except requests.exceptions.ConnectionError as e:
            return False, f"Connection to API server failed: {e}"
    def start_model_conversion(
        self, source_model_folder: str, output_gguf_name: str, quantize_method: str
    ):
        try:
            payload = {
                "source_model_folder": source_model_folder,
                "output_gguf_name": output_gguf_name,
                "quantize_method": quantize_method,
            }
            response = requests.post(
                f"{self.local_base_url}/models/convert",
                json=payload,
                headers=self._get_local_auth_headers(),
            )
            return self._handle_response(response)
        except requests.exceptions.ConnectionError as e:
            return False, f"Connection to API server failed: {e}"
    def start_model_requantize(
        self, source_gguf_path: str, output_gguf_name: str, quantize_method: str
    ):
        try:
            payload = {
                "source_gguf_path": source_gguf_path,
                "output_gguf_name": output_gguf_name,
                "quantize_method": quantize_method,
            }
            response = requests.post(
                f"{self.local_base_url}/models/requantize",
                json=payload,
                headers=self._get_local_auth_headers(),
            )
            return self._handle_response(response)
        except requests.exceptions.ConnectionError as e:
            return False, f"Connection to API server failed: {e}"
    def get_conversion_status(self, job_id: str):
        try:
            response = requests.get(
                f"{self.local_base_url}/models/convert/status/{job_id}",
                headers=self._get_local_auth_headers(),
            )
            return self._handle_response(response)
        except requests.exceptions.ConnectionError as e:
            return False, f"Connection to API server failed: {e}"
    def get_agents(self):
        try:
            response = requests.get(
                f"{self.local_base_url}/agents", headers=self._get_local_auth_headers()
            )
            return self._handle_response(response)
        except requests.exceptions.ConnectionError as e:
            return False, f"Connection to API server failed: {e}"
    def save_agent(self, agent_data: dict):
        try:
            response = requests.post(
                f"{self.local_base_url}/agents",
                json=agent_data,
                headers=self._get_local_auth_headers(),
            )
            return self._handle_response(response)
        except requests.exceptions.ConnectionError as e:
            return False, f"Connection to API server failed: {e}"
    def delete_agent(self, agent_id: str):
        try:
            response = requests.delete(
                f"{self.local_base_url}/agents/{agent_id}",
                headers=self._get_local_auth_headers(),
            )
            return self._handle_response(response)
        except requests.exceptions.ConnectionError as e:
            return False, f"Connection to API server failed: {e}"
    def run_agent(self, agent_id: str, objective: str):
        try:
            payload = {"objective": objective}
            response = requests.post(
                f"{self.local_base_url}/agents/{agent_id}/run",
                json=payload,
                headers=self._get_local_auth_headers(),
            )
            return self._handle_response(response)
        except requests.exceptions.ConnectionError as e:
            return False, f"Connection to API server failed: {e}"
    def get_agent_run_status(self, run_id: str):
        try:
            response = requests.get(
                f"{self.local_base_url}/agents/run/{run_id}",
                headers=self._get_local_auth_headers(),
            )
            return self._handle_response(response)
        except requests.exceptions.ConnectionError as e:
            return False, f"Connection to API server failed: {e}"
    def stop_agent_run(self, run_id: str):
        try:
            response = requests.post(
                f"{self.local_base_url}/agents/run/{run_id}/stop",
                headers=self._get_local_auth_headers(),
            )
            return self._handle_response(response)
        except requests.exceptions.ConnectionError as e:
            return False, f"Connection to API server failed: {e}"
    def trigger_hot_reload(self):
        try:
            payload = {"action": "hot_reload"}
            response = requests.post(
                f"{self.local_base_url}/system/actions/hot_reload",
                json=payload,
                headers=self._get_local_auth_headers(),
            )
            return self._handle_response(response)
        except requests.exceptions.ConnectionError as e:
            return False, f"Connection to API server failed: {e}"
    def get_presets(self):
        try:
            response = requests.get(
                f"{self.local_base_url}/presets", headers=self._get_local_auth_headers()
            )
            return self._handle_response(response)
        except requests.exceptions.ConnectionError as e:
            return False, f"Connection to API server failed: {e}"
    def get_preset_data(self, preset_name):
        try:
            response = requests.get(
                f"{self.local_base_url}/presets/{preset_name}",
                headers=self._get_local_auth_headers(),
            )
            return self._handle_response(response)
        except requests.exceptions.ConnectionError as e:
            return False, f"Connection to API server failed: {e}"
    def save_preset(self, preset_name, workflow_data):
        try:
            payload = {"name": preset_name, "workflow_data": workflow_data}
            response = requests.post(
                f"{self.local_base_url}/presets",
                json=payload,
                headers=self._get_local_auth_headers(),
            )
            return self._handle_response(response)
        except requests.exceptions.ConnectionError as e:
            return False, f"Connection to API server failed: {e}"
    def delete_preset(self, preset_name):
        try:
            response = requests.delete(
                f"{self.local_base_url}/presets/{preset_name}",
                headers=self._get_local_auth_headers(),
            )
            return self._handle_response(response)
        except requests.exceptions.ConnectionError as e:
            return False, f"Connection to API server failed: {e}"
    def get_preset_versions(self, preset_name: str):
        try:
            response = requests.get(
                f"{self.local_base_url}/presets/{preset_name}/versions",
                headers=self._get_local_auth_headers(),
            )
            return self._handle_response(response)
        except requests.exceptions.ConnectionError as e:
            return False, f"Connection to API server failed: {e}"
    def load_preset_version(self, preset_name: str, version_filename: str):
        try:
            response = requests.get(
                f"{self.local_base_url}/presets/{preset_name}/versions/{version_filename}",
                headers=self._get_local_auth_headers(),
            )
            return self._handle_response(response)
        except requests.exceptions.ConnectionError as e:
            return False, f"Connection to API server failed: {e}"
    def delete_preset_version(self, preset_name: str, version_filename: str):
        try:
            response = requests.delete(
                f"{self.local_base_url}/presets/{preset_name}/versions/{version_filename}",
                headers=self._get_local_auth_headers(),
            )
            return self._handle_response(response)
        except requests.exceptions.ConnectionError as e:
            return False, f"Connection to API server failed: {e}"
    def get_variables(self):
        try:
            response = requests.get(
                f"{self.local_base_url}/variables",
                headers=self._get_local_auth_headers(),
            )
            return self._handle_response(response)
        except requests.exceptions.ConnectionError as e:
            return False, f"Connection to API server failed: {e}"
    def update_variable(self, name, value, is_secret, is_enabled=True, mode=None):
        try:
            payload = {"value": value, "is_secret": is_secret, "is_enabled": is_enabled}
            if mode:
                payload["mode"] = mode
            response = requests.put(
                f"{self.local_base_url}/variables/{name}",
                json=payload,
                headers=self._get_local_auth_headers(),
            )
            return self._handle_response(response)
        except requests.exceptions.ConnectionError as e:
            return False, f"Connection to API server failed: {e}"
    def update_variable_state(self, name: str, is_enabled: bool):
        try:
            payload = {"enabled": is_enabled}
            response = requests.patch(
                f"{self.local_base_url}/variables/{name}/state",
                json=payload,
                headers=self._get_local_auth_headers(),
            )
            return self._handle_response(response)
        except requests.exceptions.ConnectionError as e:
            return False, f"Connection to API server failed: {e}"
    def delete_variable(self, name):
        try:
            response = requests.delete(
                f"{self.local_base_url}/variables/{name}",
                headers=self._get_local_auth_headers(),
            )
            return self._handle_response(response)
        except requests.exceptions.ConnectionError as e:
            return False, f"Connection to API server failed: {e}"
    def get_components(self, component_type: str, component_id: str = None):
        try:
            url = f"{self.local_base_url}/{component_type}"
            if component_id:
                url += f"/{component_id}"
            response = requests.get(url, headers=self._get_local_auth_headers())
            return self._handle_response(response)
        except requests.exceptions.ConnectionError as e:
            return False, f"Connection to API server failed: {e}"
    def get_ai_provider_services(self):
        """Fetches ONLY the AI provider services, not local models."""
        try:
            response = requests.get(
                f"{self.local_base_url}/ai_providers/services",
                headers=self._get_local_auth_headers(),
            )
            return self._handle_response(response)
        except requests.exceptions.ConnectionError as e:
            return False, f"Connection to API server failed: {e}"
    def install_component(self, zip_filepath: str):
        try:
            with open(zip_filepath, "rb") as f:
                headers = self._get_local_auth_headers()
                files = {"file": (os.path.basename(zip_filepath), f, "application/zip")}
                response = requests.post(
                    f"{self.local_base_url}/{component_type}/install",
                    files=files,
                    headers=headers,
                )
            return self._handle_response(response)
        except FileNotFoundError:
            return False, f"Local file not found: {zip_filepath}"
        except requests.exceptions.ConnectionError as e:
            return False, f"Connection to API server failed: {e}"
    def delete_component(self, component_type: str, component_id: str):
        try:
            response = requests.delete(
                f"{self.local_base_url}/{component_type}/{component_id}",
                headers=self._get_local_auth_headers(),
            )
            return self._handle_response(response)
        except requests.exceptions.ConnectionError as e:
            return False, f"Connection to API server failed: {e}"
    def update_component_state(
        self, component_type: str, component_id: str, is_paused: bool
    ):
        try:
            payload = {"paused": is_paused}
            response = requests.patch(
                f"{self.local_base_url}/{component_type}/{component_id}",
                json=payload,
                headers=self._get_local_auth_headers(),
            )
            return self._handle_response(response)
        except requests.exceptions.ConnectionError as e:
            return False, f"Connection to API server failed: {e}"
    def get_dashboard_layout(self, tab_id: str):
        """(FIXED) Fetches the dashboard layout for a specific tab via the API."""
        try:
            response = requests.get(
                f"{self.local_base_url}/uistate/dashboards/{tab_id}",
                headers=self._get_local_auth_headers(),
                timeout=3,
            )
            return self._handle_response(response)
        except (
            requests.exceptions.RequestException
        ) as e:  # (MODIFIED) Changed to catch broader RequestException including timeouts.
            error_message = (
                self.loc.get(
                    "api_connection_failed",
                    fallback="Connection to API server failed: {error}",
                    error=e,
                )
                if self.loc
                else f"Connection to API server failed: {e}"
            )
            return False, error_message
    def save_dashboard_layout(self, tab_id: str, layout_data: dict):
        """(FIXED) Saves the dashboard layout for a specific tab via the API."""
        try:
            response = requests.post(
                f"{self.local_base_url}/uistate/dashboards/{tab_id}",
                json=layout_data,
                headers=self._get_local_auth_headers(),
            )
            return self._handle_response(response)
        except requests.exceptions.ConnectionError as e:
            error_message = (
                self.loc.get(
                    "api_connection_failed",
                    fallback="Connection to API server failed: {error}",
                    error=e,
                )
                if self.loc
                else f"Connection to API server failed: {e}"
            )
            return False, error_message
    def get_tab_session(self):
        try:
            response = requests.get(
                f"{self.local_base_url}/uistate/session/tabs",
                headers=self._get_local_auth_headers(),
            )
            return self._handle_response(response)
        except requests.exceptions.ConnectionError as e:
            return False, f"Connection to API server failed: {e}"
    def save_tab_session(self, tabs_data: list):
        try:
            response = requests.post(
                f"{self.local_base_url}/uistate/session/tabs",
                json=tabs_data,
                headers=self._get_local_auth_headers(),
            )
            return self._handle_response(response)
        except requests.exceptions.ConnectionError as e:
            return False, f"Connection to API server failed: {e}"
    def open_managed_tab(self, tab_key: str):
        try:
            payload = {"tab_key": tab_key}
            response = requests.post(
                f"{self.local_base_url}/ui/actions/open_tab",
                json=payload,
                headers=self._get_local_auth_headers(),
            )
            return self._handle_response(response)
        except requests.exceptions.ConnectionError as e:
            return False, f"Connection to API server failed: {e}"
    def upload_component(
        self, comp_type: str, component_id: str, description: str, tier: str
    ):
        try:
            payload = {
                "comp_type": comp_type,
                "component_id": component_id,
                "description": description,
                "tier": tier,
            }
            response = requests.post(
                f"{self.local_base_url}/addons/upload",
                json=payload,
                headers=self._get_local_auth_headers(),
            )
            return self._handle_response(response)
        except requests.exceptions.ConnectionError as e:
            return False, f"Connection to API server failed: {e}"
    def upload_model(self, model_path: str, description: str, tier: str):
        try:
            form_data = {
                "description": description,
                "tier": tier,
                "model_id": os.path.basename(model_path).replace(".gguf", ""),
            }
            with open(model_path, "rb") as f:
                files = {
                    "file": (
                        os.path.basename(model_path),
                        f,
                        "application/octet-stream",
                    )
                }
                response = requests.post(
                    f"{self.local_base_url}/models/upload",
                    data=form_data,
                    files=files,
                    headers=self._get_local_auth_headers(),
                )
            return self._handle_response(response)
        except FileNotFoundError:
            return False, f"Local model file not found: {model_path}"
        except requests.exceptions.ConnectionError as e:
            return False, f"Connection to API server failed: {e}"
    def get_prompts(self):
        try:
            response = requests.get(
                f"{self.local_base_url}/prompts", headers=self._get_local_auth_headers()
            )
            return self._handle_response(response)
        except requests.exceptions.ConnectionError as e:
            return False, f"Connection to API server failed: {e}"
    def get_prompt(self, prompt_id: str):
        try:
            response = requests.get(
                f"{self.local_base_url}/prompts/{prompt_id}",
                headers=self._get_local_auth_headers(),
            )
            return self._handle_response(response)
        except requests.exceptions.ConnectionError as e:
            return False, f"Connection to API server failed: {e}"
    def create_prompt(self, prompt_data: dict):
        try:
            response = requests.post(
                f"{self.local_base_url}/prompts",
                json=prompt_data,
                headers=self._get_local_auth_headers(),
            )
            return self._handle_response(response)
        except requests.exceptions.ConnectionError as e:
            return False, f"Connection to API server failed: {e}"
    def update_prompt(self, prompt_id: str, prompt_data: dict):
        try:
            response = requests.put(
                f"{self.local_base_url}/prompts/{prompt_id}",
                json=prompt_data,
                headers=self._get_local_auth_headers(),
            )
            return self._handle_response(response)
        except requests.exceptions.ConnectionError as e:
            return False, f"Connection to API server failed: {e}"
    def delete_prompt(self, prompt_id: str):
        try:
            response = requests.delete(
                f"{self.local_base_url}/prompts/{prompt_id}",
                headers=self._get_local_auth_headers(),
            )
            return self._handle_response(response)
        except requests.exceptions.ConnectionError as e:
            return False, f"Connection to API server failed: {e}"
    def delete_dataset(self, name: str):
        try:
            response = requests.delete(
                f"{self.local_base_url}/datasets/{name}",
                headers=self._get_local_auth_headers(),
            )
            return self._handle_response(response)
        except requests.exceptions.ConnectionError as e:
            return False, f"Connection to API server failed: {e}"
    def get_trigger_rules(self):
        try:
            response = requests.get(
                f"{self.local_base_url}/triggers/rules",
                headers=self._get_local_auth_headers(),
            )
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, f"Connection to API server failed: {e}"
    def get_trigger_definitions(self):
        try:
            response = requests.get(
                f"{self.local_base_url}/triggers/definitions",
                headers=self._get_local_auth_headers(),
            )
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, f"Connection to API server failed: {e}"
    def create_trigger_rule(self, rule_data: dict):
        try:
            response = requests.post(
                f"{self.local_base_url}/triggers/rules",
                json=rule_data,
                headers=self._get_local_auth_headers(),
            )
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, f"Connection to API server failed: {e}"
    def update_trigger_rule(self, rule_id: str, rule_data: dict):
        try:
            response = requests.put(
                f"{self.local_base_url}/triggers/rules/{rule_id}",
                json=rule_data,
                headers=self._get_local_auth_headers(),
            )
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, f"Connection to API server failed: {e}"
    def delete_trigger_rule(self, rule_id: str):
        try:
            response = requests.delete(
                f"{self.local_base_url}/triggers/rules/{rule_id}",
                headers=self._get_local_auth_headers(),
            )
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, f"Connection to API server failed: {e}"
    def reload_triggers(self):
        try:
            response = requests.post(
                f"{self.local_base_url}/triggers/actions/reload",
                headers=self._get_local_auth_headers(),
            )
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, f"Connection to API server failed: {e}"
    def get_state(self, key: str):
        """Gets a specific key from the state manager via API."""
        try:
            response = requests.get(
                f"{self.local_base_url}/uistate/generic/{key}",
                headers=self._get_local_auth_headers(),
            )
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, f"Connection to API server failed: {e}"
    def set_state(self, key: str, value: any):
        """Sets a specific key in the state manager via API."""
        try:
            response = requests.post(
                f"{self.local_base_url}/uistate/generic/{key}",
                json=value,
                headers=self._get_local_auth_headers(),
            )
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, f"Connection to API server failed: {e}"
    def delete_state(self, key: str):
        """Deletes a specific key from the state manager via API."""
        try:
            response = requests.delete(
                f"{self.local_base_url}/uistate/generic/{key}",
                headers=self._get_local_auth_headers(),
            )
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, f"Connection to API server failed: {e}"
    def get_tab_preset(self, tab_id: str):
        return self.get_state(f"tab_preset_map::{tab_id}")
    def set_tab_preset(self, tab_id: str, preset_name: str):
        return self.set_state(f"tab_preset_map::{tab_id}", preset_name)
    def execute_raw_workflow(
        self, nodes: dict, connections: dict, initial_payload: dict
    ):
        try:
            payload = {
                "nodes": nodes,
                "connections": connections,
                "initial_payload": initial_payload,
            }
            response = requests.post(
                f"{self.local_base_url}/workflow/execute_raw",
                json=payload,
                headers=self._get_local_auth_headers(),
            )
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, f"Connection to API server failed: {e}"
    def stop_workflow(self, job_id: str):
        try:
            response = requests.post(
                f"{self.local_base_url}/workflow/stop/{job_id}",
                headers=self._get_local_auth_headers(),
            )
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, f"Connection to API server failed: {e}"
    def pause_workflow(self, job_id: str):
        try:
            response = requests.post(
                f"{self.local_base_url}/workflow/pause/{job_id}",
                headers=self._get_local_auth_headers(),
            )
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, f"Connection to API server failed: {e}"
    def resume_workflow(self, job_id: str):
        try:
            response = requests.post(
                f"{self.local_base_url}/workflow/resume/{job_id}",
                headers=self._get_local_auth_headers(),
            )
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, f"Connection to API server failed: {e}"
    def send_approval_response(self, module_id: str, result: dict):
        try:
            response = requests.post(
                f"{self.local_base_url}/workflow/approval/{module_id}",
                json=result,
                headers=self._get_local_auth_headers(),
            )
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, f"Connection to API server failed: {e}"
    def validate_node_config(self, module_id: str, config: dict):
        try:
            response = requests.post(
                f"{self.local_base_url}/validation/node_config/{module_id}",
                json=config,
                headers=self._get_local_auth_headers(),
            )
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, f"Connection to API server failed: {e}"
    def logout(self):
        try:
            response = requests.post(
                f"{self.local_base_url}/auth/logout",
                headers=self._get_local_auth_headers(),
            )
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, f"Connection to API server failed: {e}"
    def generate_workflow_from_prompt(self, prompt: str):
        try:
            response = requests.post(
                f"{self.local_base_url}/ai/generate_workflow",
                json={"prompt": prompt},
                headers=self._get_local_auth_headers(),
            )
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, f"Connection to API server failed: {e}"
    def start_recording(self):
        try:
            response = requests.post(
                f"{self.local_base_url}/recorder/start",
                headers=self._get_local_auth_headers(),
            )
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, f"Connection to API server failed: {e}"
    def stop_recording(self):
        try:
            response = requests.post(
                f"{self.local_base_url}/recorder/stop",
                headers=self._get_local_auth_headers(),
            )
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, f"Connection to API server failed: {e}"
    def clear_system_cache(self):
        try:
            response = requests.post(
                f"{self.local_base_url}/system/actions/clear_cache",
                headers=self._get_local_auth_headers(),
            )
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, f"Connection to API server failed: {e}"
