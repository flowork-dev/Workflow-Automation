from flowork_kernel.kernel_logic import ServiceWorkflowProxy
from flowork_kernel.services.base_service import BaseService

class CoreLifecycleService(BaseService):
    def __init__(self, kernel, service_id: str):
        super().__init__(kernel, service_id)
        self.proxy = ServiceWorkflowProxy(kernel, service_id, "core_services/core_lifecycle.flowork")

    def start__core__lifecycle(self, *args, **kwargs):
        return self.proxy.start__core__lifecycle(*args, **kwargs)
