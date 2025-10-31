#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\services\variable_manager_service\variable_manager_service.py JUMLAH BARIS 228 
#######################################################################

import os
import json
import threading
import base64
import logging
import secrets
import string
import random
from collections import OrderedDict
from ..base_service import BaseService
from flowork_kernel.exceptions import PermissionDeniedError
class VariableManagerService(BaseService):
    """
    Acts as a secure vault for all global and secret variables.
    (REMASTERED FOR MULTI-TENANCY & CACHING) Data is now stored per-user and cached in memory.
    """
    VARIABLES_FILENAME = "variables.json"
    MAX_USER_CACHE_SIZE = 100
    def __init__(self, kernel, service_id: str):
        super().__init__(kernel, service_id)
        self.users_data_path = os.path.join(self.kernel.data_path, "users")
        os.makedirs(self.users_data_path, exist_ok=True)
        self._variables_data_cache = (
            OrderedDict()
        )  # TAMBAHAN: [PERBAIKAN] Menggunakan OrderedDict untuk LRU Cache
        self._lock = threading.Lock()
        self.kernel.write_to_log(
            "Service 'VariableManager' (Multi-Tenant & Cached) initialized.", "DEBUG"
        )
    def _get_user_variables_path(self, user_id: str):
        if not user_id:
            return os.path.join(self.kernel.data_path, self.VARIABLES_FILENAME)
        user_dir = os.path.join(self.users_data_path, user_id)
        os.makedirs(user_dir, exist_ok=True)
        return os.path.join(user_dir, self.VARIABLES_FILENAME)
    def autodiscover_and_sync_variables(self):
        self.logger(
            "VariableManager: Autodiscovery is temporarily adjusted for multi-tenancy.",
            "WARN",
        )
        return
    def _load_variables_from_file(self, user_id: str):
        variables_file_path = self._get_user_variables_path(user_id)
        user_vars = {}
        try:
            if os.path.exists(variables_file_path):
                with open(variables_file_path, "r", encoding="utf-8") as f:
                    user_vars = json.load(f)
        except (IOError, json.JSONDecodeError) as e:
            self.kernel.write_to_log(
                f"VariableManager: Failed to load variables for user '{user_id}': {e}",
                "ERROR",
            )
            user_vars = {}
        if user_id is None:  # Hanya berlaku untuk variabel global/sistem
            requires_save = False
            default_vars = {
                "FLOWORK_API_KEY": {
                    "value_generator": lambda: "".join(
                        secrets.choice(string.ascii_uppercase + string.digits)
                        for i in range(10)
                    ),
                    "is_secret": False,
                }
            }
            for var_name, var_details in default_vars.items():
                if var_name not in user_vars:
                    user_vars[var_name] = {
                        "value": var_details["value_generator"](),
                        "values": [],
                        "mode": "single",
                        "is_secret": var_details["is_secret"],
                        "is_enabled": True,
                        "sequential_index": 0,
                    }
                    requires_save = True
            if requires_save:
                self._save_variables_to_file(user_id, user_vars)
        return user_vars
    def _save_variables_to_file(self, user_id: str, data_to_save: dict):
        variables_file_path = self._get_user_variables_path(user_id)
        try:
            with open(variables_file_path, "w", encoding="utf-8") as f:
                json.dump(data_to_save, f, indent=4)
        except IOError as e:
            self.kernel.write_to_log(
                f"VariableManager: Failed to save variables for user '{user_id}': {e}",
                "ERROR",
            )
    def get_all_variables_for_api(self, user_id: str):
        with self._lock:
            if user_id not in self._variables_data_cache:
                self._variables_data_cache[user_id] = self._load_variables_from_file(
                    user_id
                )
            user_vars = self._variables_data_cache.get(user_id, {})
            api_safe_vars = json.loads(json.dumps(user_vars))
            for name, data in api_safe_vars.items():
                if data.get("is_secret"):
                    if data.get("mode", "single") == "single":
                        data["value"] = ""
                    else:
                        data["values"] = []
            return [
                dict(data, **{"name": name})
                for name, data in sorted(api_safe_vars.items())
            ]
    def get_variable(self, name, user_id: str = None):
        with self._lock:
            if user_id in self._variables_data_cache:
                self._variables_data_cache.move_to_end(user_id)
            else:
                self.kernel.write_to_log(
                    f"VariableManager CACHE MISS for user '{user_id}'. Loading from disk.",
                    "DEBUG",
                )
                user_vars_from_file = self._load_variables_from_file(user_id)
                self._variables_data_cache[user_id] = user_vars_from_file
                if len(self._variables_data_cache) > self.MAX_USER_CACHE_SIZE:
                    self._variables_data_cache.popitem(last=False)
            user_vars = self._variables_data_cache.get(user_id, {})
            var_data = user_vars.get(name)
            if not var_data or not var_data.get("is_enabled", True):
                return None
            mode = var_data.get("mode", "single")
            value_to_return = None
            if mode == "single":
                value_to_return = var_data.get("value")
            elif mode in ["random", "sequential"]:
                values_list = var_data.get("values", [])
                if not values_list:
                    return None
                if mode == "random":
                    value_to_return = random.choice(values_list)
                elif mode == "sequential":
                    current_index = var_data.get("sequential_index", 0)
                    value_to_return = values_list[current_index]
                    var_data["sequential_index"] = (current_index + 1) % len(
                        values_list
                    )
                    self._save_variables_to_file(user_id, user_vars)
            if var_data.get("is_secret") and value_to_return:
                try:
                    decoded_bytes = base64.b64decode(
                        str(value_to_return).encode("utf-8")
                    )
                    return decoded_bytes.decode("utf-8")
                except Exception:
                    return None
            else:
                return value_to_return
    def set_variable(
        self,
        name,
        value,
        is_secret,
        is_enabled=True,
        mode="single",
        user_id: str = None,
    ):
        if not name.isupper() or not name.replace("_", "").isalnum():
            raise ValueError(
                "Variable name must only contain uppercase letters (A-Z), numbers (0-9), and underscores (_)."
            )
        with self._lock:
            if user_id not in self._variables_data_cache:
                self.get_variable(
                    "any_key_to_load_data", user_id=user_id
                )  # Trik untuk load data ke cache
            user_vars = self._variables_data_cache.get(user_id, {})
            if mode == "single":
                processed_value = value
                if is_secret and value and value != "PLEASE_EDIT_ME":
                    processed_value = base64.b64encode(
                        str(value).encode("utf-8")
                    ).decode("utf-8")
                user_vars[name] = {
                    "value": processed_value,
                    "values": [],
                    "mode": "single",
                    "is_secret": is_secret,
                    "is_enabled": is_enabled,
                    "sequential_index": 0,
                }
            else:
                if not isinstance(value, list):
                    raise ValueError(
                        "Value for a pooled variable must be a list of strings."
                    )
                processed_values = []
                if is_secret:
                    for val in value:
                        if val:
                            processed_values.append(
                                base64.b64encode(str(val).encode("utf-8")).decode(
                                    "utf-8"
                                )
                            )
                else:
                    processed_values = value
                user_vars[name] = {
                    "value": None,
                    "values": processed_values,
                    "mode": mode,
                    "is_secret": is_secret,
                    "is_enabled": is_enabled,
                    "sequential_index": 0,
                }
            self._save_variables_to_file(user_id, user_vars)
    def delete_variable(self, name, user_id: str):
        with self._lock:
            if user_id not in self._variables_data_cache:
                self.get_variable(
                    "any_key_to_load_data", user_id=user_id
                )  # Trik untuk load data ke cache
            user_vars = self._variables_data_cache.get(user_id, {})
            if name in user_vars:
                del user_vars[name]
                self._save_variables_to_file(user_id, user_vars)
                return True
            return False
