#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\execution\LoopHandler.py JUMLAH BARIS 105 
#######################################################################

import time
import random
from ..utils.type_converter import to_number
class LoopHandler:
    """
    Manages the entire lifecycle of a loop for a node execution.
    Handles count-based and condition-based loops, including delays.
    """
    def __init__(self, kernel, core_executor_func):
        """
        Initializes the loop handler.
        Args:
            kernel: The main application kernel.
            core_executor_func (function): The core function that executes a single node attempt.
        """
        self.kernel = kernel
        self.loc = self.kernel.get_service("localization_manager")
        self.state_manager = self.kernel.get_service("state_manager")
        self.core_executor_func = core_executor_func
    def execute_with_loop(self, payload: dict, config: dict, node_info: dict, context_id: str, mode: str):
        """
        Wraps the execution of a node with looping logic if enabled in the config.
        Args:
            payload: The current workflow payload.
            config: The resolved configuration for the node.
            node_info: The dictionary containing all node data.
            context_id: The unique ID for the current workflow execution context.
            mode: The execution mode ('EXECUTE' or 'SIMULATE').
        Returns:
            The final payload after the loop completes or the first error encountered.
        """
        node_id = node_info.get("id")
        node_name = node_info.get("name", "[Unnamed]")
        loop_state_key = f"loop_progress::{context_id}::{node_id}"
        start_iteration = self.state_manager.get(loop_state_key, 0)
        if start_iteration > 0:
            self.kernel.write_to_log(f"Resuming loop for node '{node_name}' from iteration {start_iteration + 1}", "INFO") # English Log
        loop_count = start_iteration
        current_payload = payload
        while True:
            if self.kernel.get_service("workflow_executor_service")._stop_event.is_set():
                self.kernel.write_to_log(f"Loop for node '{node_name}' stopped by user.", "WARN") # English Log
                break
            self.kernel.get_service("workflow_executor_service")._pause_event.wait()
            loop_type = config.get('loop_type', 'count')
            if loop_type == 'count':
                total_iterations = config.get('loop_iterations', 1)
                if loop_count >= total_iterations:
                    self.kernel.write_to_log(f"Count-based loop for '{node_name}' finished after {loop_count} iterations.", "INFO") # English Log
                    break
            elif loop_type == 'condition':
                if self._check_condition(current_payload, config):
                    self.kernel.write_to_log(f"Condition for loop on node '{node_name}' met. Exiting loop.", "INFO") # English Log
                    break
            execution_result = self.core_executor_func(current_payload, config, node_info, context_id, mode)
            if isinstance(execution_result, Exception):
                self.kernel.write_to_log(f"Error during loop iteration {loop_count + 1} for node '{node_name}': {execution_result}", "ERROR") # English Log
                current_payload = execution_result # (COMMENT) Propagate the error
                break
            if isinstance(execution_result, dict) and "payload" in execution_result:
                current_payload = execution_result.get("payload", current_payload)
            else:
                current_payload = execution_result
            loop_count += 1
            if mode == 'EXECUTE':
                self.state_manager.set(loop_state_key, loop_count)
            self._handle_sleep(config, node_name, mode)
        if mode == 'EXECUTE':
            self.state_manager.delete(loop_state_key) # (COMMENT) Clean up loop state
        return current_payload
    def _check_condition(self, payload: dict, config: dict) -> bool:
        var_path = config.get('loop_condition_var')
        operator = config.get('loop_condition_op')
        target_value = config.get('loop_condition_val')
        if not var_path:
            return True # (COMMENT) Exit loop if condition var is not set
        from ..utils.payload_helper import get_nested_value
        actual_value = get_nested_value(payload, var_path)
        if isinstance(actual_value, (int, float)):
            target_value = to_number(target_value)
        elif isinstance(actual_value, bool):
            target_value = str(target_value).lower() == 'true'
        if operator == '==': return actual_value == target_value
        if operator == '!=': return actual_value != target_value
        return False
    def _handle_sleep(self, config: dict, node_name: str, mode: str):
        if config.get('enable_sleep', False) and mode == 'EXECUTE':
            sleep_duration = 0
            if config.get('sleep_type') == 'static':
                sleep_duration = config.get('static_duration', 1)
                self.kernel.write_to_log(f"Loop on '{node_name}': Sleeping for {sleep_duration} seconds.", "INFO") # English Log
            elif config.get('sleep_type') == 'random_range':
                min_sleep = config.get('random_min', 1)
                max_sleep = config.get('random_max', 5)
                sleep_duration = random.randint(min_sleep, max_sleep)
                self.kernel.write_to_log(f"Loop on '{node_name}': Sleeping for a random duration of {sleep_duration}s.", "INFO") # English Log
            if sleep_duration > 0:
                time.sleep(sleep_duration)
