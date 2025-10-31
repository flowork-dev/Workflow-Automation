#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\services\behavior_manager_service\behavior_handlers.py JUMLAH BARIS 182 
#######################################################################

import time
import random
from flowork_kernel.api_contract import LoopConfig
from queue import Queue
import threading
import json
class BaseBehaviorHandler:
    """Base class for all behavior handlers."""
    def __init__(self, kernel, module_id):
        self.kernel = kernel
        self.module_id = module_id
        self.loc = self.kernel.get_service("localization_manager")
        self.state_manager = self.kernel.get_service("state_manager")
        self.workflow_executor = self.kernel.get_service("workflow_executor_service")
    def wrap(self, execute_func):
        raise NotImplementedError("Each handler must implement the 'wrap' method.")
class LoopHandler(BaseBehaviorHandler):
    """Handles the looping behavior for a node."""
    def wrap(self, execute_func):
        def loop_wrapper(
            payload, config, status_updater, mode, node_info, highlight, **kwargs
        ):
            enable_loop = config.get("enable_loop", False)
            if not enable_loop:
                return execute_func(
                    payload,
                    config,
                    status_updater,
                    mode,
                    node_info=node_info,
                    highlight=highlight,
                    **kwargs,
                )
            current_node_id = node_info.get("id")
            workflow_context_id = self.workflow_executor.get_current_context_id()
            loop_state_key = f"loop_progress::{workflow_context_id}::{current_node_id}"
            start_iteration = self.state_manager.get(loop_state_key, 0)
            node_name_for_log = node_info.get("name", "[Unnamed]")
            self.kernel.write_to_log(
                self.loc.get(
                    "exec_loading_loop_state",
                    node_name=node_name_for_log,
                    context_id=workflow_context_id,
                    start_iter=start_iteration,
                ),
                "DEBUG",
            )
            loop_config = LoopConfig.from_dict(config)
            loop_count = start_iteration
            last_result_obj = {"payload": payload}
            while True:
                if self.workflow_executor._stop_event.is_set():
                    self.kernel.write_to_log(
                        self.loc.get("exec_loop_stopped", node_name=node_name_for_log),
                        "WARN",
                    )
                    break
                self.workflow_executor._pause_event.wait()
                if loop_config.loop_type == LoopConfig.LOOP_TYPE_COUNT:
                    total_iterations = loop_config.iterations
                    if loop_count >= total_iterations:
                        self.kernel.write_to_log(
                            self.loc.get(
                                "exec_loop_count_finished",
                                node_name=node_name_for_log,
                                iterations=loop_count,
                            ),
                            "INFO",
                        )
                        break
                    status_updater(f"Loop {loop_count + 1}/{total_iterations}", "INFO")
                payload_for_this_iteration = last_result_obj.get("payload", {})
                execution_result = execute_func(
                    payload=payload_for_this_iteration,
                    config=config,
                    status_updater=status_updater,
                    mode=mode,
                    node_info=node_info,
                    highlight=highlight,
                    **kwargs,
                )
                if isinstance(execution_result, Exception):
                    self.kernel.write_to_log(
                        f"Error during loop iteration {loop_count + 1} for '{node_name_for_log}': {execution_result}",
                        "ERROR",
                    )
                    last_result_obj = execution_result
                    break
                last_result_obj = execution_result
                loop_count += 1
                if mode == "EXECUTE":
                    self.state_manager.set(loop_state_key, loop_count)
                if (
                    loop_config.enable_sleep
                    and mode == "EXECUTE"
                    and loop_count < loop_config.iterations
                ):
                    sleep_duration = 0
                    if loop_config.sleep_type == "static":
                        sleep_duration = loop_config.static_duration
                    elif loop_config.sleep_type == "random_range":
                        sleep_duration = random.randint(
                            loop_config.random_min, loop_config.random_max
                        )
                    if sleep_duration > 0:
                        highlight("sleeping_node", current_node_id)
                        time.sleep(sleep_duration)
            if mode == "EXECUTE":
                self.state_manager.delete(loop_state_key)
            return last_result_obj
        return loop_wrapper
class RetryHandler(BaseBehaviorHandler):
    """Handles the retry behavior for a node."""
    def wrap(self, execute_func):
        def retry_wrapper(
            payload, config, status_updater, mode, node_info, highlight, **kwargs
        ):
            retry_attempts = config.get("retry_attempts", 0)
            retry_delay = config.get("retry_delay_seconds", 5)
            node_name_for_log = node_info.get("name", "[Unnamed]")
            last_exception = None
            for attempt in range(retry_attempts + 1):
                if self.workflow_executor._stop_event.is_set():
                    break
                if attempt > 0:
                    self.kernel.write_to_log(
                        self.loc.get(
                            "exec_node_retrying_error",
                            node_name=node_name_for_log,
                            delay=retry_delay,
                            attempt=attempt,
                            total_attempts=retry_attempts,
                        ),
                        "WARN",
                    )
                    status_updater(f"Retry {attempt}/{retry_attempts}", "WARN")
                    time.sleep(retry_delay)
                result_queue = Queue()
                timeout_seconds = config.get("timeout_seconds", 0)
                def execution_target():
                    try:
                        res = execute_func(
                            payload=payload,
                            config=config,
                            status_updater=status_updater,
                            mode=mode,
                            node_info=node_info,
                            highlight=highlight,
                            **kwargs,
                        )
                        result_queue.put(res)
                    except Exception as e:
                        result_queue.put(e)
                exec_thread = threading.Thread(target=execution_target, daemon=True)
                exec_thread.start()
                try:
                    timeout = timeout_seconds if timeout_seconds > 0 else None
                    result = result_queue.get(timeout=timeout)
                except queue.Empty:
                    result = TimeoutError(
                        self.loc.get(
                            "exec_node_timeout_error",
                            node_name=node_name_for_log,
                            seconds=timeout_seconds,
                        )
                    )
                if not isinstance(result, Exception):
                    return result
                last_exception = result
            self.kernel.write_to_log(
                f"Node '{node_name_for_log}' failed after {retry_attempts} retries.",
                "ERROR",
            )
            return last_exception
        return retry_wrapper
