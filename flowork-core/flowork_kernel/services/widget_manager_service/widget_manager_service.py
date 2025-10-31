#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\services\widget_manager_service\widget_manager_service.py JUMLAH BARIS 229 
#######################################################################

import os
import json
import importlib.util
import subprocess
import sys
import importlib.metadata
from ..base_service import BaseService
import zipfile
import tempfile
import shutil
import hashlib
from flowork_kernel.api_contract import BaseDashboardWidget
class WidgetManagerService(BaseService):
    """
    (REMASTERED V10 - Headless) A pure-Python loader for widgets.
    This service exclusively scans the 'widgets' folder within flowork-core
    and does not load any UI code, only manifests.
    """
    def __init__(self, kernel, service_id: str):
        super().__init__(kernel, service_id)
        self.widgets_dir = self.kernel.widgets_path
        self.loaded_widgets = {}
        self.paused_status_file = os.path.join(
            self.kernel.data_path, "paused_widgets.json"
        )
        self.kernel.write_to_log(
            "Service 'WidgetManager' initialized.", "DEBUG"
        )  # English Log
    def discover_and_load_widgets(self):
        self.kernel.write_to_log(
            "WidgetManager: Starting discovery and loading of custom widgets...", "INFO"
        )  # English Log
        discovered_widgets = {}
        paused_ids = self._load_paused_status()
        paths_to_scan = [self.widgets_dir]  # + self.dynamic_template_widget_paths
        for base_path in paths_to_scan:
            if not os.path.exists(base_path):
                continue
            self.kernel.write_to_log(
                f"WidgetManager: Scanning for widgets in '{base_path}'", "DEBUG"
            )  # English Log
            for widget_id in os.listdir(base_path):
                if widget_id in self.kernel.globally_disabled_components:
                    self.logger(
                        f"Skipping globally disabled widget: {widget_id}", "WARN"
                    )
                    continue
                widget_dir = os.path.join(base_path, widget_id)
                if os.path.isdir(widget_dir) and widget_id != "__pycache__":
                    self._process_single_widget(
                        widget_dir, widget_id, paused_ids, discovered_widgets
                    )
        self.loaded_widgets = discovered_widgets
        self.logger(
            f"<<< MATA-MATA (1B/4) >>> WidgetManagerService: Discovery complete. Final 'loaded_widgets' contains {len(self.loaded_widgets)} items: {list(self.loaded_widgets.keys())}",
            "WARN",
        )  # English Log
        self.kernel.write_to_log(
            f"WidgetManager: Custom widget loading complete. Total loaded: {len(self.loaded_widgets)}",
            "INFO",
        )  # English Log
    def _process_single_widget(self, widget_dir, widget_id, paused_ids, target_dict):
        self.kernel.write_to_log(
            f" -> Processing widget manifest: '{widget_id}'", "DEBUG"
        )  # English Log
        manifest_path = os.path.join(widget_dir, "manifest.json")
        if not os.path.exists(manifest_path):
            return
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
            target_dict[widget_id] = {
                "class": None,  # IMPORTANT: Set to None as the core doesn't load it.
                "name": manifest.get("name", widget_id),
                "manifest": manifest,
                "path": widget_dir,
                "is_paused": widget_id in paused_ids,
                "tier": manifest.get(
                    "tier", "free"
                ).lower(),  # ADDED: Make sure tier info is available
            }
            self.kernel.write_to_log(
                f" + Success: Widget '{widget_id}' manifest loaded.", "SUCCESS"
            )  # English Log
        except Exception as e:
            self.kernel.write_to_log(
                f" ! Failed to process manifest for widget '{widget_id}': {e}", "ERROR"
            )  # English Log
            import traceback
            self.kernel.write_to_log(traceback.format_exc(), "DEBUG")  # English Log
    def _calculate_requirements_hash(self, file_path):
        sha256_hash = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except IOError:
            return None
    def _load_paused_status(self):
        if os.path.exists(self.paused_status_file):
            try:
                with open(self.paused_status_file, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return []
        return []
    def _save_paused_status(self):
        paused_ids = [
            wid for wid, data in self.loaded_widgets.items() if data.get("is_paused")
        ]
        try:
            with open(self.paused_status_file, "w") as f:
                json.dump(paused_ids, f, indent=4)
        except IOError as e:
            self.kernel.write_to_log(
                f" ! Failed to save widget paused status: {e}", "ERROR"
            )  # English Log
    def set_widget_paused(self, widget_id, is_paused):
        if widget_id in self.loaded_widgets:
            self.loaded_widgets[widget_id]["is_paused"] = is_paused
            self._save_paused_status()
            event_bus = self.kernel.get_service("event_bus")
            if event_bus:
                event_bus.publish(
                    "COMPONENT_LIST_CHANGED",
                    {"type": "widget", "id": widget_id, "paused": is_paused},
                )
            return True
        return False
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
                    )  # English Log
                with open(
                    os.path.join(component_root_path, "manifest.json"),
                    "r",
                    encoding="utf-8",
                ) as f:
                    manifest = json.load(f)
                required_tier = manifest.get("tier", "free")
                if not self.kernel.is_tier_sufficient(required_tier):
                    error_msg = f"Installation failed. This widget requires a '{required_tier.capitalize()}' license or higher. Your current tier is '{self.kernel.license_tier.capitalize()}'."  # English Log
                    self.kernel.write_to_log(error_msg, "ERROR")
                    return False, error_msg
                component_id = manifest.get("id")
                if not component_id:
                    return (
                        False,
                        "Component 'id' is missing from manifest.json.",
                    )  # English Log
                final_path = os.path.join(self.widgets_dir, component_id)
                if os.path.exists(final_path):
                    return (
                        False,
                        f"Widget '{component_id}' is already installed.",
                    )  # English Log
                shutil.move(component_root_path, final_path)
                self.kernel.write_to_log(
                    f"Widget '{component_id}' installed successfully.", "SUCCESS"
                )  # English Log
                return (
                    True,
                    f"Widget '{manifest.get('name', component_id)}' installed successfully.",
                )  # English Log
            except Exception as e:
                self.kernel.write_to_log(
                    f"Widget installation failed: {e}", "ERROR"
                )  # English Log
                return (
                    False,
                    f"An error occurred during widget installation: {e}",
                )  # English Log
    def uninstall_component(self, component_id: str) -> (bool, str):
        if component_id not in self.loaded_widgets:
            return (
                False,
                f"Widget '{component_id}' is not currently loaded or does not exist.",
            )  # English Log
        component_data = self.loaded_widgets[component_id]
        component_path = component_data.get("path")
        if not component_path or not os.path.isdir(component_path):
            return (
                False,
                f"Path for widget '{component_id}' not found or is invalid.",
            )  # English Log
        try:
            shutil.rmtree(component_path)
            del self.loaded_widgets[component_id]
            self.kernel.write_to_log(
                f"Widget '{component_id}' folder deleted successfully.", "SUCCESS"
            )  # English Log
            return (
                True,
                f"Widget '{component_id}' uninstalled. A restart is required to fully clear it.",
            )  # English Log
        except Exception as e:
            self.kernel.write_to_log(
                f"Failed to delete widget folder '{component_path}': {e}", "ERROR"
            )  # English Log
            return False, f"Could not delete widget folder: {e}"  # English Log
