#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\plugins\metrics_dashboard\processor.py JUMLAH BARIS 19 
#######################################################################

from flowork_kernel.api_contract import BaseModule #, BaseUIProvider
class MetricsDashboardModule(BaseModule): # [REFACTORY] Removed BaseUIProvider inheritance
    TIER = "free"  # ADDED BY SCANNER: Default tier
    """
    Plugin yang menyediakan UI untuk menampilkan metrik eksekusi workflow.
    """
    def __init__(self, module_id, services):
        super().__init__(module_id, services)
        self.kernel.write_to_log(f"Plugin Dashboard Metrik ({self.module_id}) berhasil diinisialisasi.", "SUCCESS")
    def execute(self, payload, config, status_updater, mode='EXECUTE', **kwargs):
        status_updater("Tidak ada aksi", "INFO")
        return payload
