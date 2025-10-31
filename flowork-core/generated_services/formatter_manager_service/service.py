from flowork_kernel.kernel_logic import ServiceWorkflowProxy
from flowork_kernel.services.base_service import BaseService

class FormatterManagerService(BaseService):
    def __init__(self, kernel, service_id: str):
        super().__init__(kernel, service_id)
        self.proxy = ServiceWorkflowProxy(kernel, service_id, "core_services/formatter_manager.flowork")

    def get_formatter(self, *args, **kwargs):
        return self.proxy.get_formatter(*args, **kwargs)
