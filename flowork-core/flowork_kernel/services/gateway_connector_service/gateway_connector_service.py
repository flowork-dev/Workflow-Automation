#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\services\gateway_connector_service\gateway_connector_service.py JUMLAH BARIS 1043 
#######################################################################

import socketio
import threading
import time
import os
import json
import random
import psutil
import requests
import traceback # <-- PENAMBAHAN KODE
from ..base_service import BaseService
from web3.auto import w3
from eth_account.messages import encode_defunct
import asyncio
from flowork_kernel.kernel import Kernel
from flowork_kernel.exceptions import PermissionDeniedError # (PENAMBAHAN KODE)
import uuid # (PENAMBAHAN KODE)
try:
    from get_ip import get_local_ip # Try to import from root
except ImportError:
    from ...get_ip import get_local_ip # Fallback for relative path
class GatewayConnectorService(BaseService):
    """
    (REMASTERED V5.0) Service ini sekarang juga bertanggung jawab untuk
    mengelola daftar otorisasi user (siapa saja yang boleh mengakses engine ini).
    (PERBAIKAN FASE 4) Sekarang menjadi SATU-SATUNYA entrypoint WebSocket.
    Mendengarkan event 'execute_rpc_from_gui' dan menjalankan logika auth 3-lapis.
    """
    def __init__(self, kernel, service_id):
        super().__init__(kernel, service_id)
        self.sio = None
        self._config_lock = threading.Lock()
        self.authorized_addresses = set()
        self._auth_list_lock = threading.Lock()
        self.is_auth_list_fetched = False # Flag untuk startup
        env_token = os.getenv("FLOWORK_ENGINE_TOKEN")
        conf_token = None
        docker_conf_path = os.path.join(self.kernel.data_path, "docker-engine.conf")
        if os.path.exists(docker_conf_path):
            self.logger("Found docker-engine.conf, loading it for config.", "INFO") # English log
            self.config = self._load_config(is_docker=True)
            conf_token = self.config.get("engine_token")
            if not self.config.get("gateway_api_url"):
                fallback_config = self._load_config(is_docker=False)
                self.config.setdefault("gateway_api_url", fallback_config.get("gateway_api_url", "https://api.flowork.cloud"))
                self.config.setdefault("gateway_webapp_url", fallback_config.get("gateway_webapp_url", "https://flowork.cloud"))
        else:
            self.logger("docker-engine.conf not found, using engine.conf.", "INFO") # English log
            self.config = self._load_config(is_docker=False)
            conf_token = self.config.get("engine_token")
        if env_token:
            self.engine_token = env_token
            self.logger("Using Engine Token from FLOWORK_ENGINE_TOKEN environment variable.", "SUCCESS") # English log
        elif conf_token:
            self.engine_token = conf_token
            self.logger("Using Engine Token from config file (docker-engine.conf / engine.conf).", "INFO") # English log
        else:
            self.engine_token = None
            self.logger("CRITICAL: No Engine Token found in environment variables or config files.", "CRITICAL") # English log
        if not self.config:
            self.config = {
                "gateway_api_url": "https://api.flowork.cloud",
                "gateway_webapp_url": "https://flowork.cloud",
            }
        self.gateway_url = self.config.get("gateway_api_url", "https://api.flowork.cloud")
        local_ip = get_local_ip()
        port = int(os.getenv("CORE_API_PORT", self.loc.get_setting("webhook_port", 8989) if self.loc else 8989))
        self.core_server_url = f"http://{local_ip}:{port}"
        self.is_connected_and_authed = False
        self.ping_thread = None
        self.event_bus = self.kernel.get_service("event_bus")
        self.stop_ping_event = threading.Event()
        self.process = psutil.Process(os.getpid())
        self.api_server_service = None # Akan diisi di start()
        self.executor = None
        self.preset_manager = None
        self.module_manager = None
        self.plugin_manager = None
        self.tools_manager = None
        self.trigger_manager = None
        self.ai_provider_manager = None
        self.variable_manager = None
        self.settings_manager = None
        self.dataset_manager = None
        self.training_manager = None
        self.prompt_manager = None
        self.session_job_ids = {} # Ganti set global dengan dict per user: { 'user_id': set() }
        self._session_lock = threading.Lock()
    def _load_dependencies_for_rpc(self):
        """Memuat semua service yang dibutuhkan oleh handler RPC."""
        self.executor = self.kernel.get_service("workflow_executor_service")
        self.preset_manager = self.kernel.get_service("preset_manager_service")
        self.module_manager = self.kernel.get_service("module_manager_service")
        self.plugin_manager = self.kernel.get_service("plugin_manager_service")
        self.tools_manager = self.kernel.get_service("tools_manager_service")
        self.trigger_manager = self.kernel.get_service("trigger_manager_service")
        self.ai_provider_manager = self.kernel.get_service("ai_provider_manager_service")
        self.variable_manager = self.kernel.get_service("variable_manager")
        self.settings_manager = self.kernel.get_service("localization_manager")
        self.dataset_manager = self.kernel.get_service("dataset_manager_service")
        self.training_manager = self.kernel.get_service("ai_training_service")
        self.prompt_manager = self.kernel.get_service("prompt_manager_service")
        self.logger("All dependencies for RPC handler loaded.", "INFO") # English Hardcode
    def fetch_and_update_auth_list(self) -> bool:
        """
        Saat startup atau saat ada notifikasi, hubungi Gateway untuk mengambil DAFTAR
        alamat publik (User ID) yang diotorisasi mengakses engine ini.
        """
        self.logger("[AuthZ] Attempting to fetch/refresh engine authorization info from Gateway...", "INFO") # English Hardcode
        try:
            gateway_url = self.config.get("gateway_api_url")
            if not gateway_url:
                 gateway_url = os.getenv("GATEWAY_API_URL", "http://gateway:8000") # English Hardcode
            engine_token = self.engine_token
            if not gateway_url or not engine_token or "PLEASE_REPLACE_ME" in engine_token: # English Hardcode
                self.logger("[AuthZ] CRITICAL: Gateway URL or Engine Token is not configured. Cannot fetch auth info.", "CRITICAL") # English Hardcode
                self.is_auth_list_fetched = True # Tandai tetap selesai agar server tidak hang
                return False
            target_url = f"{gateway_url}/api/v1/engine/get-engine-auth-info"
            headers = { "X-Engine-Token": engine_token }
            self.logger(f"[AuthZ] Contacting Gateway at: {target_url}", "DEBUG") # English Log (Debug)
            response = requests.get(target_url, headers=headers, timeout=15)
            if response.status_code == 200:
                data = response.json()
                addresses = data.get("authorized_addresses")
                if addresses and isinstance(addresses, list):
                    with self._auth_list_lock:
                        self.authorized_addresses.clear()
                        for addr in addresses:
                            if isinstance(addr, str) and addr.startswith('0x'):
                                self.authorized_addresses.add(addr.lower())
                    if not self.authorized_addresses:
                        self.logger(f"[AuthZ] CRITICAL: Gateway returned an empty or invalid authorized list.", "CRITICAL") # English Hardcode
                        self.is_auth_list_fetched = True # Tandai selesai
                        return False
                    self.logger(f"[AuthZ] SUCCESS: Engine authorization list refreshed. Authorized users count: {len(self.authorized_addresses)}", "SUCCESS") # English Hardcode
                    self.logger(f"[AuthZ] Sample Authorized: {list(self.authorized_addresses)[:3]}", "DEBUG") # English Hardcode
                    self.is_auth_list_fetched = True # Tandai selesai
                    return True
                else:
                    self.logger(f"[AuthZ] CRITICAL: Gateway response missing or invalid 'authorized_addresses' list.", "CRITICAL") # English Hardcode
            else:
                self.logger(f"[AuthZ] CRITICAL: Gateway rejected request. Status: {response.status_code}, Body: {response.text}", "CRITICAL") # English Hardcode
        except requests.exceptions.Timeout:
            self.logger(f"[AuthZ] CRITICAL: Timeout connecting to Gateway at {gateway_url}. Cannot fetch auth info.", "CRITICAL") # English Hardcode
        except requests.exceptions.RequestException as e:
            self.logger(f"[AuthZ] CRITICAL: Failed to connect to Gateway. Error: {e}", "CRITICAL") # English Hardcode
        except Exception as e:
            self.logger(f"[AuthZ] CRITICAL: Unexpected error fetching auth info: {e}", "CRITICAL") # English Hardcode
            self.logger(traceback.format_exc(), "DEBUG")
        self.is_auth_list_fetched = True # Tandai selesai (meskipun gagal) agar server tidak hang
        return False
    def is_user_authorized(self, public_address: str) -> bool:
        """
        Memeriksa (thread-safe) apakah suatu public address ada di dalam daftar yang diizinkan.
        """
        if not public_address:
            return False
        with self._auth_list_lock:
            return public_address.lower() in self.authorized_addresses
    def on_force_refresh_auth_list(self, data=None):
        """
        Handler saat Gateway mengirim event 'force_refresh_auth_list' via WebSocket.
        """
        self.logger("Received 'force_refresh_auth_list' signal from Gateway. Re-fetching...", "WARN") # English Log
        threading.Thread(target=self.fetch_and_update_auth_list, daemon=True).start()
    def force_reconnect(self):
        if self.sio and self.sio.connected:
            self.logger(
                "Received force reconnect command. Resending authentication token...", # English log
                "WARN",
            )
            engine_id_from_env = os.getenv("FLOWORK_ENGINE_ID")
            auth_payload = {"token": self.engine_token, "engine_id": engine_id_from_env} # English Hardcode
            try:
                self.sio.emit("auth", auth_payload, namespace="/engine-socket")
            except Exception as e:
                self.logger(f"Failed to resend auth token: {e}", "ERROR") # English log
        else:
            self.logger(
                "Received force reconnect command. Attempting to reconnect...", "INFO" # English log
            )
            self.connect()
        return {"status": "success", "message": "Reconnect initiated."} # English log
    def update_engine_token(self, new_token: str):
        with self._config_lock:
            self.logger("Attempting to update Engine Token...", "WARN") # English log
            docker_conf_path = os.path.join(self.kernel.data_path, "docker-engine.conf")
            conf_path_to_update = docker_conf_path if os.path.exists(docker_conf_path) else os.path.join(self.kernel.data_path, "engine.conf")
            self.logger("Please also update FLOWORK_ENGINE_TOKEN in your main .env file for persistence.", "WARN") # English log
            try:
                current_config = {}
                if os.path.exists(conf_path_to_update):
                    with open(conf_path_to_update, "r", encoding="utf-8") as f:
                        current_config = json.load(f)
                current_config["engine_token"] = new_token
                with open(conf_path_to_update, "w", encoding="utf-8") as f:
                    json.dump(current_config, f, indent=4)
                self.engine_token = new_token
                self.logger(f"Engine Token successfully updated in {os.path.basename(conf_path_to_update)} and config reloaded.", "SUCCESS") # English log
                self.fetch_and_update_auth_list()
                self.force_reconnect()
                return {
                    "status": "success",
                    "message": "Token updated and reconnect initiated.", # English log
                }
            except Exception as e:
                self.logger(f"Failed to update {os.path.basename(conf_path_to_update)}: {e}", "CRITICAL") # English log
                return {"status": "error", "message": str(e)}
    def _load_config(self, is_docker=False):
        with self._config_lock:
            return self._load_config_unsafe(is_docker)
    def _load_config_unsafe(self, is_docker=False):
        if is_docker:
            config_path = os.path.join(self.kernel.data_path, "docker-engine.conf")
            if not os.path.exists(config_path):
                 self.logger("File 'docker-engine.conf' not found in data volume.", "WARN") # English log
                 return {} # Kembalikan dict kosong jika tidak ada
        else:
            config_path = os.path.join(self.kernel.data_path, "engine.conf")
            if not os.path.exists(config_path):
                self.logger(
                    "File 'engine.conf' not found. Creating default file...", "WARN" # English log
                )
                default_config = {
                    "gateway_api_url": "https://api.flowork.cloud", # Default URL public
                    "gateway_webapp_url": "https://flowork.cloud",
                    "engine_token": "PLEASE_REPLACE_ME_WITH_TOKEN_FROM_WEBSITE", # English log
                }
                try:
                    with open(config_path, "w", encoding="utf-8") as f:
                        json.dump(default_config, f, indent=4)
                    return default_config
                except Exception as e:
                    self.logger(f"Failed to create default engine.conf: {e}", "CRITICAL") # English log
                    return {}
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            self.logger(f"Failed to read config file {os.path.basename(config_path)}: {e}", "CRITICAL") # English log
            return {}
    def _ping_worker(self):
        while not self.stop_ping_event.is_set():
            if self.is_connected_and_authed:
                try:
                    self.logger("Sending ping and vitals to Gateway...", "DEBUG") # English log
                    vitals_payload = {
                        "cpu_percent": self.process.cpu_percent(interval=0.1),
                        "ram_percent": self.process.memory_percent(),
                        "ram_rss_mb": self.process.memory_info().rss / (1024 * 1024),
                        "kernel_version": self.kernel.APP_VERSION,
                    }
                    self.sio.emit(
                        "engine_vitals_update",
                        vitals_payload,
                        namespace="/engine-socket",
                    )
                except Exception as e:
                    self.logger(f"Failed to send ping/vitals: {e}", "WARN") # English log
            self.stop_ping_event.wait(5) # Tunggu 5 detik sebelum ping lagi
        self.logger("Ping worker stopped.", "INFO") # English log
    def _send_rpc_response_to_gateway(self, payload_dict):
        """Mengirim respons RPC kembali ke Gateway."""
        if self.is_connected_and_authed and self.sio:
            try:
                if 'content' in payload_dict and isinstance(payload_dict['content'], str):
                    try:
                        parsed_content = json.loads(payload_dict['content'])
                        payload_dict['content'] = parsed_content
                    except json.JSONDecodeError:
                        pass # Biarkan sebagai string jika bukan JSON
                self.sio.emit(
                    "rpc_response_from_engine", # Event baru
                    payload_dict,
                    namespace="/engine-socket"
                )
            except Exception as e:
                self.logger(f"Failed to send RPC response (type: {payload_dict.get('type')}) to Gateway: {e}", "ERROR") # English log
    def _handle_internal_event(self, event_name, event_data):
        """
        Menangkap event bus internal dan mengirimkannya sebagai
        respons RPC 'catch-all' ke Gateway.
        """
        event_user_context = event_data.get("user_context")
        event_user_id = event_user_context.get("id") if isinstance(event_user_context, dict) else None
        if not event_user_id:
            return
        event_job_id = event_data.get("job_id") or event_data.get("workflow_context_id")
        user_job_set = self._get_job_id_set_for_user(event_user_id)
        job_specific_events = [
            "SHOW_DEBUG_POPUP", "WORKFLOW_JOB_STATUS_UPDATE", "NODE_EXECUTION_METRIC", # English Hardcode
            "WORKFLOW_LOG_ENTRY", "MANUAL_APPROVAL_REQUESTED", "CONNECTION_STATUS_UPDATE" # English Hardcode
        ]
        if event_name in job_specific_events and event_job_id not in user_job_set:
            self.logger(f"EventBus: Ignoring event '{event_name}' for job '{event_job_id}' (not tracked by user '{event_user_id}').", "DEBUG") # English Hardcode
            return
        payload_to_gui = event_data.copy()
        payload_type_gui = None
        if event_name == "SHOW_DEBUG_POPUP":
            payload_type_gui = "SHOW_DEBUG_POPUP" # English Hardcode
        elif event_name == "WORKFLOW_JOB_STATUS_UPDATE":
            payload_type_gui = "workflow_status_update" # English Hardcode
        elif event_name == "NODE_EXECUTION_METRIC":
            payload_type_gui = "NODE_EXECUTION_METRIC" # English Hardcode
        elif event_name == "CONNECTION_STATUS_UPDATE":
            payload_type_gui = "CONNECTION_STATUS_UPDATE" # English Hardcode
        elif event_name == "WORKFLOW_LOG_ENTRY":
            payload_type_gui = "log" # English Hardcode
        elif event_name == "MANUAL_APPROVAL_REQUESTED":
             payload_type_gui = "MANUAL_APPROVAL_REQUESTED" # English Hardcode
        elif event_name == "TRAINING_JOB_STATUS_UPDATE":
             payload_type_gui = "training_job_status_update" # English Hardcode
             payload_to_gui["status"] = payload_to_gui.pop("job_status", {})
        if payload_type_gui:
            payload_to_gui["type"] = payload_type_gui
            self._send_rpc_response_to_gateway(payload_to_gui)
        else:
            payload_to_gui["type"] = "generic_event" # English Hardcode
            payload_to_gui["original_event_name"] = event_name
            self._send_rpc_response_to_gateway(payload_to_gui)
    def _sync_kill_switch_list(self):
        self.logger("Syncing global kill switch list from Gateway...", "INFO") # English log
        try:
            target_url = f"{self.gateway_url}/api/v1/system/disabled-components"
            api_key = os.getenv("GATEWAY_SECRET_TOKEN")
            headers = {"X-API-Key": api_key} if api_key else {}
            response = requests.get(target_url, headers=headers, timeout=10)
            response.raise_for_status()
            disabled_ids = response.json()
            if isinstance(disabled_ids, list):
                self.kernel.set_globally_disabled_components(disabled_ids)
            else:
                self.logger(
                    "Received invalid data format for kill switch list.", "ERROR" # English log
                )
        except requests.exceptions.RequestException as e:
            self.logger(f"Failed to sync kill switch list from Gateway: {e}", "ERROR") # English log
        except Exception as e:
            self.logger(
                f"An unexpected error occurred during kill switch sync: {e}", "ERROR" # English log
            )
    def connect(self):
        if not self.sio:
            self.logger("SocketIO client not initialized. Cannot connect.", "ERROR") # English log
            return
        if self.sio.connected:
            self.logger("Already connected to Gateway.", "DEBUG") # English log
            return
        try:
            connect_target_url = self.gateway_url or self.config.get("gateway_api_url", "https://api.flowork.cloud")
            self.logger(
                f"Attempting to connect to Gateway at {connect_target_url}...", "INFO" # English log
            )
            self.sio.connect(
                connect_target_url,
                namespaces=["/engine-socket"],
                transports=["websocket"],
            )
        except socketio.exceptions.ConnectionError as e:
            self.logger(f"Connection to Gateway failed: {e}", "ERROR") # English log
        except Exception as e:
             self.logger(f"Unexpected error during connection attempt: {e}", "ERROR") # English log
    def start(self):
        self.api_server_service = self.kernel.get_service("api_server_service")
        if not self.api_server_service:
            self.logger("ApiServerService not found, job status forwarding to local dashboard might fail.", "WARN") # English log
        if not self.engine_token or "PLEASE_REPLACE_ME" in self.engine_token: # English log
            self.logger(
                "Engine Token is not configured correctly. Authentication will likely fail.", "WARN" # English log
            )
        self._load_dependencies_for_rpc()
        if self.event_bus:
            events_to_forward = [
                "WORKFLOW_LOG_ENTRY",
                "NODE_EXECUTION_METRIC",
                "CONNECTION_STATUS_UPDATE",
                "DASHBOARD_ACTIVE_JOBS_UPDATE",
                "SHOW_DEBUG_POPUP",
                "WORKFLOW_JOB_STATUS_UPDATE",
                "MANUAL_APPROVAL_REQUESTED",
                "TRAINING_JOB_STATUS_UPDATE"
            ]
            for event_name in events_to_forward:
                self.event_bus.subscribe(
                    event_name,
                    f"GatewayForwarder_{event_name}",
                    lambda data, name=event_name: self._handle_internal_event(name, data),
                )
            self.logger(
                "GatewayConnector is now listening to internal events for forwarding.", # English log
                "INFO",
            )
        self.sio = socketio.Client(
            logger=False, # Set True untuk debug socketio
            engineio_logger=False, # Set True untuk debug engineio
            reconnection=True,
            reconnection_attempts=0, # Coba reconnect selamanya
            reconnection_delay=5,
            reconnection_delay_max=300,
            randomization_factor=0.5,
        )
        self.sio.on("connect", self.on_connect, namespace="/engine-socket")
        self.sio.on("disconnect", self.on_disconnect, namespace="/engine-socket")
        self.sio.on("auth_success", self.on_auth_success, namespace="/engine-socket")
        self.sio.on("auth_failed", self.on_auth_failed, namespace="/engine-socket")
        self.sio.on(
            "execute_rpc_from_gui",
            self.on_execute_rpc_from_gui,
            namespace="/engine-socket"
        )
        self.sio.on(
            "trigger_backup", self.on_trigger_backup, namespace="/engine-socket"
        )
        self.sio.on(
            "trigger_restore", self.on_trigger_restore, namespace="/engine-socket"
        )
        self.sio.on(
            "force_sync_kill_switch",
            self.on_force_sync_kill_switch,
            namespace="/engine-socket",
        )
        self.sio.on(
            "force_refresh_auth_list",
            self.on_force_refresh_auth_list,
            namespace="/engine-socket"
        )
        self.logger("Fetching initial authorization list...", "INFO") # English Log
        self.fetch_and_update_auth_list() # Lakukan fetch SYNC saat startup
        self.connect()
    def _get_job_id_set_for_user(self, user_id):
        with self._session_lock:
            if user_id not in self.session_job_ids:
                self.session_job_ids[user_id] = set()
            return self.session_job_ids[user_id]
    def _create_async_install_callback(self, component_type, operation_type, user_id):
        """
        Factory to create a thread-safe callback for component operations.
        (Diambil dari local_server.py)
        """
        def on_complete_from_thread(component_id, success, message):
            self.logger(f"Component operation '{operation_type}' for {component_type} '{component_id}' finished. Success: {success}", "INFO") # English Log
            is_installed_state = False
            if operation_type == 'install' and success: # English Hardcode
                is_installed_state = True
            elif operation_type == 'uninstall' and success: # English Hardcode
                is_installed_state = False
            elif operation_type == 'install' and not success: # English Hardcode
                is_installed_state = False
            elif operation_type == 'uninstall' and not success: # English Hardcode
                manager_to_check = None
                if component_type == 'modules': manager_to_check = self.module_manager
                elif component_type == 'plugins': manager_to_check = self.plugin_manager
                elif component_type == 'tools': manager_to_check = self.tools_manager
                elif component_type == 'triggers': manager_to_check = self.trigger_manager
                if manager_to_check:
                    loaded_map = getattr(manager_to_check, f"loaded_{component_type}", {})
                    component_path = loaded_map.get(component_id, {}).get('path')
                    if component_path:
                         install_marker_path = os.path.join(component_path, ".installed") # English Hardcode
                         is_installed_state = os.path.exists(install_marker_path)
                else:
                     is_installed_state = True # Assume still installed if we can't check
            payload_dict = {
                "type": "component_install_status", # English Hardcode
                "component_id": component_id,
                "component_type": component_type,
                "operation": operation_type,
                "success": success,
                "message": message,
                "is_installed": is_installed_state,
                "user_context": {"id": user_id} # (PENAMBAHAN KODE) Sertakan user context
            }
            self._handle_internal_event("COMPONENT_INSTALL_STATUS", payload_dict)
        return on_complete_from_thread
    def _list_safe_directory(self, req_path, user_id):
        """List isi direktori dengan aman, hanya dalam safe roots."""
        kernel = Kernel.instance
        safe_roots = [os.path.abspath(kernel.project_root_path)]
        host_mapped_paths = [
            "/host_desktop", "/host_documents", "/host_videos", "/host_music", "/host_pictures", # English Hardcode
        ]
        for path in host_mapped_paths:
            abs_path = os.path.abspath(path)
            if os.path.isdir(abs_path):
                roots.append(abs_path)
        browseable_paths_config = os.path.join(kernel.data_path, "browseable_paths.json")
        try:
            if os.path.exists(browseable_paths_config):
                with open(browseable_paths_config, "r", encoding="utf-8") as f:
                    user_defined_paths = json.load(f)
                    if isinstance(user_defined_paths, list):
                        for path in user_defined_paths:
                            if os.path.isdir(path):
                                roots.append(os.path.abspath(path))
        except Exception as e:
            self.logger(f"Could not load or parse 'browseable_paths.json': {e}", "WARN", source="GatewayConnectorRPC") # English Hardcode
        if PSUTIL_AVAILABLE:
            try:
                for partition in psutil.disk_partitions(all=False):
                     mountpoint = os.path.abspath(partition.mountpoint)
                     if mountpoint.startswith(('/proc', '/dev', '/sys', '/run', '/var/lib/docker')): # English Hardcode
                         continue
                     if os.path.isdir(mountpoint):
                         roots.append(mountpoint)
            except Exception as e:
                self.logger(f"Error listing partitions with psutil: {e}", "WARN", source="GatewayConnectorRPC") # English Hardcode
        unique_roots = sorted(list(set(roots)))
        if not req_path:
             drive_items = []
             host_mapped_names = {
                 "/host_desktop": "My Desktop", # English Hardcode
                 "/host_documents": "My Documents", # English Hardcode
                 "/host_videos": "My Videos", # English Hardcode
                 "/host_music": "My Music", # English Hardcode
                 "/host_pictures": "My Pictures", # English Hardcode
             }
             for root in unique_roots:
                 abs_root = os.path.abspath(root)
                 if not os.path.isdir(abs_root):
                     continue
                 name = host_mapped_names.get(abs_root)
                 if not name:
                     if abs_root == os.path.abspath(kernel.project_root_path):
                         name = "Flowork Project (Container)" # English Hardcode
                     elif abs_root == "/":
                         name = "Container Root ( / )" # English Hardcode
                     elif abs_root == "/app":
                         name = "Container App ( /app )" # English Hardcode
                     else:
                         name = os.path.basename(abs_root)
                         if not name: name = abs_root
                 drive_items.append({
                     "name": name,
                     "type": "drive", # English Hardcode
                     "path": abs_root.replace(os.sep, "/")
                 })
             unique_drive_items = {item['path']: item for item in drive_items}.values()
             return sorted(list(unique_drive_items), key=lambda x: x['name'])
        target_path = os.path.abspath(req_path)
        target_path = os.path.normpath(target_path)
        is_safe = False
        for root in unique_roots:
            norm_root = os.path.normpath(root)
            if target_path == norm_root or target_path.startswith(norm_root + os.sep):
                is_safe = True
                break
        if not is_safe:
            raise PermissionError("Access to the requested path is forbidden.") # English Hardcode
        if not os.path.isdir(target_path):
            raise FileNotFoundError(f"Path is not a valid directory: {target_path}") # English Hardcode
        items = []
        try:
            for item_name in sorted(os.listdir(target_path), key=lambda s: s.lower()):
                item_path = os.path.join(target_path, item_name)
                try:
                    is_dir = os.path.isdir(item_path)
                    items.append({
                        "name": item_name,
                        "type": "directory" if is_dir else "file", # English Hardcode
                        "path": os.path.abspath(item_path).replace(os.sep, "/")
                    })
                except OSError:
                    continue
        except OSError as e:
            raise PermissionError(f"Cannot access directory: {e}") # English Hardcode
        return items
    def on_execute_rpc_from_gui(self, data):
        """
        Menerima pesan RPC yang diteruskan oleh Gateway dari GUI.
        Ini adalah pengganti local_server.py
        """
        session_info = engine_session_map.get(request.sid)
        if not session_info:
             self.logger("[RPC Auth] Ignored RPC: Message from unauthed engine session.", "WARN") # English Hardcode
             return # Diam-diam abaikan
        my_engine_id = os.getenv("FLOWORK_ENGINE_ID")
        try:
            auth_payload = data.get('auth')
            main_payload = data.get('payload')
            if not auth_payload or not main_payload:
                raise ValueError("Auth or main payload missing.") # English Hardcode
            message_to_verify_str = auth_payload.get('message')
            signature_str = auth_payload.get('signature')
            address_str = auth_payload.get('address')
            if not message_to_verify_str or not signature_str or not address_str:
                raise ValueError("Incomplete auth payload fields.") # English Hardcode
            message_to_verify = encode_defunct(text=message_to_verify_str)
            recovered_address = w3.eth.account.recover_message(
                message_to_verify, signature=signature_str
            )
            if recovered_address.lower() != address_str.lower():
                raise ValueError(f"Invalid signature. Recovered {recovered_address} != {address_str}") # English Hardcode
            if not self.is_user_authorized(recovered_address.lower()):
                raise PermissionError(f"User {recovered_address} is NOT authorized for this engine.") # English Hardcode
            authed_user_id = recovered_address.lower() # Ini adalah public address
            self.kernel.current_user = {"id": authed_user_id} # Set user di Kernel
            payload_type = main_payload.get('type')
            self.logger(f"[RPC Exec] Auth success. User {authed_user_id[:8]}... executing type: {payload_type}", "INFO") # English Hardcode
            threading.Thread(
                target=self._route_rpc_message_threadsafe,
                args=(payload_type, main_payload, authed_user_id),
                daemon=True
            ).start()
        except Exception as e:
            self.logger(f"[RPC Auth] FAILED: {e}", "ERROR") # English Hardcode
            self._send_rpc_response_to_gateway({"type": "error", "message": str(e)}) # English Hardcode
    def _route_rpc_message_threadsafe(self, payload_type, main_payload, authed_user_id):
        """
        Memproses pesan yang sudah diautentikasi dan mengembalikannya
        payload respons (atau None jika tidak ada balasan langsung).
        (Ini adalah logika 'if/elif' dari local_server.py)
        """
        response_payload = None
        user_context = {'id': authed_user_id}
        try:
            if payload_type == 'execute_workflow':
                if self.executor:
                    job_id = main_payload.get('job_id')
                    if not job_id:
                         job_id = f"job_{uuid.uuid4()}" # Buat job_id jika tidak ada
                    self._get_job_id_set_for_user(authed_user_id).add(job_id)
                    def rpc_workflow_logger(message, level="INFO", source="Executor"): # English Hardcode
                        log_payload = {
                            "type": "log", # English Hardcode
                            "level": level.upper(),
                            "source": source,
                            "message": message,
                            "user_context": user_context,
                            "workflow_context_id": job_id
                        }
                        self._send_rpc_response_to_gateway(log_payload)
                    workflow_data_from_gui = main_payload.get('workflow_data', {})
                    global_loop_config_from_gui = workflow_data_from_gui.get("global_loop_config")
                    self.executor.execute_workflow_synchronous(
                        nodes={node["id"]: node for node in workflow_data_from_gui.get("nodes", [])},
                        connections={conn["id"]: conn for conn in workflow_data_from_gui.get("connections", [])},
                        initial_payload=main_payload.get('initial_payload', {}),
                        logger=rpc_workflow_logger,
                        status_updater=None,
                        highlighter=None,
                        workflow_context_id=job_id,
                        job_status_updater=None, # (COMMENT) Status update ditangani oleh event bus
                        user_context=user_context,
                        preset_name=main_payload.get('preset_name'),
                        mode=main_payload.get('mode', 'EXECUTE'),
                        global_loop_config=global_loop_config_from_gui,
                    )
                    response_payload = None
                else:
                    response_payload = {"type": "error", "message": "WorkflowExecutorService not available."} # English Hardcode
            elif payload_type == 'execute_standalone_node': # English Hardcode
                if self.executor:
                    job_id = main_payload.get('job_id')
                    if not job_id:
                         job_id = f"job_{uuid.uuid4()}"
                    self._get_job_id_set_for_user(authed_user_id).add(job_id)
                    self.executor.execute_standalone_node(
                        node_data=main_payload.get('node_data'),
                        job_id=job_id,
                        user_context=user_context,
                        mode=main_payload.get('mode', 'EXECUTE')
                    )
                    response_payload = {"type": "status_response", "status": "Standalone execution started."} # English Hardcode
                else:
                    response_payload = {"type": "error", "message": "WorkflowExecutorService not available."} # English Hardcode
            elif payload_type == 'stop_workflow': # English Hardcode
                if self.executor: self.executor.stop_execution()
                response_payload = {"type": "status_response", "status": "Stop signal sent"} # English Hardcode
            elif payload_type == 'pause_workflow': # English Hardcode
                if self.executor: self.executor.pause_execution()
                response_payload = {"type": "status_response", "status": "Pause signal sent"} # English Hardcode
            elif payload_type == 'resume_workflow': # English Hardcode
                if self.executor: self.executor.resume_execution()
                response_payload = {"type": "status_response", "status": "Resume signal sent"} # English Hardcode
            elif payload_type == 'request_drives': # English Hardcode
                drive_items = self._list_safe_directory(None, authed_user_id)
                response_payload = {"type": "drives_list_response", "drives": drive_items} # English Hardcode
            elif payload_type == 'request_directory_list': # English Hardcode
                path_to_list = main_payload.get('path')
                dir_items = self._list_safe_directory(path_to_list, authed_user_id)
                response_payload = {"type": "directory_list_response", "path": path_to_list, "items": dir_items} # English Hardcode
            elif payload_type == 'install_component': # English Hardcode
                comp_type = main_payload.get('component_type')
                comp_id = main_payload.get('component_id')
                manager = None
                if comp_type == 'modules': manager = self.module_manager
                elif comp_type == 'plugins': manager = self.plugin_manager
                elif comp_type == 'tools': manager = self.tools_manager
                elif comp_type == 'triggers': manager = self.trigger_manager
                if manager and comp_id:
                    self.logger(f"Received request to INSTALL {comp_type} '{comp_id}'", "WARN", "GatewayConnectorRPC") # English Log
                    response_payload = {"type": "status_response", "status": f"Install command received for {comp_id}."} # English Hardcode
                    install_callback = self._create_async_install_callback(comp_type, 'install', authed_user_id) # English Hardcode
                    manager.install_component_dependencies(comp_id, on_complete=install_callback)
                else:
                    response_payload = {"type": "error", "message": "Invalid component type or ID for install."} # English Hardcode
            elif payload_type == 'uninstall_component': # English Hardcode
                comp_type = main_payload.get('component_type')
                comp_id = main_payload.get('component_id')
                manager = None
                if comp_type == 'modules': manager = self.module_manager
                elif comp_type == 'plugins': manager = self.plugin_manager
                elif comp_type == 'tools': manager = self.tools_manager
                elif comp_type == 'triggers': manager = self.trigger_manager
                if manager and comp_id:
                    self.logger(f"Received request to UNINSTALL {comp_type} '{comp_id}'", "WARN", "GatewayConnectorRPC") # English Log
                    response_payload = {"type": "status_response", "status": f"Uninstall command received for {comp_id}."} # English Hardcode
                    uninstall_callback = self._create_async_install_callback(comp_type, 'uninstall', authed_user_id) # English Hardcode
                    manager.uninstall_component_dependencies(comp_id, on_complete=uninstall_callback)
                else:
                    response_payload = {"type": "error", "message": "Invalid component type or ID for uninstall."} # English Hardcode
            elif payload_type == 'request_components_list': # English Hardcode
                comp_type = main_payload.get('component_type')
                manager = None
                if comp_type == 'modules': manager = self.module_manager
                elif comp_type == 'plugins': manager = self.plugin_manager
                elif comp_type == 'tools': manager = self.tools_manager
                elif comp_type == 'triggers': manager = self.trigger_manager
                elif comp_type == 'ai_providers': manager = self.ai_provider_manager
                components = []
                if manager:
                    items_attr_name = None
                    if comp_type == 'modules': items_attr_name = 'loaded_modules'
                    elif comp_type == 'plugins': items_attr_name = 'loaded_plugins'
                    elif comp_type == 'tools': items_attr_name = 'loaded_tools'
                    elif comp_type == 'triggers': items_attr_name = 'loaded_triggers'
                    elif comp_type == 'ai_providers': items_attr_name = 'loaded_providers'
                    if items_attr_name:
                        loaded_items = getattr(manager, items_attr_name, {})
                        for item_id, item_data in loaded_items.items():
                            if isinstance(item_data, dict) and not item_data.get('is_paused', False):
                                manifest_data = {}
                                if comp_type == 'ai_providers':
                                    instance = item_data
                                    if hasattr(instance, 'get_manifest'):
                                        manifest_data = instance.get_manifest()
                                else:
                                    manifest_data = item_data.get("manifest", {})
                                components.append({
                                    "id": item_id,
                                    "name": manifest_data.get("name", item_id),
                                    "manifest": manifest_data,
                                    "is_installed": item_data.get("is_installed", False)
                                })
                response_payload = {
                    "type": "components_list_response", # English Hardcode
                    "component_type": comp_type,
                    "components": sorted(components, key=lambda x: x['name'])
                }
            elif payload_type == 'request_presets_list': # English Hardcode
                presets = []
                if self.preset_manager:
                    presets = self.preset_manager.get_preset_list(user_id=authed_user_id)
                response_payload = {"type": "presets_list_response", "presets": presets} # English Hardcode
            elif payload_type == 'load_preset': # English Hardcode
                preset_name = main_payload.get('name')
                workflow_data = None
                if self.preset_manager:
                    workflow_data = self.preset_manager.get_preset_data(preset_name, user_id=authed_user_id)
                response_payload = {"type": "load_preset_response", "name": preset_name, "workflow_data": workflow_data} # English Hardcode
            elif payload_type == 'save_preset': # English Hardcode
                preset_name = main_payload.get('name')
                workflow_data = main_payload.get('workflow_data')
                signature = main_payload.get('signature')
                if self.preset_manager:
                    success = self.preset_manager.save_preset(
                        preset_name, workflow_data, user_id=authed_user_id, signature=signature
                    )
                    if success:
                        response_payload = {"type": "status_response", "status": f"Preset '{preset_name}' saved."} # English Hardcode
                        presets = self.preset_manager.get_preset_list(user_id=authed_user_id)
                        self._send_rpc_response_to_gateway({"type": "presets_list_response", "presets": presets}) # English Hardcode
                    else:
                         response_payload = {"type": "error", "message": "Failed to save preset."} # English Hardcode
                else:
                     response_payload = {"type": "error", "message": "PresetManagerService not available."} # English Hardcode
            elif payload_type == 'delete_preset': # English Hardcode
                preset_name = main_payload.get('name')
                if self.preset_manager:
                    success = self.preset_manager.delete_preset(preset_name, user_id=authed_user_id)
                    if success:
                        response_payload = {"type": "status_response", "status": f"Preset '{preset_name}' deleted."} # English Hardcode
                        presets = self.preset_manager.get_preset_list(user_id=authed_user_id)
                        self._send_rpc_response_to_gateway({"type": "presets_list_response", "presets": presets}) # English Hardcode
                    else:
                         response_payload = {"type": "error", "message": "Failed to delete preset."} # English Hardcode
                else:
                    response_payload = {"type": "error", "message": "PresetManagerService not available."} # English Hardcode
            elif payload_type == 'request_settings': # English Hardcode
                settings = {}
                if self.settings_manager:
                    settings = self.settings_manager.get_all_settings(user_id=authed_user_id)
                response_payload = {"type": "settings_response", "settings": settings} # English Hardcode
            elif payload_type == 'save_settings': # English Hardcode
                if self.settings_manager:
                    self.settings_manager._save_settings(main_payload.get('settings', {}), user_id=authed_user_id)
                    response_payload = {"type": "status_response", "status": "Settings saved."} # English Hardcode
                else:
                    response_payload = {"type": "error", "message": "Settings manager not available."} # English Hardcode
            elif payload_type == 'request_variables': # English Hardcode
                variables = []
                if self.variable_manager:
                    variables = self.variable_manager.get_all_variables_for_api(user_id=authed_user_id)
                response_payload = {"type": "variables_response", "variables": variables} # English Hardcode
            elif payload_type == 'update_variable': # English Hardcode
                var_name = main_payload.get('name')
                var_data = main_payload.get('data')
                if self.variable_manager and var_name and var_data:
                    try:
                         self.variable_manager.set_variable(
                             var_name,
                             var_data.get('value'),
                             var_data.get('is_secret', False),
                             var_data.get('is_enabled', True),
                             mode=var_data.get('mode', 'single'),
                             user_id=authed_user_id
                         )
                         response_payload = {"type": "status_response", "status": f"Variable '{var_name}' updated."} # English Hardcode
                         variables = self.variable_manager.get_all_variables_for_api(user_id=authed_user_id)
                         self._send_rpc_response_to_gateway({"type": "variables_response", "variables": variables}) # English Hardcode
                    except ValueError as ve:
                         response_payload = {"type": "error", "message": str(ve)}
                else:
                    response_payload = {"type": "error", "message": "Variable manager not available or invalid payload."} # English Hardcode
            elif payload_type == 'delete_variable': # English Hardcode
                var_name = main_payload.get('name')
                if self.variable_manager and var_name:
                    success = self.variable_manager.delete_variable(var_name, user_id=authed_user_id)
                    if success:
                        response_payload = {"type": "status_response", "status": f"Variable '{var_name}' deleted."} # English Hardcode
                        variables = self.variable_manager.get_all_variables_for_api(user_id=authed_user_id)
                        self._send_rpc_response_to_gateway({"type": "variables_response", "variables": variables}) # English Hardcode
                    else:
                        response_payload = {"type": "error", "message": f"Variable '{var_name}' not found."} # English Hardcode
                else:
                     response_payload = {"type": "error", "message": "Variable manager not available or variable name missing."} # English Hardcode
            elif payload_type == 'request_connection_history': # English Hardcode
                if self.executor:
                     job_id_hist = main_payload.get('job_id')
                     conn_id_hist = main_payload.get('connection_id')
                     history_data = self.executor.get_connection_history(job_id_hist, conn_id_hist)
                     response_payload = {
                         "type": "connection_history_response", # English Hardcode
                         "job_id": job_id_hist,
                         "connection_id": conn_id_hist,
                         "history": history_data
                     }
                else:
                     response_payload = {"type": "error", "message": "Executor service not available."} # English Hardcode
            elif payload_type == 'request_ai_status': # English Hardcode
                if self.ai_provider_manager:
                    providers = self.ai_provider_manager.get_available_providers()
                    response_payload = {"type": "ai_status_response", "providers": providers} # English Hardcode
                else:
                    response_payload = {"type": "ai_status_response", "error": "AIProviderManagerService not available."} # English Hardcode
            elif payload_type == 'request_ai_playground': # English Hardcode
                if self.ai_provider_manager:
                    prompt = main_payload.get('prompt')
                    endpoint_id = main_payload.get('endpoint_id')
                    result = self.ai_provider_manager.query_ai_by_task('text', prompt, endpoint_id=endpoint_id) # English Hardcode
                    response_payload = {"type": "ai_playground_response", "result": result} # English Hardcode
                else:
                    response_payload = {"type": "ai_playground_response", "result": {"error": "AIProviderManagerService not available."}} # English Hardcode
            elif payload_type == 'request_datasets_list': # English Hardcode
                datasets = []
                if self.dataset_manager:
                    datasets = self.dataset_manager.list_datasets() # user_id ditangani oleh service
                response_payload = {"type": "datasets_list_response", "datasets": datasets} # English Hardcode
            elif payload_type == 'load_dataset_data': # English Hardcode
                name = main_payload.get('name')
                data = []
                if self.dataset_manager and name:
                    data = self.dataset_manager.get_dataset_data(name) # user_id ditangani oleh service
                response_payload = {"type": "dataset_data_response", "name": name, "data": data} # English Hardcode
            elif payload_type == 'create_dataset': # English Hardcode
                name = main_payload.get('name')
                if self.dataset_manager and name:
                    self.dataset_manager.create_dataset(name) # user_id ditangani oleh service
                    datasets = self.dataset_manager.list_datasets()
                    response_payload = {"type": "datasets_list_response", "datasets": datasets} # English Hardcode
                else:
                    response_payload = {"type": "error", "message": "Invalid name or dataset manager unavailable."} # English Hardcode
            elif payload_type == 'delete_dataset': # English Hardcode
                name = main_payload.get('name')
                if self.dataset_manager and name:
                    self.dataset_manager.delete_dataset(name) # user_id ditangani oleh service
                    datasets = self.dataset_manager.list_datasets()
                    response_payload = {"type": "datasets_list_response", "datasets": datasets} # English Hardcode
                else:
                    response_payload = {"type": "error", "message": "Invalid name or dataset manager unavailable."} # English Hardcode
            elif payload_type == 'add_dataset_data': # English Hardcode
                name = main_payload.get('name')
                data_rows = main_payload.get('data')
                if self.dataset_manager and name and data_rows:
                    self.dataset_manager.add_data_to_dataset(name, data_rows) # user_id ditangani oleh service
                    updated_data = self.dataset_manager.get_dataset_data(name)
                    self._send_rpc_response_to_gateway({"type": "dataset_data_response", "name": name, "data": updated_data}) # English Hardcode
                    datasets = self.dataset_manager.list_datasets()
                    response_payload = {"type": "datasets_list_response", "datasets": datasets} # English Hardcode
                else:
                    response_payload = {"type": "error", "message": "Invalid payload or dataset manager unavailable."} # English Hardcode
            elif payload_type == 'update_dataset_row': # English Hardcode
                name = main_payload.get('name')
                row_data = main_payload.get('row_data')
                if self.dataset_manager and name and row_data:
                    self.dataset_manager.update_dataset_row(name, row_data) # user_id ditangani oleh service
                    updated_data = self.dataset_manager.get_dataset_data(name)
                    response_payload = {"type": "dataset_data_response", "name": name, "data": updated_data} # English Hardcode
                else:
                    response_payload = {"type": "error", "message": "Invalid payload or dataset manager unavailable."} # English Hardcode
            elif payload_type == 'delete_dataset_row': # English Hardcode
                name = main_payload.get('name')
                row_id = main_payload.get('row_id')
                if self.dataset_manager and name and row_id:
                    self.dataset_manager.delete_dataset_row(name, row_id) # user_id ditangani oleh service
                    updated_data = self.dataset_manager.get_dataset_data(name)
                    response_payload = {"type": "dataset_data_response", "name": name, "data": updated_data} # English Hardcode
                else:
                    response_payload = {"type": "error", "message": "Invalid payload or dataset manager unavailable."} # English Hardcode
            elif payload_type == 'request_local_models': # English Hardcode
                models = []
                if self.ai_provider_manager:
                    all_models = getattr(self.ai_provider_manager, 'local_models', {})
                    for model_id, model_data in all_models.items():
                        if model_data.get("category") == "text": # English Hardcode
                            models.append({"id": model_data.get("name"), "name": model_data.get("name")})
                response_payload = {"type": "local_models_response", "models": sorted(models, key=lambda x: x['name'])} # English Hardcode
            elif payload_type == 'start_training_job': # English Hardcode
                config = main_payload.get('config')
                if self.training_manager and config:
                    try:
                        job_status = self.training_manager.start_fine_tuning_job(
                            base_model_id=config["base_model_id"],
                            dataset_name=config["dataset_name"],
                            new_model_name=config["new_model_name"],
                            training_args=config["training_args"]
                        )
                        response_payload = {"type": "training_job_status_response", "status": [job_status]} # English Hardcode
                    except Exception as train_e:
                        response_payload = {"type": "error", "message": str(train_e)} # English Hardcode
                else:
                    response_payload = {"type": "error", "message": "Invalid config or Training manager unavailable."} # English Hardcode
            elif payload_type == 'request_training_job_status': # English Hardcode
                job_id = main_payload.get('job_id')
                status_data = []
                if self.training_manager:
                    if job_id:
                        job_status = self.training_manager.get_job_status(job_id)
                        if job_status: status_data = [job_status]
                    else:
                        all_jobs = getattr(self.training_manager, 'training_jobs', {})
                        status_data = list(all_jobs.values())
                response_payload = {"type": "training_job_status_response", "status": status_data} # English Hardcode
            elif payload_type == 'request_prompts_list': # English Hardcode
                prompts = []
                if self.prompt_manager:
                    prompts = self.prompt_manager.get_all_prompts()
                response_payload = {"type": "prompts_list_response", "prompts": prompts} # English Hardcode
            else:
                response_payload = {"type": "error", "message": f"Command type '{payload_type}' is not recognized by the engine."} # English Hardcode
        except Exception as e:
            self.logger(f"[RPC Exec] Error processing {payload_type} for user {authed_user_id[:8]}...: {e}", "ERROR") # English Hardcode
            self.logger(traceback.format_exc(), "DEBUG")
            response_payload = {"type": "error", "message": str(e)} # English Hardcode
        if response_payload:
            self._send_rpc_response_to_gateway(response_payload)
    def on_force_sync_kill_switch(self, data=None):
        self.logger(
            "Received 'force_sync_kill_switch' signal from Gateway. Re-syncing...", # English log
            "WARN",
        )
        self._sync_kill_switch_list()
    def on_connect(self):
        self.logger(
            "Successfully connected to Gateway. Sending authentication token...", "SUCCESS" # English log
        )
        engine_id_from_env = os.getenv("FLOWORK_ENGINE_ID")
        if not engine_id_from_env:
            self.logger("CRITICAL: FLOWORK_ENGINE_ID not set in env. Auth will fail.", "CRITICAL") # English Hardcode
        auth_payload = {"token": self.engine_token, "engine_id": engine_id_from_env} # English Hardcode
        try:
            self.sio.emit("auth", auth_payload, namespace="/engine-socket")
        except Exception as e:
            self.logger(f"Failed to send auth token on connect: {e}", "ERROR") # English log
    def on_disconnect(self):
        self.is_connected_and_authed = False
        self.logger("Disconnected from Gateway.", "WARN") # English log
        self.stop_ping_event.set() # Hentikan ping worker
    def on_auth_success(self, data):
        self.is_connected_and_authed = True
        self.logger(
            f"Engine successfully authenticated by Gateway: {data.get('message')}", # English log
            "SUCCESS",
        )
        try:
            self.sio.emit(
                "register_engine_http_info",
                {"http_url": self.core_server_url},
                namespace="/engine-socket",
            )
        except Exception as e:
             self.logger(f"Failed to register engine HTTP info: {e}", "ERROR") # English log
        self.fetch_and_update_auth_list()
        self._sync_kill_switch_list()
        self.stop_ping_event.clear()
        if self.ping_thread is None or not self.ping_thread.is_alive():
            self.ping_thread = threading.Thread(target=self._ping_worker, daemon=True)
            self.ping_thread.start()
    def on_auth_failed(self, data):
        self.logger(
            f"Authentication FAILED: {data.get('message')}. Please check your engine token.", # English log
            "CRITICAL",
        )
        self.sio.disconnect() # Putuskan koneksi jika token salah
    def on_trigger_backup(self, data):
        user_id = data.get("user_id")
        password = data.get("password")
        self.logger(
            f"BACKUP command received from Gateway for user: {user_id}", "INFO" # English log
        )
        if not user_id or not password:
            self.logger(
                "Backup command incomplete (missing user_id or password).", "ERROR" # English log
            )
            return
    def on_trigger_restore(self, data):
        user_id = data.get("user_id")
        password = data.get("password")
        self.logger(
            f"RESTORE command received from Gateway for user: {user_id}", "INFO" # English log
        )
        if not user_id or not password:
            self.logger(
                "Restore command incomplete (missing user_id or password).", "ERROR" # English log
            )
            return
