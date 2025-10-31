#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\triggers\event_bus_trigger\processor.py JUMLAH BARIS 43 
#######################################################################

from flowork_kernel.api_contract import BaseModule, IExecutable, BaseTriggerListener
class EventBusListener(BaseTriggerListener):
    def __init__(self, trigger_id, config, services, **kwargs):
        super().__init__(trigger_id, config, services, **kwargs)
        self.event_name = self.config.get("event_name_to_listen")
    def start(self):
        if not self.event_name:
            self.logger(f"Event Bus Trigger '{self.rule_id}' failed: Event name is not configured.", "ERROR")
            return
        self.event_bus.subscribe(
            event_name=self.event_name,
            subscriber_id=f"trigger_listener::{self.rule_id}",
            callback=self.on_event_received
        )
        self.is_running = True
        self.logger(f"Event Bus Trigger '{self.rule_id}' started. Listening for '{self.event_name}'.", "INFO")
    def on_event_received(self, event_data):
        self._on_event(event_data)
    def stop(self):
        self.is_running = False
        self.logger(f"Event Bus Trigger '{self.rule_id}' stopped.", "INFO")
class EventBusTriggerModule(BaseModule, IExecutable):
    TIER = "architect"
    def __init__(self, module_id, services):
        super().__init__(module_id, services)
    def execute(self, payload: dict, config: dict, status_updater, mode='EXECUTE', **kwargs):
        event_name = config.get("event_name_to_listen", "N/A")
        status_updater(f"Event Bus Trigger (manual run). Listening for: {event_name}.", "INFO")
        if 'data' not in payload:
            payload['data'] = {}
        payload['data']['trigger_info'] = {
            'type': 'event_bus',
            'event_name': event_name,
            'event_data': {'message': 'This is a manual simulation.'}
        }
        return {"payload": payload, "output_name": "output"}
