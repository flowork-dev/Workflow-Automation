#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\kernel_logic.py JUMLAH BARIS 595 
#######################################################################

import os
import sys
import json
import time
import logging
import threading
import queue
import importlib
import datetime
import asyncio
from typing import List, Dict, Any, Callable
import requests
from packaging import version
from flowork_kernel.exceptions import PermissionDeniedError
class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "source": "flowork-core",
        }
        if hasattr(record, "extra_info"):
            log_record.update(record.extra_info)
        return json.dumps(log_record)
class ServiceWorkflowProxy:
    def __init__(self, kernel, service_id, preset_path):
        self.kernel = kernel
        self.service_id = service_id
        self.preset_path = os.path.join(
            self.kernel.project_root_path, preset_path.replace("/", os.sep)
        )
        self.workflow_data = None
        self.nodes = {}
        self.connections = {}
        self._load_workflow_definition()
    def _load_workflow_definition(self):
        try:
            if not os.path.exists(self.preset_path):
                raise FileNotFoundError(
                    f"Service preset file not found at calculated path: {self.preset_path}"
                )
            with open(self.preset_path, "r", encoding="utf-8") as f:
                self.workflow_data = json.load(f)
            self.nodes = {
                node["id"]: node for node in self.workflow_data.get("nodes", [])
            }
            self.connections = {
                conn["id"]: conn for conn in self.workflow_data.get("connections", [])
            }
            self.kernel.write_to_log(
                f"Service workflow definition for '{self.service_id}' loaded successfully.",
                "SUCCESS",
            )
        except Exception as e:
            self.kernel.write_to_log(
                f"CRITICAL: Failed to load service workflow for '{self.service_id}': {e}",
                "ERROR",
            )
            self.workflow_data = None
    def reload_definition(self):
        self.kernel.write_to_log(f"Reload request ignored for service workflow proxy '{self.service_id}'.", "WARN") # English Hardcode
    def __getattr__(self, name):
        def method(*args, **kwargs):
            self.kernel.write_to_log(
                f"Proxy '{self.service_id}': Method '{name}' called. Executing corresponding workflow...",
                "INFO",
            )
            if not self.workflow_data:
                self.kernel.write_to_log(
                    f"Cannot execute '{name}' for service '{self.service_id}', workflow definition failed to load.",
                    "ERROR",
                )
                return None
            start_node_id = None
            sanitized_name = name.replace(" ", "_")
            for node_id, node_data in self.nodes.items():
                if (
                    node_data.get("name", "").strip().replace(" ", "_")
                    == sanitized_name
                ):
                    start_node_id = node_id
                    break
            if not start_node_id:
                self.kernel.write_to_log(
                    f"No start node named '{name}' found in workflow for service '{self.service_id}'.",
                    "ERROR",
                )
                return None
            context_id = f"service_call_{self.service_id}_{name}_{time.time()}"
            executor = self.kernel.get_service(
                "workflow_executor_service", is_system_call=True
            )
            if not executor:
                self.kernel.write_to_log(
                    f"WorkflowExecutorService not available to run service '{self.service_id}'.",
                    "CRITICAL",
                )
                return None
            initial_payload = {"data": {"args": args, "kwargs": kwargs}, "history": []}
            execution_result = executor.execute_workflow_synchronous(
                self.nodes,
                self.connections,
                initial_payload,
                logger=self.kernel.write_to_log,
                status_updater=lambda a, b, c: None,
                highlighter=lambda a, b: None,
                workflow_context_id=context_id,
                mode="EXECUTE", # Service workflows always execute
                job_status_updater=None,
            )
            if isinstance(execution_result, dict) and "payload" in execution_result:
                return execution_result["payload"]
            else:
                return execution_result
        return method
class Kernel:
    instance = None
    APP_VERSION = "1.0.0" # Keep versioning
    license_tier: str = "architect" # Default to highest tier in Open Core
    is_premium: bool = True # Default to True in Open Core
    DEV_MODE_PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAysqZG2+F82W0TgLHmF3Y
0GRPEZvXvmndTY84N/wA1ljt+JxMBVsmcVTkv8f1TrmFRD19IDzl2Yzb2lgqEbEy
GFxHhudC28leDsVEIp8B+oYWVm8Mh242YKYK8r5DAvr9CPQivnIjZ4BWgKKddMTd
harVxLF2CoSoTs00xWKd6VlXfoW9wdBvoDVifL+hCMepgLLdQQE4HbamPDJ3bpra
pCgcAD5urmVoJEUJdjd+Iic27RBK7jD1dWDO2MASMh/0IyXyM8i7RDymQ88gZier
U0OdWzeCWGyl4EquvR8lj5GNz4vg2f+oEY7h9AIC1f4ARtoihc+apSntqz7nAqa/
sQIDAQAB
-----END PUBLIC KEY-----""" # Keep for dev mode validation
    TIER_HIERARCHY = { # Keep for potential internal logic, but checks are disabled
        "free": 0,
        "builder": 1,
        "creator": 2,
        "architect": 3,
        "enterprise": 4,
    }
    MODULE_CAPABILITY_MAP = { # Keep for potential internal logic, but checks are disabled
        "stable_diffusion_xl_module": "ai_local_models",
        "agent_host": "ai_architect",
        "core_compiler_module": "core_compiler",
        "function_runner_module": "ai_architect",
        "Dynamic Media Stitcher": "video_processing",
        "video_storyboard_stitcher_d5e6": "video_processing",
    }
    class FileSystemProxy:
        def __init__(self, kernel):
            self.kernel = kernel
            self.os_module = os
            self.shutil_module = __import__("shutil")
        def _check_permission(self, caller_module_id: str, required_permission: str):
            permission_manager = self.kernel.get_service(
                "permission_manager_service", is_system_call=True
            )
            if permission_manager:
                 if not permission_manager.check_permission(required_permission):
                     raise PermissionDeniedError(
                        f"Module '{caller_module_id}' does not have the required permission: '{required_permission}'"
                     )
        def read(
            self, file_path, mode="r", encoding="utf-8", caller_module_id: str = None
        ):
            self._check_permission(caller_module_id, "file_system:read")
            with open(file_path, mode, encoding=encoding) as f:
                return f.read()
        def write(
            self,
            file_path,
            data,
            mode="w",
            encoding="utf-8",
            caller_module_id: str = None,
        ):
            self._check_permission(caller_module_id, "file_system:write")
            with open(file_path, mode, encoding=encoding) as f:
                f.write(data)
        def exists(self, path, caller_module_id: str = None):
            self._check_permission(caller_module_id, "file_system:read")
            return self.os_module.path.exists(path)
        def remove(self, path, caller_module_id: str = None):
            self._check_permission(caller_module_id, "file_system:write")
            return self.os_module.remove(path)
        def rmtree(self, path, caller_module_id: str = None):
            self._check_permission(caller_module_id, "file_system:write")
            return self.shutil_module.rmtree(path)
    class NetworkProxy:
        def __init__(self, kernel):
            self.kernel = kernel
            self.requests_module = requests
        def _check_permission(self, caller_module_id: str, required_permission: str):
            permission_manager = self.kernel.get_service(
                "permission_manager_service", is_system_call=True
            )
            if permission_manager:
                if not permission_manager.check_permission(required_permission):
                     raise PermissionDeniedError(
                        f"Module '{caller_module_id}' does not have the required permission: '{required_permission}'"
                     )
        def get(self, url, caller_module_id: str = None, **kwargs):
            self._check_permission(caller_module_id, "network:get")
            return self.requests_module.get(url, **kwargs)
        def post(self, url, caller_module_id: str = None, **kwargs):
            self._check_permission(caller_module_id, "network:post")
            return self.requests_module.post(url, **kwargs)
    def __init__(self, project_root_path: str):
        Kernel.instance = self
        self.project_root_path = "/app/flowork-core"
        self.data_path = "/app/core-data"
        self.base_path = "/app/flowork-core" # (COMMENT) Disesuaikan dengan project_root_path
        dev_mode_base_path = "/app" # Lokasi 'devmode.on' ada di root /app
        self.is_dev_mode = self._validate_dev_mode(dev_mode_base_path)
        self._log_dev_mode_on_init = self.is_dev_mode
        self.services: Dict[str, Any] = {}
        self.startup_complete = False
        self.current_user = None # User identity managed via WebSocket auth
        self.globally_disabled_components = set()
        self.logs_path = os.path.join(self.data_path, "logs")
        self.modules_path = os.path.join(self.project_root_path, "modules")
        self.plugins_path = os.path.join(self.project_root_path, "plugins")
        self.system_plugins_path = os.path.join(
            self.project_root_path, "system_plugins"
        )
        self.widgets_path = os.path.join(self.project_root_path, "widgets")
        self.themes_path = os.path.join(self.project_root_path, "themes")
        self.triggers_path = os.path.join(self.project_root_path, "triggers")
        self.locales_path = os.path.join(self.project_root_path, "locales")
        self.ai_providers_path = os.path.join(self.project_root_path, "ai_providers")
        self.formatters_path = os.path.join(self.project_root_path, "formatters")
        self.tools_path = os.path.join(self.project_root_path, "tools")
        os.makedirs(self.data_path, exist_ok=True)
        os.makedirs(self.logs_path, exist_ok=True)
        self.log_queue = queue.Queue()
        self.cmd_log_queue = queue.Queue()
        self.file_system = self.FileSystemProxy(self)
        self.network = self.NetworkProxy(self)
        self.json_logger = None
        self.dashboard_socketio = None # Used by dashboard_server.py
        self._setup_file_logger()
        if self._log_dev_mode_on_init:
            self.write_to_log("Kernel booted in secure DEVELOPMENT MODE.", "WARN") # English Hardcode
        self._load_services_from_manifest()
    async def restart_application(self):
        """Schedules a graceful restart of the HOST MACHINE."""
        self.write_to_log(
            "OS RESTART signal received. Restarting host machine...", "CRITICAL" # English Hardcode
        )
        await asyncio.sleep(1)
        if sys.platform == "win32":
            os.system("shutdown /r /t 1")
        else:  # Linux & macOS
            os.system("shutdown -r now")
    async def shutdown_application(self):
        """Schedules a graceful shutdown of the HOST MACHINE."""
        self.write_to_log(
            "OS SHUTDOWN signal received. Shutting down host machine...", "CRITICAL" # English Hardcode
        )
        await asyncio.sleep(1)
        if sys.platform == "win32":
            os.system("shutdown /s /t 1")
        else:  # Linux & macOS
            os.system("shutdown -h now")
    def _validate_dev_mode(self, base_path) -> bool:
        dev_mode_file = os.path.join(base_path, "devmode.on")
        if not os.path.exists(dev_mode_file):
            return False
        try:
            with open(dev_mode_file, "r", encoding="utf-8") as f:
                content = f.read().strip()
            if content == self.DEV_MODE_PUBLIC_KEY.strip():
                return True
            else:
                self._log_dev_mode_on_init = True
                print(
                    "[KERNEL-WARN] devmode.on file found, but its content is invalid. DEV MODE WILL NOT ACTIVATE." # English Hardcode
                )
                return False
        except Exception:
            print(
                "[KERNEL-ERROR] Could not read devmode.on file. DEV MODE WILL NOT ACTIVATE." # English Hardcode
            )
            return False
    def get_component_instance(self, component_id: str) -> Any:
        if component_id in self.globally_disabled_components:
            self.write_to_log(
                f"Access to globally disabled component '{component_id}' was blocked.",
                "CRITICAL",
            )
            return None
        module_manager = self.get_service("module_manager_service", is_system_call=True)
        if module_manager and component_id in module_manager.loaded_modules:
            return module_manager.get_instance(component_id)
        plugin_manager = self.get_service("plugin_manager_service", is_system_call=True)
        if plugin_manager and component_id in plugin_manager.loaded_plugins:
            return plugin_manager.get_instance(component_id)
        tools_manager = self.get_service("tools_manager_service", is_system_call=True)
        if tools_manager and component_id in tools_manager.loaded_tools:
            return tools_manager.get_instance(component_id) # Assuming get_instance exists
        self.write_to_log(f"Component '{component_id}' not found in any manager.", "ERROR") # English Hardcode
        return None
    @property
    def loc(self):
        return self.get_service("localization_manager", is_system_call=True)
    @property
    def event_bus(self):
        return self.get_service("event_bus", is_system_call=True)
    def _log_queue_worker(self):
        while True:
            try:
                log_record = self.log_queue.get()
                if self.json_logger:
                    level_upper = log_record.get("level", "INFO").upper()
                    message = log_record.get("message", "")
                    source = log_record.get("source", "Unknown")
                    log_map = {
                        "INFO": self.json_logger.info,
                        "SUCCESS": self.json_logger.info,
                        "WARN": self.json_logger.warning,
                        "ERROR": self.json_logger.error,
                        "CRITICAL": self.json_logger.critical,
                        "DEBUG": self.json_logger.debug,
                        "DETAIL": self.json_logger.debug,
                    }
                    log_function = log_map.get(level_upper, self.json_logger.info)
                    log_function(message, extra={"extra_info": {"source": source}})
                if self.dashboard_socketio:
                    try:
                        self.dashboard_socketio.emit(
                            "new_log", log_record, namespace="/dashboard_events"
                        )
                    except Exception as e_sock:
                        if self.file_logger: self.file_logger.error(f"Failed to emit log to dashboard socket: {e_sock}") # English Hardcode
                if self.file_logger:
                    self.file_logger.info(f"[{log_record.get('level', 'INFO').upper()}] [{log_record.get('source', 'Unknown')}] {log_record.get('message', '')}")
                self.log_queue.task_done()
            except Exception as e:
                if self.file_logger: self.file_logger.error(f"[LOG WORKER ERROR] {e}") # English Hardcode
                else: print(f"[LOG WORKER ERROR] {e}") # English Hardcode
                time.sleep(1) # Prevent tight loop on error
    def _load_services_from_manifest(self):
        manifest_path = os.path.join(self.project_root_path, "flowork_kernel", "services.json")
        self.write_to_log(
            f"Kernel: Loading services from manifest: {manifest_path}", "INFO" # English Hardcode
        )
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                services_manifest = json.load(f)
            essential_order = [
                "integrity_checker_service",
                "license_manager_service", # Must run before permission_manager
                "event_bus",
                "localization_manager",
                "state_manager",
                "permission_manager_service", # Must run after license_manager
                "variable_manager",
                "preset_manager_service",
            ]
            all_service_configs = services_manifest["services"]
            loaded_ids = set()
            for service_id in essential_order:
                service_config = next(
                    (s for s in all_service_configs if s["id"] == service_id), None
                )
                if service_config:
                    self._load_service(service_config)
                    loaded_ids.add(service_id)
                else:
                    self.write_to_log(f"Essential service '{service_id}' not found in manifest.", "WARN") # English Hardcode
            for service_config in all_service_configs:
                if service_config["id"] not in loaded_ids:
                    if service_config.get("COMMENT"):
                        self.write_to_log(f"Skipping commented service: {service_config['id']} - {service_config['COMMENT']}", "INFO") # English Hardcode
                        continue
                    self._load_service(service_config)
            self.write_to_log(
                "Kernel: All services loaded. Creating aliases...", "DEBUG" # English Hardcode
            )
            if "preset_manager_service" in self.services:
                self.services["preset_manager"] = self.services[
                    "preset_manager_service"
                ]
                self.write_to_log(
                    "Alias 'preset_manager' created for 'preset_manager_service'.", # English Hardcode
                    "SUCCESS",
                )
            if "variable_manager" in self.services:
                self.services["variable_manager_service"] = self.services[
                    "variable_manager"
                ]
                self.write_to_log(
                    "Alias 'variable_manager_service' created for 'variable_manager'.", # English Hardcode
                    "SUCCESS",
                )
        except Exception as e:
            import traceback
            self.write_to_log(f"CRITICAL ERROR loading services manifest: {e}\n{traceback.format_exc()}", "CRITICAL") # English Hardcode
            raise RuntimeError(f"Could not load services manifest: {e}") from e
    def _load_service(self, service_config: Dict[str, str]):
        service_id = service_config["id"]
        service_type = service_config.get("type", "class")
        try:
            if service_type == "service_workflow":
                preset_path = service_config.get("preset_path")
                if not preset_path:
                    self.write_to_log(
                        f"Failed to load service workflow '{service_id}': 'preset_path' is missing.", # English Hardcode
                        "ERROR",
                    )
                    return
                self.services[service_id] = ServiceWorkflowProxy(
                    self, service_id, preset_path
                )
            else:
                module_path = service_config["path"]
                class_name = service_config["class"]
                module = importlib.import_module(module_path)
                ServiceClass = getattr(module, class_name)
                self.services[service_id] = ServiceClass(self, service_id)
            self.write_to_log(f"Service '{service_id}' loaded successfully.", "SUCCESS") # English Hardcode
        except Exception as e:
            self.write_to_log(f"Failed to load service '{service_id}': {e}", "ERROR") # English Hardcode
            critical_services = [
                "event_bus", "localization_manager", "integrity_checker_service",
                "license_manager_service", "permission_manager_service",
                "state_manager", "variable_manager", "preset_manager_service",
                "module_manager_service", "startup_service" # StartupService is critical
            ]
            if service_id in critical_services:
                raise RuntimeError(
                    f"Critical service '{service_id}' failed to load." # English Hardcode
                ) from e
    def get_service(self, service_id: str, is_system_call: bool = False) -> Any:
        try:
            service = self.services.get(service_id)
            if not service:
                self.write_to_log(
                    f"Service '{service_id}' requested but not found in loaded services!", # English Hardcode
                    "ERROR",
                )
            return service
        except PermissionDeniedError as e:
            self.write_to_log(
                f"Permission Denied accessing service '{service_id}': {e}", "WARN" # English Hardcode
            )
            raise e
        except Exception as e:
            self.write_to_log(
                f"An unexpected error occurred in get_service for '{service_id}': {e}", # English Hardcode
                "CRITICAL",
            )
            raise e
    async def start_all_services(self):
        self.write_to_log("Kernel: Minimalist bootloader starting...", "INFO") # English Hardcode
        log_worker_thread = threading.Thread(target=self._log_queue_worker, daemon=True)
        log_worker_thread.start()
        self.write_to_log(
            "Kernel: Handing control directly to StartupService...", "INFO" # English Hardcode
        )
        try:
            startup_service = self.get_service("startup_service", is_system_call=True)
            if startup_service:
                result = await startup_service.run_startup_sequence()
                self.write_to_log(
                    f"Startup sequence finished with status: {result}", "SUCCESS" # English Hardcode
                )
            else:
                self.write_to_log(
                    "CRITICAL: StartupService not found! Cannot start application.", # English Hardcode
                    "ERROR",
                )
                raise RuntimeError(
                    "StartupService is essential for application startup and was not found." # English Hardcode
                )
        except Exception as e:
            self.write_to_log(
                f"CRITICAL: Startup sequence failed with an exception: {e}", "ERROR" # English Hardcode
            )
            raise e
    def hot_reload_components(self):
        self.write_to_log("Kernel: Hot reload triggered...", "WARN") # English Hardcode
        for cache_file in [
            "module_index.cache",
            "widget_index.cache",
            "trigger_index.cache",
            "plugin_index.cache", # Add plugin cache if it exists
            "tool_index.cache", # Add tool cache if it exists
        ]:
            cache_path = os.path.join(self.data_path, cache_file)
            if os.path.exists(cache_path):
                try:
                    os.remove(cache_path)
                except OSError as e:
                     self.write_to_log(f"Could not remove cache file {cache_path}: {e}", "WARN") # English Hardcode
        mm = self.get_service("module_manager_service", is_system_call=True)
        if mm: mm.discover_and_load_modules()
        pm = self.get_service("plugin_manager_service", is_system_call=True)
        if pm: pm.discover_and_load_plugins()
        tm = self.get_service("tools_manager_service", is_system_call=True)
        if tm: tm.discover_and_load_tools()
        wm = self.get_service("widget_manager_service", is_system_call=True)
        if wm: wm.discover_and_load_widgets()
        trg_m = self.get_service("trigger_manager_service", is_system_call=True)
        if trg_m: trg_m.discover_and_load_triggers()
        ai_m = self.get_service("ai_provider_manager_service", is_system_call=True)
        if ai_m: ai_m.discover_and_load_endpoints()
        loc_m = self.get_service("localization_manager", is_system_call=True)
        if loc_m: loc_m.load_all_languages()
        if self.event_bus:
            self.event_bus.publish("COMPONENT_LIST_CHANGED", {"status": "hot_reloaded"}) # English Hardcode
        self.write_to_log("Kernel: Hot reload finished.", "SUCCESS") # English Hardcode
    async def stop_all_services(self):
        self.write_to_log("Kernel: Stopping all services...", "INFO") # English Hardcode
        for service_id, service_instance in reversed(list(self.services.items())):
            if hasattr(service_instance, "stop") and callable(
                getattr(service_instance, "stop")
            ):
                try:
                    if not isinstance(service_instance, ServiceWorkflowProxy):
                        if asyncio.iscoroutinefunction(service_instance.stop):
                            await service_instance.stop()
                        else:
                            service_instance.stop()
                        self.write_to_log(f"Service '{service_id}' stopped.", "DEBUG") # English Hardcode
                except Exception as e:
                    self.write_to_log(
                        f"Error stopping service '{service_id}': {e}", "ERROR" # English Hardcode
                    )
        for thread in threading.enumerate():
            if thread != threading.main_thread() and hasattr(thread, 'daemon') and thread.daemon:
                try:
                    thread.join(timeout=1.0)
                except RuntimeError:
                    pass # Ignore if thread already finished
    def is_premium_user(self) -> bool:
        return True
    def is_monetization_active(self) -> bool:
        return False
    def is_tier_sufficient(self, required_tier: str) -> bool:
        return True
    def activate_license_online(self, full_license_content: dict):
        self.logger("Online license activation is disabled in Open Core mode.", "WARN") # English Hardcode
        return False, "Online activation disabled." # English Hardcode
    def deactivate_license_on_server(self):
        self.logger("Online license deactivation is disabled in Open Core mode.", "WARN") # English Hardcode
        return False, "Online deactivation disabled." # English Hardcode
    def _setup_file_logger(self):
        self.json_logger = logging.getLogger("FloworkJsonLogger")
        self.json_logger.setLevel(logging.DEBUG)
        if self.json_logger.hasHandlers():
            self.json_logger.handlers.clear()
        json_handler = logging.StreamHandler(sys.stdout) # Log JSON to stdout
        json_handler.setFormatter(JsonFormatter())
        self.json_logger.addHandler(json_handler)
        self.json_logger.propagate = False # Prevent propagation to root logger
        self.file_logger = logging.getLogger("FloworkFileLogger")
        self.file_logger.setLevel(logging.DEBUG)
        log_file_path = os.path.join(
            self.logs_path,
            f"flowork_debug_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
        )
        if not self.file_logger.handlers:
            file_handler = logging.FileHandler(log_file_path, encoding="utf-8")
            formatter = logging.Formatter(
                "%(asctime)s [%(levelname)s] [%(name)s] %(message)s", datefmt="%H:%M:%S"
            )
            file_handler.setFormatter(formatter)
            self.file_logger.addHandler(file_handler)
            self.file_logger.propagate = False # Prevent propagation
    def write_to_log(self, message, level="INFO", source="Kernel"):
        log_record = {"message": str(message), "level": level.upper(), "source": source}
        self.log_queue.put(log_record)
    def request_manual_approval(
        self, module_id: str, message: str, callback_func: Callable
    ):
        log_message = f"Manual approval requested by module '{module_id}': {message}"
        self.write_to_log(log_message, "WARN") # English Hardcode
        if self.event_bus:
            event_data = {
                "module_id": module_id,
                "message": message,
                "workflow_context_id": self.get_service(
                    "workflow_executor_service"
                ).get_current_context_id(),
            }
            self.event_bus.publish(
                "MANUAL_APPROVAL_REQUESTED", event_data, publisher_id=module_id
            )
        else:
            self.write_to_log("EventBus not available, cannot broadcast approval request.", "ERROR") # English Hardcode
