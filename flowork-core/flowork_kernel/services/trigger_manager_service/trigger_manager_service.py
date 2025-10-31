#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\services\trigger_manager_service\trigger_manager_service.py JUMLAH BARIS 490 
#######################################################################

import os
import json
import importlib.util
from importlib.machinery import ExtensionFileLoader
import uuid
import time
import tempfile
import zipfile
import shutil
from flowork_kernel.api_contract import BaseTriggerListener
from ..base_service import BaseService
import hashlib
import subprocess
import sys
import threading
import shutil
import traceback
class TriggerManagerService(BaseService):
    """
    Manages the discovery, loading, and lifecycle of all Trigger modules.
    (MODIFIED V4) Now supports installable, isolated dependencies.
    """
    def __init__(self, kernel, service_id: str):
        super().__init__(kernel, service_id)
        self.triggers_dir = self.kernel.triggers_path
        self.loaded_triggers = {}
        self.active_listeners = []
        self.cache_file = os.path.join(self.kernel.data_path, "trigger_index.cache")
        self.kernel.write_to_log("Service 'TriggerManager' initialized.", "DEBUG")
    def start(self):
        """
        Subscribes to the main event bus to safely start listeners after all services are ready.
        """
        event_bus = self.kernel.get_service("event_bus")
        if event_bus:
            event_bus.subscribe(
                "event_all_services_started",
                "TriggerManagerStarter",
                self.start_all_listeners,
            )
            self.logger(
                "TriggerManager is now waiting for the signal to start all listeners.",
                "INFO",
            )
    def _is_cache_valid(self):
        if not os.path.exists(self.cache_file):
            return False
        cache_mod_time = os.path.getmtime(self.cache_file)
        if os.path.exists(self.triggers_dir):
            if os.path.getmtime(self.triggers_dir) > cache_mod_time:
                return False
            for root, dirs, _ in os.walk(self.triggers_dir):
                for d in dirs:
                    if os.path.getmtime(os.path.join(root, d)) > cache_mod_time:
                        return False
        return True
    def discover_and_load_triggers(self):
        self.kernel.write_to_log(
            "TriggerManager: Starting discovery and loading of Trigger modules...",
            "INFO",
        )
        self.loaded_triggers.clear()
        if self._is_cache_valid():
            self.kernel.write_to_log(
                "TriggerManager: Valid cache found. Loading triggers from index...",
                "INFO",
            )
            with open(self.cache_file, "r", encoding="utf-8") as f:
                cached_data = json.load(f)
            for trigger_id, trigger_data in cached_data.items():
                self._process_single_trigger(
                    trigger_dir=trigger_data["path"],
                    trigger_id=trigger_id,
                    manifest_override=trigger_data["manifest"],
                )
            self.kernel.write_to_log(
                f"Trigger discovery from cache complete. Total processed: {len(self.loaded_triggers)}",
                "INFO",
            )
            return
        self.kernel.write_to_log(
            "TriggerManager: Cache not found or stale. Discovering from disk...", "WARN"
        )
        discovered_data_for_cache = {}
        if not os.path.exists(self.triggers_dir):
            self.kernel.write_to_log(
                f"Triggers directory '{self.triggers_dir}' not found. Skipping.", "WARN"
            )
            return
        for trigger_id in os.listdir(self.triggers_dir):
            if trigger_id in self.kernel.globally_disabled_components:
                self.logger(f"Skipping globally disabled trigger: {trigger_id}", "WARN")
                continue
            trigger_dir = os.path.join(self.triggers_dir, trigger_id)
            if not os.path.isdir(trigger_dir) or trigger_id == "__pycache__":
                continue
            manifest = self._process_single_trigger(trigger_dir, trigger_id)
            if manifest:
                discovered_data_for_cache[trigger_id] = {
                    "manifest": manifest,
                    "path": trigger_dir,
                }
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(discovered_data_for_cache, f)
            self.kernel.write_to_log(
                f"TriggerManager: Trigger index cache created at {self.cache_file}",
                "SUCCESS",
            )
        except Exception as e:
            self.kernel.write_to_log(
                f"TriggerManager: Failed to write trigger cache file: {e}", "ERROR"
            )
        self.kernel.write_to_log(
            f"Trigger discovery complete. Total processed: {len(self.loaded_triggers)}",
            "INFO",
        )
    def _get_venv_site_packages_path(self, venv_path):
        """Finds the site-packages directory for a given venv."""
        if sys.platform == "win32":
            return os.path.join(venv_path, "Lib", "site-packages") # English Hardcode
        else:
            lib_path = os.path.join(venv_path, "lib") # English Hardcode
            if os.path.isdir(lib_path):
                py_dirs = [d for d in os.listdir(lib_path) if d.startswith('python')] # English Hardcode
                if py_dirs:
                    return os.path.join(lib_path, py_dirs[0], "site-packages") # English Hardcode
        return None
    def _process_single_trigger(self, trigger_dir, trigger_id, manifest_override=None):
        manifest = manifest_override
        if manifest is None:
            manifest_path = os.path.join(trigger_dir, "manifest.json")
            if not os.path.exists(manifest_path):
                return None
            try:
                with open(manifest_path, "r", encoding="utf-8") as f:
                    manifest = json.load(f)
            except Exception as e:
                self.kernel.write_to_log(
                    f" ! Failed to load trigger manifest for '{trigger_id}': {e}",
                    "ERROR",
                )
                return None
        try:
            self.kernel.write_to_log(
                f" -> Found trigger: '{manifest.get('name', trigger_id)}'", "DEBUG"
            )
            listener_entry = manifest.get(
                "listener_entry_point", manifest.get("entry_point")
            )
            install_marker_path = os.path.join(trigger_dir, ".installed") # English Hardcode
            is_installed = os.path.exists(install_marker_path)
            trigger_data = {
                "listener_class": None,
                "manifest": manifest,
                "path": trigger_dir,
                "is_installed": is_installed, # (KODE DARI CHAT SEBELUMNYA)
            }
            if listener_entry:
                module_filename, class_name = listener_entry.split(".")
                source_file_path = os.path.join(trigger_dir, f"{module_filename}.py")
                native_file_path = os.path.join(
                    trigger_dir, f"{module_filename}.trigger.flowork"
                )
                path_to_load = None
                is_native_module = False
                if os.path.exists(native_file_path):
                    path_to_load = native_file_path
                    is_native_module = True
                elif os.path.exists(source_file_path):
                    path_to_load = source_file_path
                if not path_to_load:
                    raise FileNotFoundError(
                        f"Entry point file '{module_filename}.py' or '{os.path.basename(native_file_path)}' not found."
                    )
                venv_path = os.path.join(trigger_dir, ".venv") # English Hardcode
                site_packages_path = self._get_venv_site_packages_path(venv_path)
                is_venv_path_added = False
                if is_installed and site_packages_path and os.path.isdir(site_packages_path):
                    if site_packages_path not in sys.path:
                        sys.path.insert(0, site_packages_path)
                        is_venv_path_added = True
                        self.logger(f"Added venv path to sys.path for '{trigger_id}': {site_packages_path}", "DEBUG") # English Hardcode
                try:
                    safe_trigger_id = trigger_id.replace("-", "_")
                    module_full_name = f"triggers.{safe_trigger_id}.{module_filename}"
                    if is_native_module:
                        loader = ExtensionFileLoader(module_full_name, path_to_load)
                        spec = importlib.util.spec_from_loader(loader.name, loader)
                    else:
                        spec = importlib.util.spec_from_file_location(
                            module_full_name, source_file_path
                        )
                    module_lib = importlib.util.module_from_spec(spec)
                    if module_full_name not in sys.modules:
                        sys.modules[module_full_name] = module_lib
                    spec.loader.exec_module(module_lib)
                    ListenerClass = getattr(module_lib, class_name)
                    if not issubclass(ListenerClass, BaseTriggerListener):
                        if (
                            manifest.get("id") != "cron_trigger"
                        ):  # Cron trigger is a special case handled by scheduler
                            raise TypeError(
                                f"Class '{class_name}' must inherit from BaseTriggerListener."
                            )
                    trigger_data["listener_class"] = ListenerClass
                finally:
                    if is_venv_path_added:
                        try:
                            sys.path.remove(site_packages_path)
                            self.logger(f"Removed venv path from sys.path for '{trigger_id}'", "DEBUG") # English Hardcode
                        except ValueError:
                            pass
            self.loaded_triggers[trigger_id] = trigger_data
            self.kernel.write_to_log(
                f" + Trigger '{manifest.get('name', trigger_id)}' processed successfully.",
                "SUCCESS",
            )
        except Exception as e:
            self.kernel.write_to_log(
                f" ! Failed to load trigger from folder '{trigger_id}': {e}", "ERROR"
            )
        return manifest
    def _calculate_requirements_hash(self, file_path):
        sha256_hash = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except IOError:
            return None
    def get_config_ui_class(self, trigger_id: str):
        return None
    def start_all_listeners(self, event_data=None):
        self.kernel.write_to_log(
            "TriggerManager: Starting all listeners and scheduling rules...", "INFO"
        )
        self.stop_all_listeners()
        scheduler_manager = self.kernel.get_service("scheduler_manager_service")
        if scheduler_manager and scheduler_manager.scheduler.running:
            scheduler_manager.scheduler.remove_all_jobs()
        state_manager = self.kernel.get_service("state_manager")
        rules = (
            state_manager.get("trigger_rules", default={}) if state_manager else {}
        )  # TAMBAHAN: [PERBAIKAN DARI GEMINI] Menggunakan keyword argument 'default' agar aman
        for rule_id, rule_data in rules.items():
            if not rule_data.get("is_enabled", False):
                continue
            trigger_id = rule_data.get("trigger_id")
            if trigger_id == "cron_trigger":
                if scheduler_manager:
                    scheduler_manager.schedule_rule(rule_id, rule_data)
            else:
                trigger_info = self.loaded_triggers.get(trigger_id)
                if not trigger_info:
                    continue
                if not trigger_info.get("is_installed", False):
                    self.kernel.write_to_log(f"Cannot start listener for rule '{rule_data.get('name')}': Trigger '{trigger_id}' is not installed.", "WARN") # English Hardcode
                    continue
                ListenerClass = trigger_info.get("listener_class")
                if not ListenerClass:
                    continue
                try:
                    config = rule_data.get("config", {})
                    services_to_inject = {
                        "kernel": self.kernel,
                        "loc": self.loc,
                        "state_manager": state_manager,
                        "event_bus": self.kernel.get_service("event_bus"),
                        "logger": self.kernel.write_to_log,
                    }
                    listener_instance = ListenerClass(
                        trigger_id=trigger_id,
                        config=config,
                        services=services_to_inject,
                        rule_id=rule_id,
                    )
                    listener_instance.set_callback(self._handle_event)
                    listener_instance.start()
                    self.active_listeners.append(listener_instance)
                except Exception as e:
                    self.kernel.write_to_log(
                        f"Failed to start listener for rule '{rule_data.get('name')}': {e}",
                        "ERROR",
                    )
    def stop_all_listeners(self):
        if not self.active_listeners:
            return
        for listener in self.active_listeners:
            try:
                listener.stop()
            except Exception as e:
                self.kernel.write_to_log(
                    f"Error while stopping listener for trigger '{listener.trigger_id}': {e}",
                    "ERROR",
                )
        self.active_listeners.clear()
    def _handle_event(self, event_data: dict):
        rule_id = event_data.get("rule_id")
        state_manager = self.kernel.get_service("state_manager")
        if not rule_id or not state_manager:
            return
        rules = state_manager.get("trigger_rules", {})
        rule_data = rules.get(rule_id)
        if not rule_data:
            return
        preset_to_run = rule_data.get("preset_to_run")
        if not preset_to_run:
            return
        self.kernel.write_to_log(
            f"TRIGGER DETECTED! Rule '{rule_data.get('name')}' met. Scheduling execution for preset '{preset_to_run}'.",
            "SUCCESS",
        )
        initial_payload = {
            "data": {
                "trigger_type": "event",
                "trigger_rule_id": rule_id,
                "trigger_rule_name": rule_data.get("name"),
                "trigger_event_data": event_data,
            },
            "history": [],
        }
        api_service = self.kernel.get_service("api_server_service")
        if api_service:
            api_service.trigger_workflow_by_api(
                preset_name=preset_to_run, initial_payload=initial_payload
            )
    def _worker_install_dependencies(self, trigger_id: str, on_complete: callable):
        """Worker thread for installing dependencies."""
        try:
            if trigger_id not in self.loaded_triggers:
                raise FileNotFoundError(f"Trigger '{trigger_id}' not found in loaded_triggers.") # English Hardcode
            trigger_data = self.loaded_triggers[trigger_id]
            component_path = trigger_data["path"]
            venv_path = os.path.join(component_path, ".venv") # English Hardcode
            requirements_path = os.path.join(component_path, "requirements.txt") # English Hardcode
            install_marker_path = os.path.join(component_path, ".installed") # English Hardcode
            if not os.path.exists(requirements_path):
                self.logger(f"No requirements.txt found for '{trigger_id}'. Marking as installed.", "INFO") # English Hardcode
                with open(install_marker_path, "w") as f:
                    f.write("installed") # English Hardcode
                self.loaded_triggers[trigger_id]["is_installed"] = True
                on_complete(trigger_id, True, "No requirements.txt found, marked as installed.") # English Hardcode
                return
            self.logger(f"Creating venv for '{trigger_id}' at {venv_path}...", "INFO") # English Hardcode
            python_executable = sys.executable
            result = subprocess.run(
                [python_executable, "-m", "venv", venv_path],
                capture_output=True, text=True, encoding='utf-8', errors='ignore'
            )
            if result.returncode != 0:
                raise Exception(f"Failed to create venv: {result.stderr}") # English Hardcode
            self.logger(f"Installing requirements for '{trigger_id}'...", "INFO") # English Hardcode
            pip_executable = os.path.join(
                venv_path, "Scripts" if sys.platform == "win32" else "bin", "pip"
            )
            result = subprocess.run(
                [pip_executable, "install", "-r", requirements_path, "--no-cache-dir", "--disable-pip-version-check"],
                capture_output=True, text=True, encoding='utf-8', errors='ignore'
            )
            if result.returncode != 0:
                raise Exception(f"Failed to install requirements: {result.stderr}") # English Hardcode
            self.logger(f"Installation successful for '{trigger_id}'. Creating marker file.", "SUCCESS") # English Hardcode
            with open(install_marker_path, "w") as f:
                f.write("installed") # English Hardcode
            self.loaded_triggers[trigger_id]["is_installed"] = True
            on_complete(trigger_id, True, f"Dependencies installed successfully: {result.stdout}") # English Hardcode
        except Exception as e:
            self.logger(f"Failed to install dependencies for '{trigger_id}': {e}", "ERROR") # English Hardcode
            self.logger(traceback.format_exc(), "DEBUG")
            on_complete(trigger_id, False, f"Installation failed: {e}") # English Hardcode
            try:
                if os.path.isdir(venv_path):
                    shutil.rmtree(venv_path)
                if os.path.exists(install_marker_path):
                    os.remove(install_marker_path)
            except Exception as cleanup_e:
                self.logger(f"Failed to cleanup failed install for '{trigger_id}': {cleanup_e}", "ERROR") # English Hardcode
    def install_component_dependencies(self, trigger_id: str, on_complete: callable):
        """
        Starts the installation process for a trigger's dependencies in a separate thread.
        """
        self.logger(f"Queuing dependency installation for trigger: {trigger_id}", "INFO") # English Hardcode
        install_thread = threading.Thread(
            target=self._worker_install_dependencies,
            args=(trigger_id, on_complete)
        )
        install_thread.start()
    def _worker_uninstall_dependencies(self, trigger_id: str, on_complete: callable):
        """Worker thread for uninstalling dependencies."""
        try:
            if trigger_id not in self.loaded_triggers:
                raise FileNotFoundError(f"Trigger '{trigger_id}' not found in loaded_triggers.") # English Hardcode
            trigger_data = self.loaded_triggers[trigger_id]
            component_path = trigger_data["path"]
            venv_path = os.path.join(component_path, ".venv") # English Hardcode
            install_marker_path = os.path.join(component_path, ".installed") # English Hardcode
            if os.path.exists(install_marker_path):
                os.remove(install_marker_path)
                self.logger(f"Removed install marker for '{trigger_id}'.", "INFO") # English Hardcode
            if os.path.isdir(venv_path):
                shutil.rmtree(venv_path)
                self.logger(f"Removed venv directory for '{trigger_id}'.", "INFO") # English Hardcode
            self.loaded_triggers[trigger_id]["is_installed"] = False
            on_complete(trigger_id, True, "Component dependencies uninstalled successfully.") # English Hardcode
        except Exception as e:
            self.logger(f"Failed to uninstall dependencies for '{trigger_id}': {e}", "ERROR") # English Hardcode
            self.logger(traceback.format_exc(), "DEBUG")
            on_complete(trigger_id, False, f"Uninstallation failed: {e}") # English Hardcode
    def uninstall_component_dependencies(self, trigger_id: str, on_complete: callable):
        """
        Starts the uninstallation process for a trigger's dependencies in a separate thread.
        """
        self.logger(f"Queuing dependency uninstallation for trigger: {trigger_id}", "INFO") # English Hardcode
        uninstall_thread = threading.Thread(
            target=self._worker_uninstall_dependencies,
            args=(trigger_id, on_complete)
        )
        uninstall_thread.start()
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
                    error_msg = f"Installation failed. This trigger requires a '{required_tier.capitalize()}' license."
                    return False, error_msg
                component_id = manifest.get("id")
                if not component_id:
                    return False, "Component 'id' is missing from manifest.json."
                final_path = os.path.join(self.triggers_dir, component_id)
                if os.path.exists(final_path):
                    return False, f"Trigger '{component_id}' is already installed."
                shutil.move(component_root_path, final_path)
                return (
                    True,
                    f"Trigger '{manifest.get('name', component_id)}' installed successfully.",
                )
            except Exception as e:
                return False, f"An error occurred during trigger installation: {e}"
    def uninstall_component(self, component_id: str) -> (bool, str):
        if component_id not in self.loaded_triggers:
            return (
                False,
                f"Trigger '{component_id}' is not currently loaded or does not exist.",
            )
        component_path = self.loaded_triggers[component_id].get("path")
        if not component_path or not os.path.isdir(component_path):
            return False, f"Path for trigger '{component_id}' not found."
        try:
            shutil.rmtree(component_path)
            del self.loaded_triggers[component_id]
            return True, f"Trigger '{component_id}' uninstalled successfully."
        except Exception as e:
            return False, f"Could not delete trigger folder: {e}"
