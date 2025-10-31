#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\services\tools_manager_service\tools_manager_service.py JUMLAH BARIS 305 
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
import hashlib
from flowork_kernel.exceptions import PermissionDeniedError
import threading
import shutil
class ToolsManagerService(BaseService):
    """
    Manages tools specifically designed to be used by AI Agents (e.g., Agent Host).
    (REMASTERED V2) Now supports installable, isolated dependencies.
    """
    def __init__(self, kernel, service_id: str):
        super().__init__(kernel, service_id)
        self.tools_dir = self.kernel.tools_path
        self.loaded_tools = {}
        self.instance_cache = {}
        self.paused_status_file = os.path.join(
            self.kernel.data_path, "paused_tools.json"
        )
        self.logger(f"Service 'ToolsManagerService' initialized.", "DEBUG")
    def discover_and_load_tools(self):
        self.logger(
            "ToolsManager: Starting discovery and loading of AI tools...", "INFO"
        )
        self.loaded_tools.clear()
        self.instance_cache.clear()
        paused_ids = self._load_paused_status()
        if not os.path.exists(self.tools_dir):
            self.logger(
                f"Tools directory not found at {self.tools_dir}, creating it.", "WARN"
            )
            os.makedirs(self.tools_dir, exist_ok=True)
            return  # Stop here if the directory was just created
        for item_id in os.listdir(self.tools_dir):
            if item_id in self.kernel.globally_disabled_components:
                self.logger(f"Skipping globally disabled tool: {item_id}", "WARN")
                continue
            item_dir = os.path.join(self.tools_dir, item_id)
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
                    tool_data = {
                        "manifest": manifest,
                        "path": item_dir,
                        "installed_as": "tool",
                        "is_paused": is_paused,
                        "permissions": manifest.get("permissions", []),
                        "tier": manifest.get("tier", "free").lower(),
                        "is_installed": is_installed, # (KODE DARI CHAT SEBELUMNYA)
                    }
                    self.loaded_tools[item_id] = tool_data
                except Exception as e:
                    self.logger(
                        f"   ! Failed to process manifest for tool '{item_id}': {e}",
                        "WARN",
                    )
        self.logger(
            f"ToolsManager: Discovery complete. Found {len(self.loaded_tools)} tools.",
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
    def get_instance(self, tool_id):
        if tool_id in self.instance_cache:
            return self.instance_cache[tool_id]
        if tool_id not in self.loaded_tools:
            self.logger(f"Attempted to get instance for unknown tool_id: {tool_id}", "ERROR") # English Hardcode
            return None
        tool_data = self.loaded_tools[tool_id]
        if tool_data.get("is_paused", False):
            return None
        if not tool_data.get("is_installed", False):
            self.logger(f"Attempted to get instance for non-installed tool: {tool_id}", "ERROR") # English Hardcode
            return None
        self.logger(f"Just-In-Time Load: Instantiating tool '{tool_id}' for the first time.", "DEBUG") # English Hardcode
        vendor_path = os.path.join(tool_data["path"], "vendor") # English Hardcode
        is_vendor_path_added = False
        venv_path = os.path.join(tool_data["path"], ".venv") # English Hardcode
        site_packages_path = self._get_venv_site_packages_path(venv_path)
        is_venv_path_added = False
        try:
            if os.path.isdir(vendor_path) and vendor_path not in sys.path:
                sys.path.insert(0, vendor_path)
                is_vendor_path_added = True
            if site_packages_path and os.path.isdir(site_packages_path):
                if site_packages_path not in sys.path:
                    sys.path.insert(0, site_packages_path)
                    is_venv_path_added = True
                    self.logger(f"Added venv path to sys.path for '{tool_id}': {site_packages_path}", "DEBUG") # English Hardcode
            manifest = tool_data["manifest"]
            entry_point = manifest.get("entry_point")
            if not entry_point:
                raise ValueError(f"'entry_point' not found for '{tool_id}'.") # English Hardcode
            module_filename, class_name = entry_point.split(".")
            source_file_path = os.path.join(tool_data["path"], f"{module_filename}.py")
            if not os.path.exists(source_file_path):
                raise FileNotFoundError(f"Entry point file not found for '{tool_id}'.") # English Hardcode
            safe_tool_id = tool_id.replace("-", "_")
            parent_package_name = f"tools.{safe_tool_id}" # English Hardcode
            module_full_name = f"{parent_package_name}.{module_filename}"
            spec = importlib.util.spec_from_file_location(module_full_name, source_file_path)
            if spec is None:
                raise ImportError(f"Could not create module spec from {source_file_path}")
            module_lib = importlib.util.module_from_spec(spec)
            if "tools" not in sys.modules: # English Hardcode
                spec_base = importlib.util.spec_from_loader("tools", loader=None, is_package=True) # English Hardcode
                module_base = importlib.util.module_from_spec(spec_base)
                sys.modules["tools"] = module_base # English Hardcode
            if parent_package_name not in sys.modules:
                spec_parent = importlib.util.spec_from_loader(parent_package_name, loader=None, is_package=True)
                module_parent = importlib.util.module_from_spec(spec_parent)
                module_parent.__path__ = [tool_data["path"]]
                sys.modules[parent_package_name] = module_parent
            sys.modules[module_full_name] = module_lib
            spec.loader.exec_module(module_lib)
            ProcessorClass = getattr(module_lib, class_name)
            services_to_inject = {}
            requested_services = manifest.get("requires_services", [])
            for service_alias in requested_services:
                if service_alias == "loc":
                    services_to_inject["loc"] = self.kernel.get_service("localization_manager")
                elif service_alias == "logger":
                    services_to_inject["logger"] = self.kernel.write_to_log
                elif service_alias == "kernel":
                    services_to_inject["kernel"] = self.kernel
                else:
                    service_instance = self.kernel.get_service(service_alias)
                    if service_instance:
                        services_to_inject[service_alias] = service_instance
            tool_instance = ProcessorClass(tool_id, services_to_inject)
            if hasattr(tool_instance, "on_load"):
                tool_instance.on_load()
            self.instance_cache[tool_id] = tool_instance
            self.loaded_tools[tool_id]["instance"] = tool_instance
            return tool_instance
        except PermissionDeniedError as e:
            self.logger(f"Skipping instantiation of tool '{tool_id}' due to insufficient permissions: {e}", "WARN") # English Hardcode
            return None
        except Exception as e:
            self.logger(f"CRITICAL FAILURE during Just-In-Time instantiation of tool '{tool_id}': {e}", "CRITICAL") # English Hardcode
            self.logger(traceback.format_exc(), "DEBUG")
            return None
        finally:
            if is_vendor_path_added:
                try: sys.path.remove(vendor_path)
                except ValueError: pass
            if is_venv_path_added:
                try:
                    sys.path.remove(site_packages_path)
                    self.logger(f"Removed venv path from sys.path for '{tool_id}'", "DEBUG") # English Hardcode
                except ValueError: pass
    def get_manifest(self, tool_id):
        return self.loaded_tools.get(tool_id, {}).get("manifest")
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
            tid for tid, data in self.loaded_tools.items() if data.get("is_paused")
        ]
        try:
            with open(self.paused_status_file, "w") as f:
                json.dump(paused_ids, f, indent=4)
        except IOError as e:
            self.kernel.write_to_log(f"Failed to save tool paused status: {e}", "ERROR")
    def set_tool_paused(self, tool_id, is_paused):
        if tool_id in self.loaded_tools:
            instance = self.instance_cache.get(tool_id)
            if is_paused and instance:
                if hasattr(instance, "on_unload"):
                    instance.on_unload()
                del self.instance_cache[tool_id]
            self.loaded_tools[tool_id]["is_paused"] = is_paused
            self._save_paused_status()
            return True
        return False
    def _worker_install_dependencies(self, tool_id: str, on_complete: callable):
        """Worker thread for installing dependencies."""
        try:
            if tool_id not in self.loaded_tools:
                raise FileNotFoundError(f"Tool '{tool_id}' not found in loaded_tools.") # English Hardcode
            tool_data = self.loaded_tools[tool_id]
            component_path = tool_data["path"]
            venv_path = os.path.join(component_path, ".venv") # English Hardcode
            requirements_path = os.path.join(component_path, "requirements.txt") # English Hardcode
            install_marker_path = os.path.join(component_path, ".installed") # English Hardcode
            if not os.path.exists(requirements_path):
                self.logger(f"No requirements.txt found for '{tool_id}'. Marking as installed.", "INFO") # English Hardcode
                with open(install_marker_path, "w") as f:
                    f.write("installed") # English Hardcode
                self.loaded_tools[tool_id]["is_installed"] = True
                on_complete(tool_id, True, "No requirements.txt found, marked as installed.") # English Hardcode
                return
            self.logger(f"Creating venv for '{tool_id}' at {venv_path}...", "INFO") # English Hardcode
            python_executable = sys.executable
            result = subprocess.run(
                [python_executable, "-m", "venv", venv_path],
                capture_output=True, text=True, encoding='utf-8', errors='ignore'
            )
            if result.returncode != 0:
                raise Exception(f"Failed to create venv: {result.stderr}") # English Hardcode
            self.logger(f"Installing requirements for '{tool_id}'...", "INFO") # English Hardcode
            pip_executable = os.path.join(
                venv_path, "Scripts" if sys.platform == "win32" else "bin", "pip"
            )
            result = subprocess.run(
                [pip_executable, "install", "-r", requirements_path, "--no-cache-dir", "--disable-pip-version-check"],
                capture_output=True, text=True, encoding='utf-8', errors='ignore'
            )
            if result.returncode != 0:
                raise Exception(f"Failed to install requirements: {result.stderr}") # English Hardcode
            self.logger(f"Installation successful for '{tool_id}'. Creating marker file.", "SUCCESS") # English Hardcode
            with open(install_marker_path, "w") as f:
                f.write("installed") # English Hardcode
            self.loaded_tools[tool_id]["is_installed"] = True
            on_complete(tool_id, True, f"Dependencies installed successfully: {result.stdout}") # English Hardcode
        except Exception as e:
            self.logger(f"Failed to install dependencies for '{tool_id}': {e}", "ERROR") # English Hardcode
            self.logger(traceback.format_exc(), "DEBUG")
            on_complete(tool_id, False, f"Installation failed: {e}") # English Hardcode
            try:
                if os.path.isdir(venv_path):
                    shutil.rmtree(venv_path)
                if os.path.exists(install_marker_path):
                    os.remove(install_marker_path)
            except Exception as cleanup_e:
                self.logger(f"Failed to cleanup failed install for '{tool_id}': {cleanup_e}", "ERROR") # English Hardcode
    def install_component_dependencies(self, tool_id: str, on_complete: callable):
        """
        Starts the installation process for a tool's dependencies in a separate thread.
        """
        self.logger(f"Queuing dependency installation for tool: {tool_id}", "INFO") # English Hardcode
        install_thread = threading.Thread(
            target=self._worker_install_dependencies,
            args=(tool_id, on_complete)
        )
        install_thread.start()
    def _worker_uninstall_dependencies(self, tool_id: str, on_complete: callable):
        """Worker thread for uninstalling dependencies."""
        try:
            if tool_id not in self.loaded_tools:
                raise FileNotFoundError(f"Tool '{tool_id}' not found in loaded_tools.") # English Hardcode
            tool_data = self.loaded_tools[tool_id]
            component_path = tool_data["path"]
            venv_path = os.path.join(component_path, ".venv") # English Hardcode
            install_marker_path = os.path.join(component_path, ".installed") # English Hardcode
            if os.path.exists(install_marker_path):
                os.remove(install_marker_path)
                self.logger(f"Removed install marker for '{tool_id}'.", "INFO") # English Hardcode
            if os.path.isdir(venv_path):
                shutil.rmtree(venv_path)
                self.logger(f"Removed venv directory for '{tool_id}'.", "INFO") # English Hardcode
            self.loaded_tools[tool_id]["is_installed"] = False
            on_complete(tool_id, True, "Component dependencies uninstalled successfully.") # English Hardcode
        except Exception as e:
            self.logger(f"Failed to uninstall dependencies for '{tool_id}': {e}", "ERROR") # English Hardcode
            self.logger(traceback.format_exc(), "DEBUG")
            on_complete(tool_id, False, f"Uninstallation failed: {e}") # English Hardcode
    def uninstall_component_dependencies(self, tool_id: str, on_complete: callable):
        """
        Starts the uninstallation process for a tool's dependencies in a separate thread.
        """
        self.logger(f"Queuing dependency uninstallation for tool: {tool_id}", "INFO") # English Hardcode
        uninstall_thread = threading.Thread(
            target=self._worker_uninstall_dependencies,
            args=(tool_id, on_complete)
        )
        uninstall_thread.start()
