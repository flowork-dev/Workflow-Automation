#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\services\module_manager_service\module_manager_service.py JUMLAH BARIS 450 
#######################################################################

import os
import json
import importlib.util
import subprocess
import sys
import traceback
from flowork_kernel.api_contract import BaseModule
from ..base_service import BaseService
import zipfile
import tempfile
import shutil
from flowork_kernel.exceptions import PermissionDeniedError
import hashlib
import threading
import shutil
class ModuleManagerService(BaseService):
    """
    (REMASTERED V8) Manages modules with installable, isolated dependencies.
    """
    def __init__(self, kernel, service_id: str):
        super().__init__(kernel, service_id)
        self.modules_dir = self.kernel.modules_path
        self.loaded_modules = {}
        self.instance_cache = {}
        self.paused_status_file = os.path.join(
            self.kernel.data_path, "paused_modules.json"
        )
        self._manual_approval_callbacks = {}
        self.logger("Service 'ModuleManager' initialized.", "DEBUG")
    def discover_and_load_modules(self):
        self.logger(
            "ModuleManager: Starting discovery and loading based on folder location...",
            "INFO",
        )
        self.loaded_modules.clear()
        self.instance_cache.clear()
        paused_ids = self._load_paused_status()
        if not os.path.exists(self.modules_dir):
            self.logger(
                f"Modules directory not found at {self.modules_dir}, skipping.", "WARN"
            )
            return
        for item_id in os.listdir(self.modules_dir):
            if item_id in self.kernel.globally_disabled_components:
                self.logger(f"Skipping globally disabled module: {item_id}", "WARN")
                continue
            item_dir = os.path.join(self.modules_dir, item_id)
            if os.path.isdir(item_dir) and item_id != "__pycache__":
                manifest_path = os.path.join(item_dir, "manifest.json")
                if not os.path.exists(manifest_path):
                    continue
                try:
                    with open(manifest_path, "r", encoding="utf-8") as f:
                        manifest = json.load(f)
                    is_paused = item_id in paused_ids
                    install_marker_path = os.path.join(item_dir, ".installed") # English Hardcode
                    is_installed = os.path.exists(install_marker_path)
                    module_data = {
                        "manifest": manifest,
                        "path": item_dir,
                        "installed_as": "module",
                        "is_paused": is_paused,
                        "permissions": manifest.get("permissions", []),
                        "tier": manifest.get("tier", "free").lower(),
                        "is_installed": is_installed, # (KODE DARI CHAT SEBELUMNYA)
                    }
                    self.loaded_modules[item_id] = module_data
                except Exception as e:
                    self.logger(
                        f"   ! Failed to process manifest for module '{item_id}': {e}",
                        "WARN",
                    )
        self.logger(
            f"<<< MATA-MATA (1/4) >>> ModuleManagerService: Discovery complete. Final 'loaded_modules' contains {len(self.loaded_modules)} items: {list(self.loaded_modules.keys())}",
            "WARN",
        )
        var_manager = self.kernel.get_service("variable_manager_service")
        if var_manager:
            var_manager.autodiscover_and_sync_variables()
        self.logger(
            f"ModuleManager: Discovery complete. Found {len(self.loaded_modules)} modules.",
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
    def get_instance(self, module_id):
        if module_id in self.instance_cache:
            return self.instance_cache[module_id]
        if module_id not in self.loaded_modules:
            self.logger(
                f"Attempted to get instance for unknown module_id: {module_id}", "ERROR"
            )
            return None
        module_data = self.loaded_modules[module_id]
        if module_data.get("is_paused", False):
            self.logger(f"Attempted to get instance for paused module: {module_id}", "WARN") # English Hardcode
            return None
        if not module_data.get("is_installed", False):
            self.logger(f"Attempted to get instance for non-installed module: {module_id}", "ERROR") # English Hardcode
            return None
        self.logger(
            f"Just-In-Time Load: Instantiating '{module_id}' for the first time.",
            "DEBUG",
        )
        vendor_path = os.path.join(module_data["path"], "vendor")
        is_path_added = False
        venv_path = os.path.join(module_data["path"], ".venv") # English Hardcode
        site_packages_path = self._get_venv_site_packages_path(venv_path)
        is_venv_path_added = False
        try:
            if os.path.isdir(vendor_path):
                if vendor_path not in sys.path:
                    sys.path.insert(0, vendor_path)
                    is_path_added = True
            if site_packages_path and os.path.isdir(site_packages_path):
                if site_packages_path not in sys.path:
                    sys.path.insert(0, site_packages_path)
                    is_venv_path_added = True
                    self.logger(f"Added venv path to sys.path for '{module_id}': {site_packages_path}", "DEBUG") # English Hardcode
            manifest = module_data["manifest"]
            entry_point = manifest.get("entry_point")
            if not entry_point:
                raise ValueError(f"'entry_point' not found for '{module_id}'.")
            module_filename, class_name = entry_point.split(".")
            source_file_path = os.path.join(
                module_data["path"], f"{module_filename}.py"
            )
            path_to_load = source_file_path  # COMMENT: Directly use the .py file path.
            if not path_to_load or not os.path.exists(path_to_load):
                raise FileNotFoundError(
                    f"Entry point file '{os.path.basename(source_file_path)}' not found for '{module_id}'."
                )
            safe_module_id = module_id.replace("-", "_")
            parent_package_name = f"modules.{safe_module_id}"
            module_full_name = f"{parent_package_name}.{module_filename}"
            spec = importlib.util.spec_from_file_location(
                module_full_name, path_to_load
            )
            if spec is None:
                raise ImportError(f"Could not create module spec from {path_to_load}")
            module_lib = importlib.util.module_from_spec(spec)
            if parent_package_name not in sys.modules:
                if "modules" not in sys.modules:
                    spec_base = importlib.util.spec_from_loader(
                        "modules", loader=None, is_package=True
                    )
                    module_base = importlib.util.module_from_spec(spec_base)
                    sys.modules["modules"] = module_base
                spec_parent = importlib.util.spec_from_loader(
                    parent_package_name, loader=None, is_package=True
                )
                module_parent = importlib.util.module_from_spec(spec_parent)
                module_parent.__path__ = [module_data["path"]]
                sys.modules[parent_package_name] = module_parent
            sys.modules[module_full_name] = module_lib
            spec.loader.exec_module(module_lib)
            ProcessorClass = getattr(module_lib, class_name)
            services_to_inject = {}
            requested_services = manifest.get("requires_services", [])
            for service_alias in requested_services:
                if service_alias == "loc":
                    services_to_inject["loc"] = self.kernel.get_service(
                        "localization_manager"
                    )
                elif service_alias == "logger":
                    services_to_inject["logger"] = self.kernel.write_to_log
                elif service_alias == "kernel":
                    services_to_inject["kernel"] = self.kernel
                else:
                    service_instance = self.kernel.get_service(service_alias)
                    if service_instance:
                        services_to_inject[service_alias] = service_instance
            module_instance = ProcessorClass(module_id, services_to_inject)
            if hasattr(module_instance, "on_load"):
                module_instance.on_load()
            self.instance_cache[module_id] = module_instance
            self.loaded_modules[module_id]["instance"] = module_instance
            return module_instance
        except PermissionDeniedError as e:
            self.logger(
                f"Skipping instantiation of '{module_id}' due to insufficient permissions: {e}",
                "WARN",
            )
            return None
        except Exception as e:
            self.logger(
                f"CRITICAL FAILURE during Just-In-Time instantiation of '{module_id}': {e}",
                "CRITICAL",
            )
            self.logger(traceback.format_exc(), "DEBUG")
            return None
        finally:
            if is_path_added:
                try:
                    sys.path.remove(vendor_path)
                except ValueError:
                    pass
            if is_venv_path_added:
                try:
                    sys.path.remove(site_packages_path)
                    self.logger(f"Removed venv path from sys.path for '{module_id}'", "DEBUG") # English Hardcode
                except ValueError:
                    pass
    def _calculate_requirements_hash(self, file_path):
        sha256_hash = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except IOError:
            return None
    def get_manifest(self, module_id):
        return self.loaded_modules.get(module_id, {}).get("manifest")
    def get_module_permissions(self, module_id):
        return self.loaded_modules.get(module_id, {}).get("permissions", [])
    def get_module_tier(self, module_id):
        return self.loaded_modules.get(module_id, {}).get("tier", "free")
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
            mid for mid, data in self.loaded_modules.items() if data.get("is_paused")
        ]
        try:
            with open(self.paused_status_file, "w") as f:
                json.dump(paused_ids, f, indent=4)
        except IOError as e:
            self.kernel.write_to_log(f"Failed to save paused status: {e}", "ERROR")
    def set_module_paused(self, module_id, is_paused):
        if module_id in self.loaded_modules:
            instance = self.instance_cache.get(module_id)
            if is_paused and instance:
                if hasattr(instance, "on_unload"):
                    instance.on_unload()
                del self.instance_cache[module_id]
            self.loaded_modules[module_id]["is_paused"] = is_paused
            self._save_paused_status()
            return True
        return False
    def register_approval_callback(self, module_id, callback):
        self._manual_approval_callbacks[module_id] = callback
    def notify_approval_response(self, module_id: str, result: str):
        if module_id in self._manual_approval_callbacks:
            callback = self._manual_approval_callbacks.pop(module_id)
            if callable(callback):
                threading.Thread(target=callback, args=(result,)).start()
        else:
            self.logger(
                f"Received approval response for an unknown or timed-out module: '{module_id}'.",
                "WARN",
            )
    def _worker_install_dependencies(self, module_id: str, on_complete: callable):
        """Worker thread for installing dependencies."""
        try:
            if module_id not in self.loaded_modules:
                raise FileNotFoundError(f"Module '{module_id}' not found in loaded_modules.") # English Hardcode
            module_data = self.loaded_modules[module_id]
            component_path = module_data["path"]
            venv_path = os.path.join(component_path, ".venv") # English Hardcode
            requirements_path = os.path.join(component_path, "requirements.txt") # English Hardcode
            install_marker_path = os.path.join(component_path, ".installed") # English Hardcode
            if not os.path.exists(requirements_path):
                self.logger(f"No requirements.txt found for '{module_id}'. Marking as installed.", "INFO") # English Hardcode
                with open(install_marker_path, "w") as f:
                    f.write("installed") # English Hardcode
                self.loaded_modules[module_id]["is_installed"] = True
                on_complete(module_id, True, "No requirements.txt found, marked as installed.") # English Hardcode
                return
            self.logger(f"Creating venv for '{module_id}' at {venv_path}...", "INFO") # English Hardcode
            python_executable = sys.executable
            result = subprocess.run(
                [python_executable, "-m", "venv", venv_path],
                capture_output=True, text=True, encoding='utf-8', errors='ignore'
            )
            if result.returncode != 0:
                raise Exception(f"Failed to create venv: {result.stderr}") # English Hardcode
            self.logger(f"Installing requirements for '{module_id}'...", "INFO") # English Hardcode
            pip_executable = os.path.join(
                venv_path, "Scripts" if sys.platform == "win32" else "bin", "pip"
            )
            result = subprocess.run(
                [pip_executable, "install", "-r", requirements_path, "--no-cache-dir", "--disable-pip-version-check"],
                capture_output=True, text=True, encoding='utf-8', errors='ignore'
            )
            if result.returncode != 0:
                raise Exception(f"Failed to install requirements: {result.stderr}") # English Hardcode
            self.logger(f"Installation successful for '{module_id}'. Creating marker file.", "SUCCESS") # English Hardcode
            with open(install_marker_path, "w") as f:
                f.write("installed") # English Hardcode
            self.loaded_modules[module_id]["is_installed"] = True
            on_complete(module_id, True, f"Dependencies installed successfully: {result.stdout}") # English Hardcode
        except Exception as e:
            self.logger(f"Failed to install dependencies for '{module_id}': {e}", "ERROR") # English Hardcode
            self.logger(traceback.format_exc(), "DEBUG")
            on_complete(module_id, False, f"Installation failed: {e}") # English Hardcode
            try:
                if os.path.isdir(venv_path):
                    shutil.rmtree(venv_path)
                if os.path.exists(install_marker_path):
                    os.remove(install_marker_path)
            except Exception as cleanup_e:
                self.logger(f"Failed to cleanup failed install for '{module_id}': {cleanup_e}", "ERROR") # English Hardcode
    def install_component_dependencies(self, module_id: str, on_complete: callable):
        """
        Starts the installation process for a module's dependencies in a separate thread.
        """
        self.logger(f"Queuing dependency installation for module: {module_id}", "INFO") # English Hardcode
        install_thread = threading.Thread(
            target=self._worker_install_dependencies,
            args=(module_id, on_complete)
        )
        install_thread.start()
    def _worker_uninstall_dependencies(self, module_id: str, on_complete: callable):
        """Worker thread for uninstalling dependencies."""
        try:
            if module_id not in self.loaded_modules:
                raise FileNotFoundError(f"Module '{module_id}' not found in loaded_modules.") # English Hardcode
            module_data = self.loaded_modules[module_id]
            component_path = module_data["path"]
            venv_path = os.path.join(component_path, ".venv") # English Hardcode
            install_marker_path = os.path.join(component_path, ".installed") # English Hardcode
            if os.path.exists(install_marker_path):
                os.remove(install_marker_path)
                self.logger(f"Removed install marker for '{module_id}'.", "INFO") # English Hardcode
            if os.path.isdir(venv_path):
                shutil.rmtree(venv_path)
                self.logger(f"Removed venv directory for '{module_id}'.", "INFO") # English Hardcode
            self.loaded_modules[module_id]["is_installed"] = False
            on_complete(module_id, True, "Component dependencies uninstalled successfully.") # English Hardcode
        except Exception as e:
            self.logger(f"Failed to uninstall dependencies for '{module_id}': {e}", "ERROR") # English Hardcode
            self.logger(traceback.format_exc(), "DEBUG")
            on_complete(module_id, False, f"Uninstallation failed: {e}") # English Hardcode
    def uninstall_component_dependencies(self, module_id: str, on_complete: callable):
        """
        Starts the uninstallation process for a module's dependencies in a separate thread.
        """
        self.logger(f"Queuing dependency uninstallation for module: {module_id}", "INFO") # English Hardcode
        uninstall_thread = threading.Thread(
            target=self._worker_uninstall_dependencies,
            args=(module_id, on_complete)
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
                    error_msg = f"Installation failed. This component requires a '{required_tier.capitalize()}' license or higher. Your current tier is '{self.kernel.license_tier.capitalize()}'."
                    self.kernel.write_to_log(error_msg, "ERROR")
                    return False, error_msg
                component_id = manifest.get("id")
                if not component_id:
                    return False, "Component 'id' is missing from manifest.json."
                final_path = os.path.join(self.modules_dir, component_id)
                if os.path.exists(final_path):
                    return False, f"Component '{component_id}' is already installed."
                shutil.move(component_root_path, final_path)
                self.kernel.write_to_log(
                    f"Component '{component_id}' installed successfully to '{self.modules_dir}'.",
                    "SUCCESS",
                )
                return (
                    True,
                    f"Component '{manifest.get('name', component_id)}' installed successfully.",
                )
            except Exception as e:
                self.kernel.write_to_log(f"Installation failed: {e}", "ERROR")
                return False, f"An error occurred during installation: {e}"
    def uninstall_component(self, component_id: str) -> (bool, str):
        if component_id not in self.loaded_modules:
            return (
                False,
                f"Component '{component_id}' is not currently loaded or does not exist.",
            )
        component_data = self.loaded_modules[component_id]
        component_path = component_data.get("path")
        if not component_path or not os.path.isdir(component_path):
            return (
                False,
                f"Path for component '{component_id}' not found or is invalid.",
            )
        try:
            shutil.rmtree(component_path)
            del self.loaded_modules[component_id]
            if component_id in self.instance_cache:
                del self.instance_cache[component_id]
            self.kernel.write_to_log(
                f"Component '{component_id}' folder deleted successfully.", "SUCCESS"
            )
            return (
                True,
                f"Component '{component_id}' uninstalled. A restart is required to fully clear it.",
            )
        except Exception as e:
            self.kernel.write_to_log(
                f"Failed to delete component folder '{component_path}': {e}", "ERROR"
            )
            return False, f"Could not delete component folder: {e}"
