#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\services\startup_service\startup_service.py JUMLAH BARIS 162 
#######################################################################

from ..base_service import BaseService
import time
import asyncio
from flowork_kernel.exceptions import (
    MandatoryUpdateRequiredError,
    PermissionDeniedError,
)
import os
class StartupService(BaseService):
    """
    (REMASTERED V7) Handles the startup sequence with corrected service loading order
    to prevent premature permission blocks.
    (REMASTERED FASE 3) Startup logic adapted for local identity and local license.
    """
    def __init__(self, kernel, service_id: str):
        super().__init__(kernel, service_id)
        pass # (PENAMBAHAN KODE) Menambahkan 'pass' agar indentasi valid
    async def run_startup_sequence(self):
        """
        Executes the main startup logic with corrected initialization order.
        """
        try:
            self.logger("StartupService (Phase 1): Pre-flight checks...", "INFO") # English Hardcode
            update_service = self.kernel.get_service(
                "update_service", is_system_call=True
            )
            if update_service:
                update_service.run_update_check()
            integrity_checker = self.kernel.get_service(
                "integrity_checker_service", is_system_call=True
            )
            if integrity_checker:
                integrity_checker.verify_core_files()
            self.logger(
                "StartupService (Phase 2): Starting all core and essential services...", # English Hardcode
                "INFO",
            )
            essential_services_to_start = {
                "api_server_service": None,
                "module_manager_service": lambda s: s.discover_and_load_modules(),
                "plugin_manager_service": lambda s: s.discover_and_load_plugins(),
                "tools_manager_service": lambda s: s.discover_and_load_tools(),
                "scanner_manager_service": lambda s: s.discover_and_load_scanners(),
                "widget_manager_service": lambda s: s.discover_and_load_widgets(),
                "trigger_manager_service": lambda s: s.discover_and_load_triggers(),
                "preset_manager_service": lambda s: s.start(),
                "localization_manager": lambda s: s.load_all_languages(),
                "scheduler_manager_service": lambda s: s.start(),
                "gateway_connector_service": None,
            }
            for service_id, start_action in essential_services_to_start.items():
                try:
                    service_instance = self.kernel.get_service(
                        service_id, is_system_call=True
                    )
                    if service_instance:
                        if (
                            start_action is None
                            and hasattr(service_instance, "start")
                            and asyncio.iscoroutinefunction(service_instance.start)
                        ):
                            await service_instance.start()
                        elif (
                            start_action is None
                            and hasattr(service_instance, "start")
                            and not asyncio.iscoroutinefunction(service_instance.start)
                        ):
                            service_instance.start()
                        elif start_action:
                            start_action(service_instance)
                except Exception as e:
                    self.logger(
                        self.loc.get(
                            "log_startup_service_error", service_id=service_id, error=e
                        ),
                        "ERROR",
                    )
            self.logger(
                "StartupService (Phase 3): User identity and permission setup...", # English Hardcode
                "INFO",
            )
            self._attempt_auto_login() # Ini sekarang memuat identitas lokal ke kernel.current_user
            license_manager = self.kernel.get_service(
                "license_manager_service", is_system_call=True
            )
            if license_manager:
                license_manager.verify_license_on_startup() # Ini sekarang memanggil verify_local_license()
            permission_manager = self.kernel.get_service(
                "permission_manager_service", is_system_call=True
            )
            if permission_manager and license_manager:
                self.logger(self.loc.get("log_startup_inject_rules"), "INFO")
                permission_manager.load_rules_from_source(
                    license_manager.remote_permission_rules
                )
            self.logger(
                "StartupService (Phase 4): Starting remaining and gateway services...", # English Hardcode
                "INFO",
            )
            remaining_services = [
                "trigger_manager_service",
            ]
            for service_id in remaining_services:
                try:
                    service_instance = self.kernel.get_service(
                        service_id, is_system_call=True
                    )
                    if service_instance and hasattr(service_instance, "start"):
                        service_instance.start()
                except PermissionDeniedError:
                    self.logger(
                        self.loc.get("log_startup_skip_service", service_id=service_id),
                        "WARN",
                    )
            self.logger(
                "StartupService: Activating background service plugins...", "INFO" # English Hardcode
            )
            plugin_manager = self.kernel.get_service(
                "plugin_manager_service", is_system_call=True
            )
            if plugin_manager:
                for plugin_id, plugin_data in plugin_manager.loaded_plugins.items():
                    if plugin_data.get("manifest", {}).get("is_service"):
                        try:
                            plugin_manager.get_instance(plugin_id)
                        except PermissionDeniedError:
                            self.logger(
                                f"Skipped loading service plugin '{plugin_id}' due to license restrictions.", # English Hardcode
                                "WARN",
                            )
            time.sleep(1)
            event_bus = self.kernel.get_service("event_bus", is_system_call=True)
            if event_bus:
                event_bus.publish("event_all_services_started", {})
            self.kernel.startup_complete = True
            self.logger(self.loc.get("log_startup_all_services_started"), "SUCCESS")
            return {"status": "complete"}
        except MandatoryUpdateRequiredError:
            raise
        except Exception as e:
            self.logger(self.loc.get("log_startup_critical_error", error=e), "CRITICAL")
            import traceback
            self.logger(traceback.format_exc(), "DEBUG")
            raise e
    def _attempt_auto_login(self):
        self.logger("StartupService: Attempting to load local user identity...", "INFO") # English Hardcode
        state_manager = self.kernel.get_service("state_manager", is_system_call=True)
        if not state_manager:
            self.logger("StateManager not found. Cannot load user identity.", "WARN") # English Hardcode
            self.kernel.current_user = None
            return
        self.logger("StartupService: No user identity loaded at startup. Waiting for GUI connection.", "INFO") # English Hardcode
        self.kernel.current_user = None
        state_manager.delete("current_user_data")
        state_manager.delete("user_session_token")
