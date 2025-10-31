#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\plugins\metrics_logger_plugin\metrics_logger.py JUMLAH BARIS 46 
#######################################################################

import os
import json
import time
from flowork_kernel.api_contract import BaseModule
class MetricsLogger(BaseModule):
    TIER = "free"  # ADDED BY SCANNER: Default tier
    """
    Service that runs in the background, listens for NODE_EXECUTION_METRIC events,
    and logs them to a file for later analysis by other widgets.
    """
    def __init__(self, module_id, services):
        super().__init__(module_id, services)
        self.history_file_path = os.path.join(
            self.kernel.data_path, "metrics_history.jsonl"
        )
    def on_load(self):
        """When the plugin loads, subscribe to the event bus."""
        self.logger(
            "Metrics Logger: Ready to record detailed execution metrics.", "INFO"
        )
        self.event_bus.subscribe(
            event_name="NODE_EXECUTION_METRIC",
            subscriber_id=self.module_id,
            callback=self.on_metrics_updated,
        )
    def on_metrics_updated(self, metrics_data):
        """
        Callback executed whenever a NODE_EXECUTION_METRIC event occurs.
        """
        log_entry = {"timestamp": time.time(), "metrics": metrics_data}
        try:
            with open(self.history_file_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            self.logger(
                f"Metrics Logger: Failed to write to history file: {e}", "ERROR"
            )
    def execute(self, payload, config, status_updater, ui_callback, mode):
        return payload
