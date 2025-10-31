#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\triggers\file_system_trigger\processor.py JUMLAH BARIS 88 
#######################################################################

import os
import time
import threading
from flowork_kernel.api_contract import BaseModule, IExecutable, BaseTriggerListener
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
class FileSystemListener(BaseTriggerListener, FileSystemEventHandler):
    def __init__(self, trigger_id, config, services, **kwargs):
        super().__init__(trigger_id, config, services, **kwargs)
        self.path_to_watch = self.config.get("path_to_watch")
        self.event_to_watch = self.config.get("event_to_watch", "created")
        self.watch_subdirectories = self.config.get("watch_subdirectories", True)
        self.observer = None
    def start(self):
        if not self.path_to_watch or not os.path.isdir(self.path_to_watch):
            self.logger(f"File System Trigger '{self.rule_id}' failed: Path '{self.path_to_watch}' is invalid.", "ERROR")
            return
        self.observer = Observer()
        self.observer.schedule(self, self.path_to_watch, recursive=self.watch_subdirectories)
        self.observer.start()
        self.is_running = True
        self.logger(f"File System Trigger '{self.rule_id}' started. Watching '{self.path_to_watch}'.", "INFO")
    def stop(self):
        if self.observer and self.observer.is_alive():
            self.observer.stop()
            self.observer.join()
        self.is_running = False
        self.logger(f"File System Trigger '{self.rule_id}' stopped.", "INFO")
    def on_created(self, event):
        if self.event_to_watch == "created":
            self._on_event({
                "event": "created",
                "path": event.src_path,
                "is_directory": event.is_directory
            })
    def on_modified(self, event):
        if self.event_to_watch == "modified":
            self._on_event({
                "event": "modified",
                "path": event.src_path,
                "is_directory": event.is_directory
            })
    def on_deleted(self, event):
        if self.event_to_watch == "deleted":
            self._on_event({
                "event": "deleted",
                "path": event.src_path,
                "is_directory": event.is_directory
            })
    def on_moved(self, event):
        if self.event_to_watch == "moved":
            self._on_event({
                "event": "moved",
                "src_path": event.src_path,
                "dest_path": event.dest_path,
                "is_directory": event.is_directory
            })
class FileSystemTriggerModule(BaseModule, IExecutable):
    """
    Processor untuk File System Trigger Node.
    """
    TIER = "free"
    def __init__(self, module_id, services):
        super().__init__(module_id, services)
    def execute(self, payload: dict, config: dict, status_updater, mode='EXECUTE', **kwargs):
        """
        Saat dijalankan manual, node ini hanya meneruskan payload dengan data simulasi.
        """
        path = config.get("path_to_watch", "N/A")
        event = config.get("event_to_watch", "N/A")
        status_updater(f"File System Trigger (manual run). Watching: {path} for {event} events.", "INFO")
        if 'data' not in payload:
            payload['data'] = {}
        payload['data']['trigger_info'] = {
            'type': 'file_system',
            'event': event,
            'path': path,
            'is_directory': True,
            'src_path': f"{path}{os.sep}contoh_file.txt"
        }
        return {"payload": payload, "output_name": "output"}
