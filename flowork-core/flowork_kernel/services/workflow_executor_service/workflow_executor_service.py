#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\services\workflow_executor_service\workflow_executor_service.py JUMLAH BARIS 968 
#######################################################################

import json
import time
import threading
import logging
import re
import os
import uuid
import random
import sys
import psutil
import traceback
from queue import Queue
from ..base_service import BaseService
from flowork_kernel.api_contract import LoopConfig
from flowork_kernel.execution.VariableResolver import VariableResolver
from flowork_kernel.exceptions import PermissionDeniedError
import queue
import requests
try:
    from app.extensions import sse_message_queue
except ImportError:
    sse_message_queue = None
_thread_local = threading.local()
class WorkflowExecutorService(BaseService):
    def __init__(self, kernel, service_id: str):
        super().__init__(kernel, service_id)
        self._paused = False
        self._pause_event = threading.Event()
        self._pause_event.set()
        self._stop_event = threading.Event()
        self.behavior_manager = None
        self.last_job_status_updater = None
        self._connection_history = {}
        self._history_lock = threading.Lock()
        self.variable_resolver = VariableResolver(self.kernel)
        self.logger("Service 'WorkflowExecutor' initialized.", "DEBUG")
        self.process = psutil.Process(os.getpid())
        self._ai_analyzer_cache = None
        self._event_bus_cache = None
        self._metrics_service_cache = None
        self._manual_approval_callbacks = {}
        self.is_busy = False # Status internal
        self._busy_lock = threading.Lock()
    @property
    def ai_analyzer(self):
        if self._ai_analyzer_cache is None:
            self._ai_analyzer_cache = self.kernel.get_service("ai_analyzer_service")
        return self._ai_analyzer_cache
    @property
    def event_bus(self):
        if self._event_bus_cache is None:
            self._event_bus_cache = self.kernel.get_service("event_bus")
        return self._event_bus_cache
    @property
    def metrics_service(self):
        if self._metrics_service_cache is None:
            self._metrics_service_cache = self.kernel.get_service("metrics_service")
        return self._metrics_service_cache
    def is_running(self) -> bool:
        """
        Checks if the executor is currently processing any workflow.
        """
        with self._busy_lock:
            return self.is_busy
    def get_current_execution_context(self):
        """
        Mengambil konteks (job_id, user_context) dari thread-local storage.
        """
        return getattr(_thread_local, 'execution_context', None)
    def request_manual_approval_from_module(self, module_id, message, callback_func):
        """
        Dipanggil oleh BaseModule. Menyimpan callback dan memublikasikan event
        dengan konteks yang benar.
        """
        context = self.get_current_execution_context()
        if not context:
            self.logger(f"Manual approval request from '{module_id}' failed: No execution context found.", "ERROR")
            return
        workflow_context_id = context.get('workflow_context_id')
        user_context = context.get('user_context')
        self.logger(f"Manual approval requested by module '{module_id}': {message}", "WARN")
        callback_key = f"{workflow_context_id}::{module_id}"
        self._manual_approval_callbacks[callback_key] = callback_func
        if self.event_bus:
            event_data = {
                "module_id": module_id,
                "message": message,
                "workflow_context_id": workflow_context_id,
                "user_context": user_context
            }
            self.event_bus.publish(
                "MANUAL_APPROVAL_REQUESTED", event_data, publisher_id=module_id
            )
        else:
            self.logger("EventBus not available, cannot broadcast approval request.", "ERROR")
    def _record_connection_event(self, context_id, connection_id, payload):
        with self._history_lock:
            if context_id not in self._connection_history:
                self._connection_history[context_id] = {}
            if "steps" not in self._connection_history[context_id]:
                self._connection_history[context_id]["steps"] = []
            history_entry = {
                "connection_id": connection_id,
                "payload": payload,
                "timestamp": time.time(),
            }
            self._connection_history[context_id]["steps"].append(history_entry)
    def get_connection_history(self, context_id, connection_id=None):
        with self._history_lock:
            history = self._connection_history.get(context_id, {})
            try:
                serializable_history = json.loads(json.dumps(history, default=str))
                return serializable_history
            except (TypeError, OverflowError):
                safe_steps = []
                for step in history.get("steps", []):
                    try:
                        json.dumps(step["payload"], default=str)
                        safe_steps.append(step)
                    except (TypeError, OverflowError):
                        safe_steps.append({
                            "payload": f"<Unserializable data type: {type(step['payload']).__name__}>",
                            "connection_id": step["connection_id"],
                            "timestamp": step["timestamp"]
                        })
                history["steps"] = safe_steps
                return history
    def get_current_context_id(self):
        context = self.get_current_execution_context()
        return context.get('workflow_context_id') if context else None
    def _get_fresh_settings(self, user_id=None):
        loc_manager = self.kernel.get_service("localization_manager")
        if loc_manager:
            return loc_manager.get_all_settings(user_id=user_id)
        self.kernel.write_to_log(
            "Failed to get fresh settings: LocalizationManager not found.", "ERROR"
        )
        return {}
    def _execute_global_error_handler(self, original_error, failed_workflow_id, user_context):
        user_id = user_context.get("id") if user_context else None
        fresh_settings = self._get_fresh_settings(user_id=user_id)
        handler_preset_name = fresh_settings.get("global_error_workflow_preset")
        if not fresh_settings.get("global_error_handler_enabled") or not handler_preset_name:
            self.kernel.write_to_log(
                f"GLOBAL ERROR HANDLER: Skipped, feature disabled or no preset defined for user {user_id}.",
                "WARN",
            )
            return
        self.kernel.write_to_log(
            f"GLOBAL ERROR HANDLER: Triggering preset '{handler_preset_name}' for user {user_id}...",
            "WARN",
        )
        preset_manager = self.kernel.get_service("preset_manager")
        if not preset_manager:
            self.kernel.write_to_log(
                f"GLOBAL ERROR HANDLER: Failed, PresetManager service not available.",
                "ERROR",
            )
            return
        handler_workflow_data = preset_manager.get_preset_data(handler_preset_name, user_id=user_id)
        if not handler_workflow_data:
            self.kernel.write_to_log(
                f"GLOBAL ERROR HANDLER: Failed, preset '{handler_preset_name}' not found for user {user_id}.",
                "ERROR",
            )
            return
        error_payload = {
            "data": {
                "failed_workflow_id": failed_workflow_id,
                "error_message": str(original_error),
                "error_time": time.time(),
            },
            "history": [],
        }
        try:
            nodes = {
                node["id"]: node for node in handler_workflow_data.get("nodes", [])
            }
            connections = {
                conn["id"]: conn
                for conn in handler_workflow_data.get("connections", [])
            }
            self.execute_workflow_synchronous(
                nodes=nodes,
                connections=connections,
                initial_payload=error_payload,
                logger=self.kernel.write_to_log,
                status_updater=lambda a, b, c: None,
                highlighter=lambda a, b: None,
                workflow_context_id=f"error_handler_for_{failed_workflow_id}",
                mode="EXECUTE",
                job_status_updater=None,
                user_context=user_context,
                preset_name=handler_preset_name
            )
            self.kernel.write_to_log(
                f"GLOBAL ERROR HANDLER: Execution of preset '{handler_preset_name}' completed.",
                "SUCCESS",
            )
        except Exception as handler_e:
            self.kernel.write_to_log(
                f"GLOBAL ERROR HANDLER: An error occurred while EXECUTING the error handler itself: {handler_e}",
                "ERROR",
            )
    def execute_workflow(
        self,
        nodes,
        connections,
        initial_payload,
        logger=None,
        status_updater=None,
        highlighter=None,
        workflow_context_id="default_workflow",
        mode="EXECUTE",
        job_status_updater=None,
        on_complete=None,
        start_node_id=None,
        user_context=None,
        global_loop_config=None,
        preset_name="Unknown Preset",
    ):
        def log_and_broadcast(message, level="INFO", source="Executor", context_override=None):
            effective_logger = logger or self.kernel.write_to_log
            current_context_id = context_override if context_override else workflow_context_id
            log_user_id = user_context.get('id') if user_context else None
            node_id_match = re.match(r"Node: (.+)", source)
            node_id_for_log = node_id_match.group(1) if node_id_match else source
            if current_context_id and log_user_id and sse_message_queue:
                try:
                    log_data = {
                        "job_id": current_context_id,
                        "node_id": node_id_for_log,
                        "status": level.upper(),
                        "message": message,
                        "timestamp": datetime.datetime.utcnow().isoformat()
                    }
                    sse_message = json.dumps({
                        "event": "log_update",
                        "data": log_data,
                        "user_id": log_user_id # PENTING untuk filtering SSE
                    })
                    sse_message_queue.put(sse_message)
                except Exception as e:
                    print(f"FATAL: Failed to publish log to In-Memory Queue: {e}")
            if callable(effective_logger):
                import inspect
                sig = inspect.signature(effective_logger)
                num_params = len(sig.parameters)
                if num_params == 3 and "source" in sig.parameters:
                     effective_logger(message, level, source=source)
                elif num_params == 2:
                     effective_logger(f"[{source}] {message}", level)
                else:
                     effective_logger(f"[{level}] [{source}] {message}")
            if self.event_bus:
                self.event_bus.publish(
                    "WORKFLOW_LOG_ENTRY",
                    {
                        "workflow_context_id": current_context_id,
                        "timestamp": time.time(),
                        "source": source,
                        "message": message,
                        "level": level.upper(),
                        "user_context": user_context
                    },
                )
        exec_thread = threading.Thread(
            target=self.execute_workflow_synchronous,
            args=(
                nodes,
                connections,
                initial_payload,
                log_and_broadcast,
                status_updater,
                highlighter,
                workflow_context_id,
                mode,
                job_status_updater,
                on_complete,
                start_node_id,
                user_context,
                global_loop_config,
                preset_name,
            ),
        )
        exec_thread.daemon = True
        exec_thread.start()
        return exec_thread
    def execute_workflow_synchronous(
        self,
        nodes,
        connections,
        initial_payload,
        logger,
        status_updater,
        highlighter,
        workflow_context_id,
        mode,
        job_status_updater,
        on_complete=None,
        start_node_id=None,
        user_context=None,
        global_loop_config=None,
        preset_name="Unknown Preset",
    ):
        with self._busy_lock:
            self.is_busy = True
        _thread_local.execution_context = {
            'workflow_context_id': workflow_context_id,
            'user_context': user_context
        }
        log = logger
        def node_status_updater_and_broadcaster(node_id, message, level):
            if callable(status_updater):
                status_updater(node_id, message, level)
            node_name = nodes.get(node_id, {}).get("name", "Unknown Node")
            source_name = f"Node: {node_name}"
            log(message, level.upper(), source=source_name)
        def highlight_func(event_type, item_id):
            if callable(highlighter):
                highlighter(event_type, item_id)
            if self.event_bus and event_type == "active_connection":
                event_data = {
                    "workflow_context_id": workflow_context_id,
                    "connection_id": item_id,
                    "status": "ACTIVE",
                    "user_context": user_context
                }
                self.event_bus.publish("CONNECTION_STATUS_UPDATE", event_data)
        with self._history_lock:
            if workflow_context_id in self._connection_history:
                del self._connection_history[workflow_context_id]
                log(
                    f"Cleared previous run history for context: {workflow_context_id}",
                    "DEBUG",
                    source="Executor",
                )
        if self.behavior_manager is None:
            self.behavior_manager = self.kernel.get_service("behavior_manager_service")
        precise_job_start_time = time.time()
        status_data_running = {
            "status": "RUNNING",
            "start_time": precise_job_start_time,
            "preset_name": preset_name
        }
        if self.event_bus:
            self.event_bus.publish(
                "WORKFLOW_JOB_STATUS_UPDATE",
                {
                    "job_id": workflow_context_id,
                    "status_data": status_data_running,
                    "user_context": user_context
                },
            )
        if callable(job_status_updater):
            job_status_updater(workflow_context_id, status_data_running)
        self._paused = False
        self._pause_event.set()
        self._stop_event.clear()
        if mode == "SIMULATE":
            log("===== STARTING SIMULATION MODE =====", "WARN", source="Executor")
        if not nodes:
            log("Execution failed: No nodes to execute.", "ERROR", source="Executor")
            _thread_local.execution_context = None
            with self._busy_lock:
                self.is_busy = False
            return ValueError("No nodes to execute.")
        state_manager = self.kernel.get_service("state_manager")
        user_id = user_context.get("id") if user_context else None
        checkpoint_key = f"checkpoint::{workflow_context_id}"
        saved_checkpoint = (
            state_manager.get(checkpoint_key, user_id=user_id)
            if state_manager and user_id
            else None
        )
        final_payload = None
        workflow_start_time = time.perf_counter()
        loop_config_data = (
            global_loop_config if isinstance(global_loop_config, dict) else {}
        )
        is_loop_enabled = loop_config_data.get("isEnabled", False)
        total_iterations = (
            loop_config_data.get("iterations", 1) if is_loop_enabled else 1
        )
        try:
            for current_iteration in range(total_iterations):
                if self._stop_event.is_set():
                    log("Global loop stopped by user.", "WARN", source="Executor")
                    break
                log(
                    f"--- Starting Workflow Iteration {current_iteration + 1}/{total_iterations} ---",
                    "INFO",
                    source="Executor",
                )
                if (
                    saved_checkpoint
                    and isinstance(saved_checkpoint, dict)
                    and mode == "EXECUTE"
                    and user_id
                ):
                    resume_node_id = saved_checkpoint.get("node_id")
                    resume_payload = saved_checkpoint.get("payload")
                    if resume_node_id and resume_payload is not None:
                        node_name = nodes.get(resume_node_id, {}).get(
                            "name", resume_node_id
                        )
                        log(
                            f"CHECKPOINT FOUND: Resuming workflow from state after '{node_name}'.",
                            "WARN",
                            source="Executor",
                        )
                        if state_manager:
                            state_manager.delete(checkpoint_key, user_id=user_id)
                        final_payload = self._find_and_execute_next_nodes(
                            current_node_id=resume_node_id,
                            execution_result=resume_payload,
                            nodes=nodes,
                            connections=connections,
                            log=log,
                            update_status=node_status_updater_and_broadcaster,
                            highlight=highlight_func,
                            workflow_context_id=workflow_context_id,
                            mode=mode,
                            job_status_updater=job_status_updater,
                            user_context=user_context,
                            preset_name=preset_name,
                        )
                        saved_checkpoint = None
                elif start_node_id:
                    log(
                        f"Service call: Starting workflow execution from specific node '{nodes.get(start_node_id, {}).get('name', start_node_id)}'.",
                        "DEBUG",
                        source="Executor",
                    )
                    final_payload = self._traverse_and_execute(
                        start_node_id,
                        nodes,
                        connections,
                        initial_payload,
                        log,
                        node_status_updater_and_broadcaster,
                        highlight_func,
                        workflow_context_id,
                        mode,
                        job_status_updater,
                        user_context=user_context,
                        preset_name=preset_name,
                    )
                else:
                    all_node_ids = set(nodes.keys())
                    nodes_with_incoming = set(
                        conn_data["target"]
                        for conn_data in connections.values()
                        if conn_data.get("target") and conn_data.get("type") != "tool"
                    )
                    start_nodes = all_node_ids - nodes_with_incoming
                    if not start_nodes:
                        log(
                            "Execution failed: No start node found (a node without incoming connections).",
                            "ERROR",
                            source="Executor",
                        )
                        raise ValueError("No start node found.")
                    final_payload = self._run_all_flows_sequentially(
                        start_nodes,
                        nodes,
                        connections,
                        log,
                        node_status_updater_and_broadcaster,
                        highlight_func,
                        initial_payload,
                        workflow_context_id,
                        mode,
                        job_status_updater,
                        user_context=user_context,
                        preset_name=preset_name,
                    )
                if is_loop_enabled and current_iteration < total_iterations - 1:
                    is_delay_enabled = loop_config_data.get("isDelayEnabled", False)
                    if is_delay_enabled and mode == "EXECUTE":
                        delay_type = loop_config_data.get("delayType", "static")
                        sleep_duration = 0
                        if delay_type == "static":
                            sleep_duration = loop_config_data.get("delayStatic", 1)
                        elif delay_type == "random_range":
                            min_delay = loop_config_data.get("delayRandomMin", 1)
                            max_delay = loop_config_data.get("delayRandomMax", 5)
                            sleep_duration = random.randint(min_delay, max_delay)
                        if sleep_duration > 0:
                            log(
                                f"Global Delay: Waiting for {sleep_duration} seconds before next iteration...",
                                "INFO",
                                source="Executor",
                            )
                            time.sleep(sleep_duration)
            if isinstance(final_payload, Exception):
                raise final_payload
        except PermissionDeniedError as e:
            final_payload = e
            log(
                f"!!! PERMISSION DENIED IN WORKFLOW: {e}", "CRITICAL", source="Executor"
            )
        except Exception as e:
            final_payload = e
            log(
                f"!!! FATAL ERROR IN WORKFLOW EXECUTOR: {e}", "ERROR", source="Executor"
            )
            log(traceback.format_exc(), "DEBUG", source="Executor")
        finally:
            if callable(job_status_updater):
                job_status_updater(
                    workflow_context_id, {"status": "RUNNING", "active_node_id": None}
                )
            highlight_func("clear_highlights", None)
            final_status_code = ""
            final_status_message = ""
            log_level = "INFO"
            if self._stop_event.is_set():
                final_status_code = "STOPPED"
                final_status_message = "Execution was stopped by user."
                log_level = "WARN"
            elif isinstance(final_payload, Exception):
                final_status_code = "FAILED"
                final_status_message = str(final_payload)
                log_level = "ERROR"
            else:
                final_status_code = "SUCCEEDED"
                final_status_message = "Execution completed successfully."
                log_level = "SUCCESS"
            final_status_data = {
                "status": final_status_code,
                "start_time": precise_job_start_time,
                "preset_name": preset_name,
                "end_time": time.time(),
            }
            if final_status_code == "FAILED":
                final_status_data["error"] = final_status_message
            else:
                final_status_data["result"] = final_status_message
            if callable(job_status_updater):
                job_status_updater(workflow_context_id, final_status_data)
            if self.event_bus:
                self.event_bus.publish(
                    "WORKFLOW_JOB_STATUS_UPDATE",
                    {
                        "job_id": workflow_context_id,
                        "status_data": final_status_data,
                        "user_context": user_context
                    },
                )
            log(f"Workflow finished with status: {final_status_code}. {final_status_message}", log_level, source="Executor")
            if self.metrics_service:
                metric_status_label = "failed" if final_status_code in ["FAILED", "STOPPED"] else "succeeded"
                self.metrics_service.WORKFLOWS_TOTAL.labels(status=metric_status_label).inc()
                workflow_duration = time.perf_counter() - workflow_start_time
                self.metrics_service.WORKFLOW_DURATION.observe(workflow_duration)
            if (
                final_status_code == "FAILED"
                and mode == "EXECUTE"
                and not workflow_context_id.startswith("error_handler_for_")
            ):
                 self._execute_global_error_handler(final_payload, workflow_context_id, user_context)
            if mode == "SIMULATE":
                log("===== SIMULATION FINISHED =====", "WARN", source="Executor")
            history = self.get_connection_history(workflow_context_id)
            if callable(on_complete):
                try:
                    on_complete(final_payload if not isinstance(final_payload, Exception) else None, history)
                except Exception as cb_e:
                    log(f"Error in on_complete callback: {cb_e}", "ERROR", source="Executor")
            if self.ai_analyzer and mode == "EXECUTE":
                log(
                    f"Executor: Attempting to dispatch analysis request for context '{workflow_context_id}'",
                    "INFO",
                    source="Executor",
                )
                try:
                    fresh_settings = self._get_fresh_settings(user_id=user_id)
                    if fresh_settings.get("ai_copilot_enabled", True):
                        self.ai_analyzer.request_analysis(workflow_context_id)
                    else:
                        log("AI Co-pilot analysis skipped (disabled in user settings).", "WARN", source="Executor")
                except Exception as analyzer_e:
                     log(f"Error dispatching analysis request: {analyzer_e}", "ERROR", source="Executor")
            _thread_local.execution_context = None
            with self._busy_lock:
                self.is_busy = False
        return final_payload
    def execute_standalone_node(
        self,
        node_data: dict,
        job_id: str,
        user_context: dict,
        mode: str = "EXECUTE",
    ):
        """
        Menjalankan satu node secara mandiri sebagai workflow 'Quick Run'.
        """
        self.logger(f"Received request for standalone execution. Job ID: {job_id}", "INFO")
        module_manager = self.kernel.get_service("module_manager_service")
        if not module_manager:
            self.logger("Cannot execute standalone node: ModuleManagerService is not available.", "CRITICAL")
            return
        module_id = node_data.get("module_id")
        config_values = node_data.get("config_values", {})
        if not module_id:
            self.logger("Cannot execute standalone node: 'module_id' is missing.", "ERROR")
            return
        manifest = module_manager.get_manifest(module_id)
        if not manifest:
            plugin_manager = self.kernel.get_service("plugin_manager_service")
            if plugin_manager:
                manifest = plugin_manager.get_manifest(module_id)
            if not manifest:
                 tools_manager = self.kernel.get_service("tools_manager_service")
                 if tools_manager:
                    manifest = tools_manager.get_manifest(module_id)
        if not manifest:
            self.logger(f"Cannot execute standalone node: Manifest for '{module_id}' not found.", "ERROR")
            return
        preset_name = f"Quick Run: {manifest.get('name', module_id)}"
        nodes = {
            "quick_run_node": {
                "id": "quick_run_node",
                "name": manifest.get("name", module_id),
                "module_id": module_id,
                "config_values": config_values,
            }
        }
        connections = {}
        api_server_service = self.kernel.get_service("api_server_service")
        if not api_server_service:
            self.logger("Cannot execute standalone node: ApiServerService is not available for status updates.", "CRITICAL")
            return
        self.logger(f"Dispatching standalone node '{module_id}' to execution thread.", "INFO")
        self.execute_workflow(
            nodes=nodes,
            connections=connections,
            initial_payload={"data": {}, "history": []}, # Payload awal kosong
            logger=self.kernel.write_to_log,
            status_updater=None, # Akan di-wrap oleh execute_workflow
            highlighter=None, # Akan di-wrap oleh execute_workflow
            workflow_context_id=job_id,
            job_status_updater=api_server_service.update_job_status,
            start_node_id="quick_run_node", # Tentukan node mana yang harus dijalankan
            mode=mode,
            user_context=user_context,
            preset_name=preset_name,
        )
    def stop_execution(self):
        self.kernel.write_to_log("STOP request received.", "INFO")
        self._stop_event.set()
        self._pause_event.set()
        if not self.is_running():
            self.logger("Executor was idle when STOP received. Forcing status update.", "WARN")
            current_context = self.get_current_execution_context()
            job_id = current_context.get('workflow_context_id') if current_context else "unknown_stopped_job"
            user_context = current_context.get('user_context') if current_context else None
            final_status_data = {
                "status": "STOPPED",
                "message": "Workflow stopped by user (post-execution).",
                "end_time": time.time(),
            }
            if callable(self.last_job_status_updater):
                 self.last_job_status_updater(job_id, final_status_data)
            if self.event_bus:
                self.event_bus.publish(
                    "WORKFLOW_JOB_STATUS_UPDATE",
                    {
                        "job_id": job_id,
                        "status_data": final_status_data,
                        "user_context": user_context
                    },
                )
    def pause_execution(self):
        if self._paused: return
        self._paused = True
        self._pause_event.clear()
        current_context = self.get_current_execution_context()
        current_job_id = current_context.get('workflow_context_id') if current_context else None
        status_data_paused = {"status": "PAUSED"}
        if callable(self.last_job_status_updater) and current_job_id:
            self.last_job_status_updater(current_job_id, status_data_paused)
        if self.event_bus and current_job_id:
            self.event_bus.publish(
                "WORKFLOW_JOB_STATUS_UPDATE",
                {
                    "job_id": current_job_id,
                    "status_data": status_data_paused,
                    "user_context": current_context.get('user_context') if current_context else None
                },
            )
        self.logger("Workflow execution paused.", "WARN")
    def resume_execution(self):
        if not self._paused: return
        self._paused = False
        self._pause_event.set()
        current_context = self.get_current_execution_context()
        current_job_id = current_context.get('workflow_context_id') if current_context else None
        status_data_running = {"status": "RUNNING"}
        if callable(self.last_job_status_updater) and current_job_id:
            self.last_job_status_updater(
                current_job_id, status_data_running
            )
        if self.event_bus and current_job_id:
            self.event_bus.publish(
                "WORKFLOW_JOB_STATUS_UPDATE",
                {
                    "job_id": current_job_id,
                    "status_data": status_data_running,
                    "user_context": current_context.get('user_context') if current_context else None
                },
            )
        self.logger("Workflow execution resumed.", "INFO")
    def _run_all_flows_sequentially(
        self,
        start_nodes, nodes, connections, log, update_status, highlight,
        initial_payload, workflow_context_id, mode, job_status_updater,
        user_context, preset_name
    ):
        final_payload = None
        last_exception = None
        results = []
        for start_node_id in start_nodes:
            if self._stop_event.is_set(): break
            payload_copy = json.loads(json.dumps(initial_payload, default=str))
            result = self._traverse_and_execute(
                start_node_id, nodes, connections, payload_copy, log, update_status, highlight,
                workflow_context_id, mode, job_status_updater,
                user_context, preset_name
            )
            if isinstance(result, Exception):
                last_exception = result
            else:
                results.append(result)
        if results:
            final_payload = results[-1]
            if len(results) > 1:
                log(f"Multiple start nodes detected. Returning result from last successful branch.", "WARN", source="Executor")
        if last_exception and not final_payload:
            return last_exception
        return final_payload if final_payload is not None else initial_payload
    def _find_and_execute_next_nodes(
        self,
        current_node_id, execution_result, nodes, connections, log, update_status, highlight,
        workflow_context_id="default_workflow", mode: str = "EXECUTE", job_status_updater=None,
        user_context=None, preset_name="Unknown Preset"
    ):
        if self._stop_event.is_set():
            return execution_result
        payload_for_next = {}
        expected_output_name = None
        if isinstance(execution_result, Exception):
            node_name = nodes.get(current_node_id, {}).get("name", "[Unnamed Node]")
            log(
                f"Node '{node_name}' failed. Checking for 'error' port connection.",
                "WARN",
                source="Executor",
            )
            payload_for_next = {
                "data": {
                    "error": str(execution_result),
                    "failed_node_id": current_node_id,
                },
                "history": [],
            }
            expected_output_name = "error"
        else:
            if isinstance(execution_result, dict):
                payload_for_next = execution_result.get("payload", execution_result)
                expected_output_name = execution_result.get("output_name")
            else:
                payload_for_next = {"data": {"value": execution_result}, "history": []}
                expected_output_name = None
        if isinstance(payload_for_next, dict):
             if "data" not in payload_for_next: payload_for_next["data"] = {}
             if "user_context" not in payload_for_next["data"]:
                 payload_for_next["data"]["user_context"] = user_context
        next_nodes_to_execute = []
        outgoing_connections = [
            (conn_id, conn_data)
            for conn_id, conn_data in connections.items()
            if conn_data.get("source") == current_node_id
            and conn_data.get("type", "data") != "tool"
        ]
        if expected_output_name is not None:
            for conn_id, conn_data in outgoing_connections:
                if conn_data.get("source_port_name") == expected_output_name:
                    highlight("active_connection", conn_id)
                    self._record_connection_event(
                        workflow_context_id, conn_id, payload_for_next
                    )
                    next_nodes_to_execute.append(
                        (conn_id, conn_data.get("target"), payload_for_next)
                    )
        elif expected_output_name is None and len(outgoing_connections) > 0:
            found_default_output = False
            for conn_id, conn_data in outgoing_connections:
                if conn_data.get("source_port_name") == "output" or conn_data.get("source_port_name") is None:
                    highlight("active_connection", conn_id)
                    self._record_connection_event(
                        workflow_context_id, conn_id, payload_for_next
                    )
                    next_nodes_to_execute.append(
                        (conn_id, conn_data.get("target"), payload_for_next)
                    )
                    found_default_output = True
            if not found_default_output and len(outgoing_connections) == 1:
                conn_id, conn_data = outgoing_connections[0]
                highlight("active_connection", conn_id)
                self._record_connection_event(
                    workflow_context_id, conn_id, payload_for_next
                )
                next_nodes_to_execute.append(
                    (conn_id, conn_data.get("target"), payload_for_next)
                )
            elif not found_default_output and len(outgoing_connections) > 1:
                log(
                    f"Execution path halted. Node '{nodes.get(current_node_id, {}).get('name', '[Unnamed Node]')}' has multiple output ports but did not specify which one to take.",
                    "WARN",
                    source="Executor",
                )
        if not next_nodes_to_execute:
            node_name_for_log = nodes.get(current_node_id, {}).get(
                "name", "[Unnamed Node]"
            )
            log(
                f"Execution path finished. Node '{node_name_for_log}' has no outgoing connections from port '{expected_output_name or 'default'}'.",
                "INFO",
                source="Executor",
            )
            return execution_result
        last_result = execution_result
        for (conn_id, next_node_id, payload) in next_nodes_to_execute:
            if not next_node_id:
                continue
            payload_copy = json.loads(json.dumps(payload, default=str))
            last_result = self._traverse_and_execute(
                next_node_id,
                nodes, connections, payload_copy, log, update_status, highlight,
                workflow_context_id, mode, job_status_updater,
                user_context, preset_name
            )
        return last_result
    def _traverse_and_execute(
        self,
        current_node_id, nodes, connections, payload, log, update_status, highlight,
        workflow_context_id, mode, job_status_updater,
        user_context=None, preset_name="Unknown Preset"
    ):
        self.last_job_status_updater = job_status_updater
        if self._stop_event.is_set():
            return payload
        self._pause_event.wait()
        if current_node_id not in nodes:
            log(f"Node ID '{current_node_id}' not found in workflow definition.", "ERROR", source="Executor")
            return payload
        node_info = nodes[current_node_id]
        node_name_for_log = node_info.get("name", "[Unnamed Node]")
        module_id_to_run = node_info.get("module_id")
        start_time = time.perf_counter()
        mem_before = self.process.memory_info().rss
        payload_size_in = sys.getsizeof(payload)
        execution_result = None
        try:
            if callable(job_status_updater) and mode == "EXECUTE":
                job_status_updater(
                    workflow_context_id,
                    {"status": "RUNNING", "active_node_id": current_node_id}
                )
            if self.event_bus and mode == "EXECUTE":
                running_metric = {
                    "workflow_context_id": workflow_context_id,
                    "node_id": current_node_id,
                    "status": "RUNNING",
                    "timestamp": time.time(),
                    "user_context": user_context
                }
                self.event_bus.publish("NODE_EXECUTION_METRIC", running_metric)
            module_instance = self.kernel.get_component_instance(module_id_to_run)
            if not module_instance:
                raise ValueError(f"Module '{module_id_to_run}' not found, is paused, or failed to load.")
            log(
                f"Executing node '{node_name_for_log}' (Module: {module_id_to_run})",
                "INFO",
                source=f"Node: {node_name_for_log}",
            )
            node_config = node_info.get("config_values", {})
            node_config["__internal_node_id"] = current_node_id
            resolved_config = self.variable_resolver.resolve(node_config)
            if isinstance(payload, dict):
                if "data" not in payload or not isinstance(payload["data"], dict):
                    payload["data"] = {}
                payload["data"]["user_context"] = user_context
            else:
                payload = {"data": {"value": payload, "user_context": user_context}, "history": []}
            kwargs_for_execute = {}
            if module_id_to_run == "agent_host":
                kwargs_for_execute["connections"] = connections
            def safe_status_updater(msg, lvl):
                if callable(update_status):
                    update_status(current_node_id, msg, lvl.upper())
            def core_execution_function(payload, config, status_updater, mode, **kwargs):
                 kwargs['user_context'] = user_context
                 return module_instance.execute(payload, config, status_updater, mode, **kwargs)
            wrapped_executor = self.behavior_manager.wrap_execution(
                module_id_to_run, core_execution_function
            )
            execution_result = wrapped_executor(
                payload=payload,
                config=resolved_config,
                status_updater=safe_status_updater,
                mode=mode,
                node_info=node_info,
                highlight=highlight,
                **kwargs_for_execute,
            )
            if not self._stop_event.is_set():
                return self._find_and_execute_next_nodes(
                    current_node_id, execution_result, nodes, connections, log,
                    update_status, highlight, workflow_context_id, mode, job_status_updater,
                    user_context, preset_name
                )
            else:
                return payload
        except Exception as e:
            execution_result = e
            log(
                f"An error occurred while executing node '{node_name_for_log}': {e}",
                "ERROR",
                source=f"Node: {node_name_for_log}",
            )
            if callable(update_status):
                update_status(current_node_id, str(e), "ERROR")
            return self._find_and_execute_next_nodes(
                current_node_id, execution_result, nodes, connections, log,
                update_status, highlight, workflow_context_id, mode, job_status_updater,
                user_context, preset_name
            )
        finally:
            if mode == "EXECUTE":
                end_time = time.perf_counter()
                mem_after = self.process.memory_info().rss
                payload_size_out = sys.getsizeof(execution_result)
                metric_status = ("ERROR" if isinstance(execution_result, Exception) else "SUCCESS")
                metric_data = {
                    "workflow_context_id": workflow_context_id,
                    "preset_name": preset_name,
                    "node_id": current_node_id,
                    "node_name": node_name_for_log,
                    "module_id": module_id_to_run,
                    "status": metric_status,
                    "execution_time_ms": (end_time - start_time) * 1000,
                    "memory_usage_bytes": mem_after - mem_before,
                    "payload_size_in_bytes": payload_size_in,
                    "payload_size_out_bytes": payload_size_out,
                    "timestamp": time.time(),
                    "user_context": user_context
                }
                if self.event_bus:
                    self.event_bus.publish("NODE_EXECUTION_METRIC", metric_data)
