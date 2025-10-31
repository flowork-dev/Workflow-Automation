#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\services\event_bus_service\event_bus_service.py JUMLAH BARIS 72 
#######################################################################

import json
import threading
from typing import Dict, Any, Callable
from ..base_service import BaseService
class EventBusService(BaseService):
    """
    Service that provides a centralized message bus for different parts of the application
    to communicate without being directly coupled.
    (PERBAIKAN FASE 4) Menambahkan try-except saat serialisasi data untuk logging.
    """
    def __init__(self, kernel, service_id: str):
        super().__init__(kernel, service_id)
        self._subscribers: Dict[str, Dict[str, Callable]] = {}
        self._lock = threading.Lock() # (PENAMBAHAN KODE) Lock untuk thread-safety
        self.kernel.write_to_log("Service 'EventBus' initialized.", "DEBUG") # English Log
    def publish(self, event_name: str, event_data: Dict[str, Any], publisher_id: str = "SYSTEM"):
        """
        Publishes an event to all registered subscribers.
        """
        self.kernel.write_to_log(f"EVENT PUBLISHED: Name='{event_name}', Publisher='{publisher_id}'", "INFO") # English Log
        try:
            event_data_str = json.dumps(event_data, default=str, indent=2)
            if len(event_data_str) > 1000: # Batasi log jika data terlalu besar
                event_data_str = event_data_str[:1000] + "... (truncated)" # English Log
            self.kernel.write_to_log(f"EVENT DATA: {event_data_str}", "DETAIL") # English Log
        except Exception as e:
            self.kernel.write_to_log(f"EVENT DATA: [Could not serialize: {e}]", "DETAIL") # English Log
        with self._lock:
            if event_name in self._subscribers:
                subscribers_to_notify = list(self._subscribers[event_name].items())
            else:
                subscribers_to_notify = [] # (PENAMBAHAN KODE) Pastikan list ada
        try:
            data_copy = json.loads(json.dumps(event_data, default=str))
        except Exception as e:
            self.kernel.write_to_log(f"EventBus: Could not deep copy event data for '{event_name}'. Subscribers might receive unsafe refs. Error: {e}", "WARN") # English Hardcode
            data_copy = event_data # Fallback ke referensi asli
        for subscriber_id, callback in subscribers_to_notify:
            self.kernel.write_to_log(f"EventBus: Notifying subscriber '{subscriber_id}' for event '{event_name}'...", "DEBUG") # English Log
            try:
                threading.Thread(target=callback, args=(data_copy,)).start()
            except Exception as e:
                self.kernel.write_to_log(f"Error executing subscriber '{subscriber_id}' for event '{event_name}': {e}", "ERROR") # English Log
    def subscribe(self, event_name: str, subscriber_id: str, callback: Callable):
        """
        Subscribes a component to a specific event.
        """
        with self._lock:
            if event_name not in self._subscribers:
                self._subscribers[event_name] = {}
            self._subscribers[event_name][subscriber_id] = callback
        self.kernel.write_to_log(f"SUBSCRIBE: Component '{subscriber_id}' successfully subscribed to event '{event_name}'.", "INFO") # English Log
    def unsubscribe(self, event_name: str, subscriber_id: str):
        """
        Removes a subscriber for a specific event.
        """
        with self._lock:
            if event_name in self._subscribers and subscriber_id in self._subscribers[event_name]:
                try:
                    del self._subscribers[event_name][subscriber_id]
                    self.kernel.write_to_log(f"UNSUBSCRIBE: Component '{subscriber_id}' removed from event '{event_name}'.", "INFO") # English Log
                except Exception as e:
                    self.kernel.write_to_log(f"Error during unsubscribe for '{subscriber_id}': {e}", "WARN") # English Log
            else:
                self.kernel.write_to_log(f"UNSUBSCRIBE: No subscription found for '{subscriber_id}' on event '{event_name}'.", "DEBUG") # English Log
