#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\services\permission_manager_service\permission_manager_service.py JUMLAH BARIS 26 
#######################################################################

from ..base_service import BaseService
from flowork_kernel.exceptions import PermissionDeniedError
class PermissionManagerService(BaseService):
    """
    (REMASTERED - OPEN CORE) Service ini dinetralkan.
    Dalam mode Open Core, semua pengecekan izin akan selalu berhasil.
    """
    def __init__(self, kernel, service_id: str):
        super().__init__(kernel, service_id)
        self.logger("PermissionManager: Running in Open Core mode. All permission checks will be approved.", "WARN")
    def load_rules_from_source(self, rules_dict):
        self.logger("Permission rules loading is skipped in Open Core mode.", "INFO")
        pass
    def check_permission(self, capability: str, is_system_call: bool = False) -> bool:
        """
        Dalam mode Open Core, fungsi ini selalu mengembalikan True.
        Tidak ada lagi fitur yang terkunci.
        """
        return True
