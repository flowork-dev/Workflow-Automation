#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\triggers\cron_trigger\processor.py JUMLAH BARIS 31 
#######################################################################

from flowork_kernel.api_contract import BaseModule, IExecutable
class CronTriggerModule(BaseModule, IExecutable):
    """
    Processor untuk Cron Trigger Node.
    Node ini bertindak sebagai entry point untuk workflow yang dijadwalkan.
    """
    TIER = "free"
    def __init__(self, module_id, services):
        super().__init__(module_id, services)
    def execute(self, payload: dict, config: dict, status_updater, mode='EXECUTE', **kwargs):
        """
        Saat dijalankan secara manual, node ini hanya meneruskan payload.
        Eksekusi sebenarnya ditangani oleh SchedulerManagerService berdasarkan
        konfigurasi yang disimpan bersama workflow.
        """
        cron_string = config.get("cron_string", "N/A")
        status_updater(f"Cron Trigger (manual run). Schedule: {cron_string}", "INFO")
        if 'data' not in payload:
            payload['data'] = {}
        payload['data']['trigger_info'] = {
            'type': 'cron',
            'schedule': cron_string
        }
        return {"payload": payload, "output_name": "output"}
