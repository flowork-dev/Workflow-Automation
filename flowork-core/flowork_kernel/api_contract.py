#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\api_contract.py JUMLAH BARIS 367 
#######################################################################

from typing import List, Dict, Any, Callable, Tuple
from abc import ABC, abstractmethod
class IWebhookProvider(ABC):
    """
    An interface for modules that can expose a webhook endpoint.
    This allows them to be triggered by external HTTP requests.
    """
    @abstractmethod
    def get_webhook_path(self, current_config: Dict[str, Any]) -> str:
        """
        Returns the specific URL path for this webhook based on its config.
        Example: '/my-custom-webhook'
        """
        raise NotImplementedError
class BaseBrainProvider(ABC):
    """
    The abstract base class (contract) that all AI Brain Providers for the Agent Host must implement.
    A brain is responsible for the core Observe-Think-Act loop.
    """
    def __init__(self, module_id: str, services: dict):
        self.kernel = services.get("kernel")
        self.loc = services.get("loc")
        self.logger = services.get("logger", print)
        self.module_id = module_id
        self.manifest = {}
        module_manager = self.kernel.get_service("module_manager_service") if self.kernel else None
        if module_manager:
            manifest_data = module_manager.get_manifest(self.module_id)
            if manifest_data:
                self.manifest = manifest_data
    @abstractmethod
    def get_provider_name(self) -> str:
        """
        Returns the display name of the brain provider.
        """
        raise NotImplementedError
    @abstractmethod
    def is_ready(self) -> tuple[bool, str]:
        """
        Checks if the provider is properly configured and ready to think.
        Returns a tuple of (is_ready: bool, message: str).
        """
        raise NotImplementedError
    @abstractmethod
    def think(self, objective: str, tools_string: str, history: list, last_observation: str) -> dict:
        """
        Takes the current state of the agent and returns a JSON object with 'thought' and 'action'.
        This is the core of the agent's decision-making process.
        """
        raise NotImplementedError
    def get_manifest(self) -> dict:
        """
        Returns the manifest data for this provider.
        """
        return self.manifest
class BaseAIProvider(ABC):
    """
    The abstract base class (contract) that all AI Providers must implement.
    [UPGRADED] Now holds its own manifest data.
    [UPGRADED V2] Now includes a standard readiness check method.
    """
    def __init__(self, kernel, manifest: dict):
        self.kernel = kernel
        self.loc = self.kernel.get_service("localization_manager")
        self.manifest = manifest
    @abstractmethod
    def get_provider_name(self) -> str:
        """
        Returns the display name of the provider.
        """
        raise NotImplementedError
    @abstractmethod
    def generate_response(self, prompt: str) -> dict:
        """
        Processes a prompt and returns a standardized dictionary.
        """
        raise NotImplementedError
    @abstractmethod
    def is_ready(self) -> tuple[bool, str]:
        """
        Checks if the provider is properly configured and ready to accept requests.
        Returns a tuple of (is_ready: bool, message: str).
        """
        raise NotImplementedError
    def get_manifest(self) -> dict:
        """
        Returns the manifest data for this provider.
        """
        return self.manifest
class IDataPreviewer(ABC):
    """
    An optional interface for modules that can provide a real-time preview
    of their potential output data based on their current configuration.
    This is the foundation for the "Data Canvas" feature.
    """
    @abstractmethod
    def get_data_preview(self, config: Dict[str, Any]) -> Any:
        """
        Executes a limited, sample version of the module's logic to return a data preview.
        This method MUST NOT have side effects and should return quickly.
        Args:
            config: The current configuration values from the properties UI.
        Returns:
            A sample of the data the module would produce (e.g., a list of dicts, a string).
        """
        raise NotImplementedError
class IDynamicOutputSchema(ABC):
    """
    An interface for modules whose output data schema can change dynamically
    based on their current configuration.
    """
    @abstractmethod
    def get_dynamic_output_schema(self, current_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Returns a list of output schema dictionaries based on the node's config.
        Example: [{'name': 'data.user_name', 'type': 'string', 'description': '...'}]
        """
        raise NotImplementedError
class IExecutable(ABC):
    """Interface for modules that can be executed in a workflow."""
    @abstractmethod
    def execute(self, payload: Dict, config: Dict, status_updater: Callable, mode: str = 'EXECUTE', **kwargs):
        raise NotImplementedError
class IDynamicPorts(ABC):
    """Interface for modules whose output ports can change dynamically."""
    @abstractmethod
    def get_dynamic_ports(self, current_config):
        raise NotImplementedError
class BaseModule:
    """
    Kelas dasar yang harus di-inherit oleh semua prosesor modul.
    Versi ini diperluas untuk mendukung Arsitektur Modul Mandiri.
    """
    def __init__(self, module_id: str, services: Dict[str, Any]):
        """
        Konstruktor baru yang menerima layanan yang dibutuhkan secara eksplisit.
        (FIXED) Now correctly assigns all injected services to self.
        """
        self.module_id = module_id
        for service_name, service_instance in services.items():
            setattr(self, service_name, service_instance)
        self.manifest = {}
        if hasattr(self, 'module_manager_service') and self.module_manager_service:
            manifest_data = self.module_manager_service.get_manifest(self.module_id)
            if manifest_data:
                self.manifest = manifest_data
        if not hasattr(self, 'loc'):
            self.loc = services.get("loc")
        if not hasattr(self, 'logger'):
            self.logger = services.get("logger", print) # Fallback to print if not provided
        self._workflow_executor_cache = None
    def on_install(self):
        """Called once when the module is first installed or discovered."""
        pass
    def on_load(self):
        """Called when the module is loaded or enabled."""
        pass
    def on_canvas_load(self, node_id: str):
        """
        Called by the CanvasManager right after a node instance is visually
        created on the canvas, providing it with its unique instance ID.
        """
        pass
    def on_unload(self):
        """Called when the module is unloaded or disabled."""
        pass
    def validate(self, config: Dict[str, Any], connected_input_ports: List[str]) -> Tuple[bool, str]:
        """
        Memvalidasi konfigurasi node saat ini.
        Metode ini harus di-override oleh modul turunan jika memerlukan validasi khusus.
        """
        return (True, "")
    def _get_executor(self):
        if self._workflow_executor_cache is None:
            self._workflow_executor_cache = getattr(self, 'workflow_executor_service', None)
        return self._workflow_executor_cache
    def pause_workflow(self):
        workflow_executor = self._get_executor()
        if workflow_executor:
            workflow_executor.pause_execution()
        else:
            if self.loc:
                self.logger(self.loc.get('api_contract_err_executor_not_requested', fallback="Error: The 'workflow_executor_service' was not requested by this module."), "ERROR")
            else:
                self.logger("Error: The 'workflow_executor_service' was not requested by this module.", "ERROR")
    def resume_workflow(self):
        workflow_executor = self._get_executor()
        if workflow_executor:
            workflow_executor.resume_execution()
        else:
            if self.loc:
                self.logger(self.loc.get('api_contract_err_executor_not_requested', fallback="Error: The 'workflow_executor_service' was not requested by this module."), "ERROR")
            else:
                self.logger("Error: The 'workflow_executor_service' was not requested by this module.", "ERROR")
    def request_manual_approval(self, message: str, callback: Callable[[str], None]):
        workflow_executor = self._get_executor()
        if workflow_executor:
            workflow_executor.request_manual_approval_from_module(
                self.module_id, message, callback
            )
        else:
            self.logger("Error: 'workflow_executor_service' not requested, cannot request approval.", "ERROR") # English Hardcode
    def publish_event(self, event_name: str, event_data: Dict[str, Any]):
        """
        (PERBAIKAN) Fungsi ini sekarang secara otomatis mengambil
        user_context dan job_id dari executor yang sedang berjalan dan
        menambahkannya ke payload event.
        (PERBAIKAN v2) Memastikan event_data adalah dict.
        """
        event_bus = getattr(self, 'event_bus', None)
        if event_bus:
            if not isinstance(event_data, dict):
                self.logger(f"Cannot publish event '{event_name}': event_data must be a dictionary, but got {type(event_data)}. Wrapping it.", "WARN") # English Hardcode
                event_data = {"data": event_data}
            workflow_executor = self._get_executor()
            event_data_to_publish = event_data.copy()
            if workflow_executor:
                current_context = workflow_executor.get_current_execution_context()
                if current_context:
                    event_data_to_publish['user_context'] = current_context.get('user_context')
                    event_data_to_publish['workflow_context_id'] = current_context.get('workflow_context_id')
            event_bus.publish(event_name, event_data_to_publish, publisher_id=self.module_id)
        else:
            if self.loc:
                self.logger(self.loc.get('api_contract_err_eventbus_not_requested', eventName=event_name, fallback=f"Error: The 'event_bus' service was not requested, cannot publish event '{event_name}'."), "ERROR")
            else:
                self.logger(f"Error: The 'event_bus' service was not requested, cannot publish event '{event_name}'.", "ERROR")
class BaseDashboardWidget(ABC):
    """
    [MODIFIED] This is now a pure abstract base class, completely decoupled from Tkinter.
    The actual UI widget in the template/theme will inherit from both this class
    and the appropriate UI framework class (e.g., ttk.Frame).
    """
    def __init__(self, kernel, widget_id: str):
        self.kernel = kernel
        self.loc = self.kernel.get_service("localization_manager")
        self.widget_id = widget_id
    @abstractmethod
    def on_widget_load(self):
        """Called when the widget is created and placed on the dashboard."""
        pass
    @abstractmethod
    def on_widget_destroy(self):
        """Called when the widget is about to be destroyed."""
        pass
    @abstractmethod
    def refresh_content(self):
        """Called to request the widget to refresh its data or view."""
        pass
    @abstractmethod
    def get_widget_state(self) -> dict:
        """
        Called by the DashboardManager when saving the layout.
        Widgets should override this to return a dictionary of their savable state.
        """
        return {}
    @abstractmethod
    def load_widget_state(self, state: dict):
        """
        Called by the DashboardManager after a widget is created and a saved state is available.
        Widgets should override this to restore their state from the dictionary.
        """
        pass
class LoopConfig:
    """
    Struktur data untuk mendefinisikan konfigurasi looping pada sebuah step.
    Ini akan digunakan dalam properti modul atau sebagai bagian dari data node.
    """
    LOOP_TYPE_COUNT = "count"
    LOOP_TYPE_CONDITION = "condition"
    def __init__(self, loop_type: str = LOOP_TYPE_COUNT, iterations: int = 1, condition_var: str = None, condition_op: str = None, condition_val: Any = None,
                 enable_sleep: bool = False, sleep_type: str = "static", static_duration: int = 1, random_min: int = 1, random_max: int = 5):
        if loop_type not in [self.LOOP_TYPE_COUNT, self.LOOP_TYPE_CONDITION]:
            raise ValueError(f"Tipe loop tidak valid: {loop_type}. Harus '{self.LOOP_TYPE_COUNT}' atau '{self.LOOP_TYPE_CONDITION}'.")
        self.loop_type = loop_type
        self.iterations = iterations
        self.condition_var = condition_var
        self.condition_op = condition_op
        self.condition_val = condition_val
        self.enable_sleep = enable_sleep
        self.sleep_type = sleep_type
        self.static_duration = static_duration
        self.random_min = random_min
        self.random_max = random_max
    def to_dict(self) -> Dict[str, Any]:
        """Mengubah objek LoopConfig menjadi dictionary."""
        return {
            "loop_type": self.loop_type,
            "iterations": self.iterations,
            "condition_var": self.condition_var,
            "condition_op": self.condition_op,
            "condition_val": self.condition_val,
            "enable_sleep": self.enable_sleep,
            "sleep_type": self.sleep_type,
            "static_duration": self.static_duration,
            "random_min": self.random_min,
            "random_max": self.random_max
        }
    @staticmethod
    def from_dict(data: Dict[str, Any]):
        """Membuat objek LoopConfig dari dictionary."""
        return LoopConfig(
            loop_type=data.get("loop_type", LoopConfig.LOOP_TYPE_COUNT),
            iterations=data.get("iterations", 1),
            condition_var=data.get("condition_var"),
            condition_op=data.get("condition_op"),
            condition_val=data.get("condition_val"),
            enable_sleep=data.get("enable_sleep", False),
            sleep_type=data.get("sleep_type", "static"),
            static_duration=data.get("static_duration", 1),
            random_min=data.get("random_min", 1),
            random_max=data.get("random_max", 5)
        )
class BaseTriggerListener:
    """
    Kelas dasar (kontrak) untuk semua modul Pemicu (Trigger).
    Setiap pemicu yang ingin mendengarkan kejadian sistem (file, proses, waktu, dll.)
    wajib mewarisi kelas ini.
    """
    def __init__(self, trigger_id: str, config: Dict[str, Any], services: Dict[str, Any], **kwargs):
        """
        Konstruktor dibuat lebih fleksibel dengan **kwargs.
        Ini akan mencegah crash jika 'rule_id' tidak dilemparkan,
        dan kita bisa memberikan peringatan yang lebih jelas.
        """
        self.trigger_id = trigger_id
        self.config = config
        self._callback = None
        self.is_running = False
        self.rule_id = kwargs.get('rule_id')
        for service_name, service_instance in services.items():
            setattr(self, service_name, service_instance)
        self.logger = getattr(self, 'logger', print)
        self.loc = getattr(self, 'loc', None) or getattr(self, 'kernel', None) and self.kernel.get_service("localization_manager")
        if not self.rule_id:
            if self.loc:
                self.logger(self.loc.get('api_contract_warn_trigger_no_ruleid', triggerId=self.trigger_id, fallback=f"CRITICAL WARNING FOR TRIGGER '{self.trigger_id}': Listener was created without a rule_id. This trigger will be unable to run a workflow."), "ERROR")
            else:
                self.logger(f"CRITICAL WARNING FOR TRIGGER '{self.trigger_id}': Listener created without rule_id. It will not be able to run a workflow.", "ERROR")
    def set_callback(self, callback: Callable[[Dict[str, Any]], None]):
        self._callback = callback
    def start(self):
        raise NotImplementedError("Setiap Pemicu harus mengimplementasikan metode 'start'.")
    def stop(self):
        raise NotImplementedError("Setiap Pemicu harus mengimplementasikan metode 'stop'.")
    def _on_event(self, event_data: Dict[str, Any]):
        if self._callback and callable(self._callback):
            try:
                if self.rule_id:
                    event_data['rule_id'] = self.rule_id
                    user_id = None
                    state_manager = getattr(self, 'state_manager', None)
                    if state_manager:
                        pass
                    self.logger(f"Trigger '{self.trigger_id}' detected an event: {event_data}", "DEBUG") # English Log
                    self._callback(event_data)
                else:
                    self.logger(f"Trigger '{self.trigger_id}' detected an event, but it was cancelled because it has no rule_id.", "WARN") # English Log
            except Exception as e:
                self.logger(f"Error during callback execution for trigger '{self.trigger_id}': {e}", "ERROR")
