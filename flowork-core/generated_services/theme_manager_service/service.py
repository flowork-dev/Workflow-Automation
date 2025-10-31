from flowork_kernel.kernel_logic import ServiceWorkflowProxy
from flowork_kernel.services.base_service import BaseService

class ThemeManagerService(BaseService):
    def __init__(self, kernel, service_id: str):
        super().__init__(kernel, service_id)
        self.proxy = ServiceWorkflowProxy(kernel, service_id, "core_services/theme_manager.flowork")

    def get_all_themes(self, *args, **kwargs):
        return self.proxy.get_all_themes(*args, **kwargs)

    def get_colors(self, *args, **kwargs):
        return self.proxy.get_colors(*args, **kwargs)
