#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\services\behavior_manager_service\behavior_manager_service.py JUMLAH BARIS 46 
#######################################################################

from ..base_service import BaseService
from .behavior_handlers import RetryHandler, LoopHandler
class BehaviorManagerService(BaseService):
    """
    Service that is dedicated to managing and applying 'behaviors'
    (like retry, loop) to a module's execution function, based on its manifest.
    This is an implementation of the Decorator Pattern.
    """
    def __init__(self, kernel, service_id: str):
        super().__init__(kernel, service_id)
        self.module_manager = self.kernel.get_service("module_manager_service")
        self.registered_behaviors = {
            "retry": RetryHandler,
            "loop": LoopHandler
        }
        self.kernel.write_to_log("Service 'BehaviorManager' initialized successfully.", "DEBUG")
    def wrap_execution(self, module_id, original_execute_func):
        """
        Wraps the original execution function with handlers based on the module's manifest.
        Args:
            module_id (str): The ID of the module to be executed.
            original_execute_func (callable): The original function that performs the execution.
        Returns:
            callable: The final, wrapped execution function.
        """
        manifest = self.module_manager.get_manifest(module_id)
        if not manifest:
            return original_execute_func
        behaviors_to_apply = manifest.get("behaviors", [])
        wrapped_func = original_execute_func
        if "retry" in behaviors_to_apply:
            retry_handler = self.registered_behaviors["retry"](self.kernel, module_id)
            wrapped_func = retry_handler.wrap(wrapped_func)
            self.kernel.write_to_log(f"BehaviorManager: Wrapping '{module_id}' with RetryHandler.", "DEBUG")
        if "loop" in behaviors_to_apply:
            loop_handler = self.registered_behaviors["loop"](self.kernel, module_id)
            wrapped_func = loop_handler.wrap(wrapped_func)
            self.kernel.write_to_log(f"BehaviorManager: Wrapping '{module_id}' with LoopHandler.", "DEBUG")
        return wrapped_func
