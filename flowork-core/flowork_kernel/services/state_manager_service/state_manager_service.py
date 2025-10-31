#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\services\state_manager_service\state_manager_service.py JUMLAH BARIS 142 
#######################################################################

import os
import json
import threading
from collections import OrderedDict
from ..base_service import BaseService
class StateManagerService(BaseService):
    """
    Manages persistent state data for the entire application in a thread-safe manner.
    (REMASTERED V2 FOR MULTI-TENANCY) Now handles both global state and user-specific state.
    """
    GLOBAL_STATE_FILENAME = "state.json"
    USER_STATE_FILENAME = "state.json"
    MAX_USER_CACHE_SIZE = 100
    def __init__(self, kernel, service_id: str):
        super().__init__(kernel, service_id)
        self.users_data_path = os.path.join(self.kernel.data_path, "users")
        self.global_state_file_path = os.path.join(
            self.kernel.data_path, self.GLOBAL_STATE_FILENAME
        )
        os.makedirs(self.users_data_path, exist_ok=True)
        self._global_state_cache = {}
        self._user_state_cache = OrderedDict()
        self._lock = threading.Lock()
        self.kernel.write_to_log(
            "Service 'StateManager' (Hybrid Multi-Tenant) initialized.", "DEBUG"
        )
        self._load_global_state()
    def _load_global_state(self):
        try:
            if os.path.exists(self.global_state_file_path):
                with open(self.global_state_file_path, "r", encoding="utf-8") as f:
                    self._global_state_cache = json.load(f)
                self.kernel.write_to_log(
                    f"StateManager: Global state loaded successfully.", "INFO"
                )
            else:
                self._global_state_cache = {}
        except (IOError, json.JSONDecodeError) as e:
            self.kernel.write_to_log(
                f"StateManager: Failed to load global state: {e}. Using empty state.",
                "ERROR",
            )
            self._global_state_cache = {}
    def _save_global_state(self):
        try:
            with open(self.global_state_file_path, "w", encoding="utf-8") as f:
                json.dump(self._global_state_cache, f, indent=4)
        except IOError as e:
            self.kernel.write_to_log(
                f"StateManager: FAILED to save global state. Error: {e}", "ERROR"
            )
    def _get_user_state_path(self, user_id: str):
        user_dir = os.path.join(self.users_data_path, user_id)
        os.makedirs(user_dir, exist_ok=True)
        return os.path.join(user_dir, self.USER_STATE_FILENAME)
    def _load_user_state_from_file(self, user_id: str):
        state_file_path = self._get_user_state_path(user_id)
        try:
            if os.path.exists(state_file_path):
                with open(state_file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            return {}
        except (IOError, json.JSONDecodeError):
            return {}
    def _save_user_state_to_file(self, user_id: str, state_data: dict):
        state_file_path = self._get_user_state_path(user_id)
        try:
            with open(state_file_path, "w", encoding="utf-8") as f:
                json.dump(state_data, f, indent=4)
        except IOError as e:
            self.kernel.write_to_log(
                f"StateManager: FAILED to save state for user '{user_id}'. Error: {e}",
                "ERROR",
            )
    def get(self, key, user_id: str = None, default=None):
        with self._lock:
            if user_id:
                if user_id not in self._user_state_cache:
                    self._user_state_cache[user_id] = self._load_user_state_from_file(
                        user_id
                    )
                    if len(self._user_state_cache) > self.MAX_USER_CACHE_SIZE:
                        self._user_state_cache.popitem(
                            last=False
                        )  # Hapus yang paling lama
                self._user_state_cache.move_to_end(
                    user_id
                )  # Tandai sebagai baru diakses
                return self._user_state_cache[user_id].get(key, default)
            else:
                return self._global_state_cache.get(key, default)
    def set(self, key, value, user_id: str = None):
        with self._lock:
            if user_id:
                if user_id not in self._user_state_cache:
                    self._user_state_cache[user_id] = self._load_user_state_from_file(
                        user_id
                    )
                self._user_state_cache[user_id][key] = value
                self._user_state_cache.move_to_end(user_id)
                self._save_user_state_to_file(user_id, self._user_state_cache[user_id])
                self.kernel.write_to_log(
                    f"StateManager: State for key '{key}' for user '{user_id}' has been set.",
                    "DEBUG",
                )
            else:
                self._global_state_cache[key] = value
                self._save_global_state()
                self.kernel.write_to_log(
                    f"StateManager: Global state for key '{key}' has been set.", "DEBUG"
                )
    def delete(self, key, user_id: str = None):
        with self._lock:
            if user_id:
                if user_id not in self._user_state_cache:
                    self._user_state_cache[user_id] = self._load_user_state_from_file(
                        user_id
                    )
                if key in self._user_state_cache[user_id]:
                    del self._user_state_cache[user_id][key]
                    self._save_user_state_to_file(
                        user_id, self._user_state_cache[user_id]
                    )
                    self.kernel.write_to_log(
                        f"StateManager: State for key '{key}' for user '{user_id}' has been deleted.",
                        "DEBUG",
                    )
            else:
                if key in self._global_state_cache:
                    del self._global_state_cache[key]
                    self._save_global_state()
                    self.kernel.write_to_log(
                        f"StateManager: Global state for key '{key}' has been deleted.",
                        "DEBUG",
                    )
