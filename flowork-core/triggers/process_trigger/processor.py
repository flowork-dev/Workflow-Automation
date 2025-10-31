#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\triggers\process_trigger\processor.py JUMLAH BARIS 68 
#######################################################################

import threading
import time
import psutil
from flowork_kernel.api_contract import BaseModule, IExecutable, BaseTriggerListener
class ProcessListener(BaseTriggerListener):
    def __init__(self, trigger_id, config, services, **kwargs):
        super().__init__(trigger_id, config, services, **kwargs)
        self.process_name = self.config.get("process_name")
        self.event_to_watch = self.config.get("event_to_watch", "started")
        self.check_interval = self.config.get("check_interval", 5)
        self.is_currently_running = False
        self._stop_event = threading.Event()
        self._thread = None
    def _is_process_running(self):
        for proc in psutil.process_iter(['name']):
            if proc.info['name'].lower() == self.process_name.lower():
                return True
        return False
    def _monitor_loop(self):
        self.is_currently_running = self._is_process_running()
        while not self._stop_event.is_set():
            time.sleep(self.check_interval)
            process_is_now_running = self._is_process_running()
            if process_is_now_running and not self.is_currently_running:
                if self.event_to_watch == "started":
                    self._on_event({"event": "started", "process_name": self.process_name})
            if not process_is_now_running and self.is_currently_running:
                if self.event_to_watch == "stopped":
                    self._on_event({"event": "stopped", "process_name": self.process_name})
            self.is_currently_running = process_is_now_running
    def start(self):
        if not self.process_name:
            self.logger(f"Process Trigger '{self.rule_id}' failed: Process name is not configured.", "ERROR")
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        self.is_running = True
        self.logger(f"Process Trigger '{self.rule_id}' started. Watching for '{self.process_name}'.", "INFO")
    def stop(self):
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)
        self.is_running = False
        self.logger(f"Process Trigger '{self.rule_id}' stopped.", "INFO")
class ProcessTriggerModule(BaseModule, IExecutable):
    TIER = "free"
    def __init__(self, module_id, services):
        super().__init__(module_id, services)
    def execute(self, payload: dict, config: dict, status_updater, mode='EXECUTE', **kwargs):
        process_name = config.get("process_name", "N/A")
        event = config.get("event_to_watch", "N/A")
        status_updater(f"Process Trigger (manual run). Watching: {process_name} for '{event}' event.", "INFO")
        if 'data' not in payload:
            payload['data'] = {}
        payload['data']['trigger_info'] = {
            'type': 'process',
            'event': event,
            'process_name': process_name
        }
        return {"payload": payload, "output_name": "output"}
