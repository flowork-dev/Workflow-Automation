#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\triggers\file_system_trigger\listener.py JUMLAH BARIS 80 
#######################################################################

from flowork_kernel.core import build_security
import time
import os
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent, FileDeletedEvent, FileMovedEvent
from flowork_kernel.api_contract import BaseTriggerListener
class _InternalEventHandler(FileSystemEventHandler):
    """Kelas internal untuk menangani event dari watchdog dan meneruskannya."""
    def __init__(self, listener_instance):
        build_security.perform_runtime_check(__file__)
        self.listener = listener_instance
    def on_any_event(self, event):
        if event.is_directory:
            return
        event_type = "unknown"
        if isinstance(event, FileCreatedEvent):
            event_type = "created"
        elif isinstance(event, FileModifiedEvent):
            event_type = "modified"
        elif isinstance(event, FileDeletedEvent):
            event_type = "deleted"
        elif isinstance(event, FileMovedEvent):
            event_type = "moved"
        event_data = {
            "trigger_id": self.listener.trigger_id,
            "rule_id": self.listener.rule_id, # Sertakan ID aturan untuk identifikasi
            "event_type": event_type,
            "src_path": event.src_path
        }
        if isinstance(event, FileMovedEvent):
            event_data["dest_path"] = event.dest_path
        self.listener._on_event(event_data)
class FileSystemListener(BaseTriggerListener):
    """
    Listener that monitors file system changes (created, modified, deleted).
    """
    def __init__(self, trigger_id: str, config: dict, services: dict, **kwargs):
        super().__init__(trigger_id, config, services, **kwargs)
        self.logger(f"FileSystemListener instance created for rule_id: {self.rule_id}", "DEBUG")
        self._observer = None
        self.path_to_watch = self.config.get("path_to_watch")
        self.events_to_watch = self.config.get("events_to_watch", []) # (COMMENT) This key seems unused, might be a future feature.
    def start(self):
        """Starts the file system monitoring thread."""
        if not self.path_to_watch or not os.path.isdir(self.path_to_watch):
            self.logger(f"File Trigger '{self.rule_id}': Path '{self.path_to_watch}' is invalid or not a directory. Trigger will not start.", "ERROR")
            return
        self.is_running = True
        event_handler = _InternalEventHandler(self)
        self._observer = Observer()
        self._observer.schedule(event_handler, self.path_to_watch, recursive=True)
        self.thread = threading.Thread(target=self._run_observer, daemon=True)
        self.thread.start()
        self.logger(f"File Trigger '{self.rule_id}': Started monitoring folder '{self.path_to_watch}'.", "INFO")
    def _run_observer(self):
        """Internal method run by the thread."""
        try:
            self._observer.start()
            while self.is_running:
                time.sleep(1)
        finally:
            if self._observer.is_alive():
                self._observer.stop()
            self._observer.join()
    def stop(self):
        """Stops the monitoring."""
        if self.is_running:
            self.is_running = False
            if self._observer and self._observer.is_alive():
                self._observer.stop()
            self.logger(f"File Trigger '{self.rule_id}': Monitoring stopped.", "INFO")
_UNUSED_SIGNATURE = 'B3Ba%m#rDeKa' # Embedded Signature
