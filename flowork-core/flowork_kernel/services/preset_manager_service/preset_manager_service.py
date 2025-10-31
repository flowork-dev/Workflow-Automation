#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\services\preset_manager_service\preset_manager_service.py JUMLAH BARIS 255 
#######################################################################

import os
import json
import shutil
import datetime
import threading
from ..base_service import BaseService
from flowork_kernel.exceptions import PresetNotFoundError
from flowork_kernel.utils.flowchain_verifier import verify_workflow_chain, calculate_hash
class PresetManagerService(BaseService):
    """
    (REMASTERED - FILE BASED) Manages loading, saving, and versioning of workflow presets from the local filesystem.
    This version is self-contained within the Core Engine and does not use a central database, ensuring portability.
    It supports multi-tenancy by storing presets in user-specific subdirectories.
    (REMASTERED - FASE 2) Now implements the "Flow-Chain" logic.
    Presets are stored in versioned, hashed, and signed files locally.
    data/users/<user_id>/presets/<preset_name>/v1_...json, v2_...json
    """
    def __init__(self, kernel, service_id: str):
        super().__init__(kernel, service_id)
        self.users_data_path = os.path.join(self.kernel.data_path, "users")
        self._save_lock = threading.Lock()
        self.state_manager = self.kernel.get_service("state_manager")
        self.trigger_manager = None
        self.logger(
            "Service 'PresetManager' (Flow-Chain Enabled) initialized.", "DEBUG" # English Hardcode
        )
    def start(self):
        """
        Loads dependencies after kernel startup.
        """
        self.trigger_manager = self.kernel.get_service("trigger_manager_service")
        os.makedirs(self.users_data_path, exist_ok=True)
        self.logger("PresetManagerService started and dependencies loaded.", "INFO") # English Hardcode
    def _get_user_presets_path(self, user_id: str):
        """
        (PERBAIKAN FASE 2) Returns the path to the *base* presets directory for a specific user.
        If user_id is None, it points to a shared/default presets folder.
        """
        if not user_id:
            user_id = "_global"
        user_dir = os.path.join(self.users_data_path, user_id)
        presets_dir = os.path.join(user_dir, "presets")
        os.makedirs(presets_dir, exist_ok=True)
        return presets_dir
    def _get_preset_workflow_path(self, user_id: str, name: str):
        """
        Returns the path to the specific workflow directory.
        e.g., .../users/0xABC/presets/my_workflow/
        """
        base_presets_dir = self._get_user_presets_path(user_id)
        workflow_path = os.path.join(base_presets_dir, name)
        os.makedirs(workflow_path, exist_ok=True)
        return workflow_path
    def _get_latest_version_file(self, workflow_path: str):
        """
        Finds the latest (highest version number) .json file in a workflow directory.
        """
        if not os.path.isdir(workflow_path):
            return None, 0
        files = [f for f in os.listdir(workflow_path) if f.endswith('.json') and f.startswith('v')]
        if not files:
            return None, 0
        def get_version_num(filename):
            try:
                return int(filename.split('_')[0][1:])
            except:
                return -1
        latest_file = max(files, key=get_version_num)
        latest_version_num = get_version_num(latest_file)
        return os.path.join(workflow_path, latest_file), latest_version_num
    def _sync_trigger_rules_for_preset(
        self,
        preset_name: str,
        workflow_data: dict,
        user_id: str,
        is_delete: bool = False,
    ):
        if not self.state_manager or not self.trigger_manager:
            self.logger(
                "Cannot sync trigger rules: StateManager or TriggerManager not available.", # English Hardcode
                "WARN",
            )
            return
        all_rules = self.state_manager.get("trigger_rules", user_id=user_id, default={})
        rules_to_delete = [
            rule_id
            for rule_id, rule in all_rules.items()
            if rule.get("preset_to_run") == preset_name
        ]
        for rule_id in rules_to_delete:
            del all_rules[rule_id]
            self.logger(
                f"Removed old trigger rule '{rule_id}' for preset '{preset_name}'.", # English Hardcode
                "INFO",
            )
        if not is_delete and workflow_data:
            trigger_nodes = [
                node
                for node in workflow_data.get("nodes", [])
                if node.get("manifest", {}).get("type") == "TRIGGER"
            ]
            for node in trigger_nodes:
                rule_id = f"node::{node['id']}"
                new_rule = {
                    "name": f"Trigger for {preset_name} ({node['name']})", # English Hardcode
                    "trigger_id": node["module_id"],
                    "preset_to_run": preset_name,
                    "config": node.get("config_values", {}),
                    "is_enabled": True,
                    "__owner_user_id": user_id,
                }
                all_rules[rule_id] = new_rule
                self.logger(
                    f"Created/Updated trigger rule '{rule_id}' for preset '{preset_name}'.", # English Hardcode
                    "INFO",
                )
        self.state_manager.set("trigger_rules", all_rules, user_id=user_id)
        self.trigger_manager.start_all_listeners()
    def get_preset_list(self, user_id: str):
        presets_dir = self._get_user_presets_path(user_id)
        try:
            preset_folders = [d for d in os.listdir(presets_dir) if os.path.isdir(os.path.join(presets_dir, d)) and not d == "_versions"]
            return [{"name": name} for name in sorted(preset_folders)]
        except FileNotFoundError:
            return []
        except Exception as e:
            self.logger(f"Could not get preset list for user '{user_id}': {e}", "ERROR") # English Hardcode
            return []
    def get_preset_data(self, name: str, user_id: str):
        workflow_path = self._get_preset_workflow_path(user_id, name)
        is_valid, message = verify_workflow_chain(workflow_path)
        if not is_valid:
            self.logger(f"CRITICAL: Integrity check failed for preset '{name}'. {message}", "ERROR") # English Hardcode
            return None # Do not load corrupt data
        latest_file_path, _ = self._get_latest_version_file(workflow_path)
        if not latest_file_path:
            self.logger(f"No version files found for preset '{name}', but folder exists.", "WARN") # English Hardcode
            return None # Return empty/none if no versions exist
        try:
            with open(latest_file_path, "r", encoding="utf-8") as f:
                chain_data = json.load(f)
                return chain_data.get("workflow_data") # Return only the workflow part
        except (IOError, json.JSONDecodeError) as e:
            self.logger(
                f"Could not read or parse latest preset file '{latest_file_path}': {e}", # English Hardcode
                "ERROR",
            )
            return None
    def save_preset(self, name: str, workflow_data: dict, user_id: str, signature: str) -> bool:
        if not name.strip() or not user_id:
            return False
        workflow_path = self._get_preset_workflow_path(user_id, name)
        try:
            with self._save_lock:
                latest_file_path, latest_version_num = self._get_latest_version_file(workflow_path)
                previous_hash = None
                if latest_file_path:
                    previous_hash = calculate_hash(latest_file_path)
                new_version = latest_version_num + 1
                new_timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat().replace('+00:00', 'Z')
                new_chain_data = {
                    "version": new_version,
                    "author_id": user_id, # The public address of the user [cite: 47]
                    "timestamp": new_timestamp,
                    "previous_hash": previous_hash, # [cite: 47]
                    "workflow_data": workflow_data,
                    "signature": signature # [cite: 48]
                }
                new_filename = f"v{new_version}_{new_timestamp.replace(':', '-').replace('.', '-')}.json"
                new_file_path = os.path.join(workflow_path, new_filename)
                with open(new_file_path, "w", encoding="utf-8") as f:
                    json.dump(new_chain_data, f, indent=4)
                self.logger(f"Flow-Chain: Saved version {new_version} for preset '{name}'.", "SUCCESS") # English Hardcode
                self._sync_trigger_rules_for_preset(
                    name, workflow_data, user_id=user_id
                )
                return True
        except Exception as e:
            self.logger(f"Could not save preset '{name}': {e}", "ERROR") # English Hardcode
            return False
    def delete_preset(self, name: str, user_id: str) -> bool:
        workflow_path = self._get_preset_workflow_path(user_id, name)
        try:
            with self._save_lock:
                if os.path.isdir(workflow_path):
                    shutil.rmtree(workflow_path) # Delete the whole folder
                    self._sync_trigger_rules_for_preset(
                        name, None, user_id=user_id, is_delete=True
                    )
                    return True
                return False
        except Exception as e:
            self.logger(f"Could not delete preset folder '{name}': {e}", "ERROR") # English Hardcode
            return False
    def get_preset_versions(self, name: str, user_id: str) -> list:
        workflow_path = self._get_preset_workflow_path(user_id, name)
        if not os.path.isdir(workflow_path):
            return []
        files = [f for f in os.listdir(workflow_path) if f.endswith('.json') and f.startswith('v')]
        versions = []
        def get_version_num(filename):
            try:
                return int(filename.split('_')[0][1:])
            except:
                return -1
        sorted_files = sorted(files, key=get_version_num, reverse=True)
        for filename in sorted_files:
            try:
                version_str = filename.split('_')[0]
                timestamp_str = os.path.splitext(filename.split('_', 1)[1])[0].replace('-', ':')
                try:
                    dt_obj = datetime.datetime.fromisoformat(timestamp_str)
                    ts_display = dt_obj.strftime("%Y-%m-%d %H:%M:%S")
                except:
                    ts_display = datetime.datetime.fromtimestamp(os.path.getmtime(os.path.join(workflow_path, filename))).strftime("%Y-%m-%d %H:%M:%S")
                versions.append(
                    {
                        "id": filename,  # Use filename as unique ID
                        "version": version_str,
                        "timestamp": ts_display,
                    }
                )
            except Exception:
                continue # Skip files with incorrect name format
        return versions
    def load_preset_version(self, name: str, version_filename: str, user_id: str):
        workflow_path = self._get_preset_workflow_path(user_id, name)
        version_path = os.path.join(workflow_path, version_filename)
        is_valid, message = verify_workflow_chain(workflow_path)
        if not is_valid:
            self.logger(f"CRITICAL: Integrity check failed for preset '{name}' when trying to load version. {message}", "ERROR") # English Hardcode
            return None
        try:
            with open(version_path, "r", encoding="utf-8") as f:
                chain_data = json.load(f)
                return chain_data.get("workflow_data") # Return only the workflow part
        except FileNotFoundError:
            return None
        except Exception as e:
            self.logger(
                f"Could not load preset version '{version_filename}': {e}", "ERROR" # English Hardcode
            )
            return None
    def delete_preset_version(
        self, name: str, version_filename: str, user_id: str
    ) -> bool:
        self.logger("Deleting a single version is not allowed in Flow-Chain model as it breaks integrity.", "WARN") # English Hardcode
        return False
