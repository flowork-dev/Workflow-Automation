#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\services\license_manager_service\license_manager_service.py JUMLAH BARIS 37 
#######################################################################

from ..base_service import BaseService
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from flowork_kernel.kernel import Kernel
class LicenseManagerService(BaseService):
    """
    (REMASTERED - OPEN CORE) Service ini dinetralkan.
    Tugasnya hanya untuk memberikan izin akses penuh (tier 'architect') kepada semua pengguna
    dan mengaktifkan semua kapabilitas (permissions) yang ada di sistem.
    """
    def __init__(self, kernel: "Kernel", service_id: str):
        super().__init__(kernel, service_id)
        self.logger("LicenseManager: Running in Open Core mode. All features unlocked.", "WARN")
        self.remote_permission_rules = {}
    def verify_license_on_startup(self):
        """
        Dalam mode Open Core, fungsi ini langsung memberikan tier tertinggi
        dan semua kapabilitas (permissions) ke sistem.
        """
        self.kernel.license_tier = "architect" # Berikan tier tertinggi secara default
        all_capabilities = [
            "basic_execution", "core_services", "unlimited_api", "preset_versioning",
            "ai_provider_access", "ai_local_models", "ai_copilot", "time_travel_debugger",
            "ai_architect", "core_compiler", "engine_management", "cloud_sync"
        ]
        self.remote_permission_rules = {
            "monetization_active": False, # Monetisasi via lisensi tidak aktif
            "capabilities": all_capabilities
        }
        self.logger(f"License tier automatically set to: {self.kernel.license_tier.upper()}", "SUCCESS")
