#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\services\agent_executor_service\agent_executor_service.py JUMLAH BARIS 120 
#######################################################################

import threading
import json
import time
import re
import os
from ..base_service import BaseService
class AgentExecutorService(BaseService):
    def __init__(self, kernel, service_id: str):
        super().__init__(kernel, service_id)
        self.module_manager = self.kernel.get_service("module_manager_service")
        self.workflow_executor = self.kernel.get_service("workflow_executor_service")
        self.ai_manager = self.kernel.get_service("ai_provider_manager_service")
        self.event_bus = self.kernel.get_service("event_bus")
        self.kernel.write_to_log("Service 'AgentExecutor' initialized.", "DEBUG")
    def run_dynamic_agent_synchronous(self, initial_payload: dict, full_prompt_template: str, connected_tools: list, ai_brain_endpoint: str, status_updater, host_node_id: str):
        self.logger(f"Starting synchronous dynamic agent run for host node {host_node_id}.", "INFO") # ADDED host_node_id for context
        current_payload = initial_payload.copy()
        if 'data' not in current_payload or not isinstance(current_payload['data'], dict):
            current_payload['data'] = {}
        conversation_history = []
        last_observation = "No actions taken yet."
        max_steps = 10
        tools_prompt_string = self._get_tools_prompt_from_nodes(connected_tools)
        objective = current_payload.get('data', {}).get('prompt', 'No objective provided in payload.')
        for i in range(max_steps):
            status_updater(f"Cycle {i+1}/{max_steps}: Thinking...", "INFO")
            if self.event_bus: self.event_bus.publish("AGENT_HOST_DISPLAY_UPDATE", {"node_id": host_node_id, "text": f"🤔 Thinking...\n(Cycle {i+1}/{max_steps})"})
            prompt_to_brain = full_prompt_template
            prompt_to_brain = prompt_to_brain.replace('{objective}', objective)
            prompt_to_brain = prompt_to_brain.replace('{tools_string}', tools_string) # [PERBAIKAN] Ini kuncinya
            prompt_to_brain = prompt_to_brain.replace('{history}', json.dumps(conversation_history, indent=2))
            prompt_to_brain = prompt_to_brain.replace('{last_observation}', last_observation)
            self.logger(f"Sending prompt to brain: {ai_brain_endpoint}", "DEBUG")
            ai_response = self.ai_manager.query_ai_by_task('text', prompt_to_brain, endpoint_id=ai_brain_endpoint)
            if "error" in ai_response:
                last_observation = f"AI Brain Error: {ai_response['error']}"
                self.logger(f"Error during agent cycle: {last_observation}", "ERROR")
                conversation_history.append({"role": "user", "content": f"Observation: {last_observation}"})
                if self.event_bus: self.event_bus.publish("AGENT_HOST_DISPLAY_UPDATE", {"node_id": host_node_id, "text": f"❌ Brain Error:\n{ai_response['error']}"})
                continue
            action_json_str = ai_response.get('data', '{}')
            self.logger(f"Brain response received: {action_json_str}", "DETAIL")
            try:
                json_match = re.search(r'\{[\s\S]*\}', action_json_str)
                if not json_match:
                    raise json.JSONDecodeError("No valid JSON object found in the AI's response.", action_json_str, 0)
                clean_json_str = json_match.group(0)
                action_data = json.loads(clean_json_str)
                thought = action_data.get("thought", action_data.get("thoughts", "No thought provided."))
                action = action_data.get("action", {})
                tool_to_use = action.get("tool_id")
                tool_data = action.get("data", {})
                conversation_history.append({"role": "assistant", "content": action_json_str})
                status_updater(f"Thought: {thought}", "INFO")
                if self.event_bus: self.event_bus.publish("AGENT_HOST_DISPLAY_UPDATE", {"node_id": host_node_id, "text": f"💡 Thought:\n{thought}"})
                if tool_to_use == "finish":
                    final_answer = action.get('final_answer', "Objective complete.")
                    status_updater(f"Agent decided the objective is complete.", "SUCCESS")
                    if self.event_bus: self.event_bus.publish("AGENT_HOST_DISPLAY_UPDATE", {"node_id": host_node_id, "text": f"✅ Finished:\n{final_answer}"})
                    return final_answer, conversation_history
                if not tool_to_use:
                    raise ValueError("AI brain failed to select a valid tool.")
                status_updater(f"Action: Using tool '{tool_to_use}'", "INFO")
                if self.event_bus: self.event_bus.publish("AGENT_HOST_DISPLAY_UPDATE", {"node_id": host_node_id, "text": f"🛠️ Using Tool: {tool_to_use}\nData: {json.dumps(tool_data, indent=2)}"})
                node_to_run = next((t for t in connected_tools if t.get('module_id') == tool_to_use), None)
                if not node_to_run:
                    raise ValueError(f"Tool '{tool_to_use}' was chosen by the AI, but it is not connected to the Agent Host.")
                if self.event_bus: self.event_bus.publish("AGENT_HOST_TOOL_HIGHLIGHT", {"tool_node_id": node_to_run['id'], "host_node_id": host_node_id})
                time.sleep(0.5)
                payload_for_tool = current_payload.copy()
                if 'data' not in payload_for_tool or not isinstance(payload_for_tool.get('data'), dict):
                    payload_for_tool['data'] = {}
                payload_for_tool['data'].update(tool_data)
                result_from_tool = self.workflow_executor.execute_workflow_synchronous(
                    nodes={node_to_run['id']: node_to_run},
                    connections={},
                    initial_payload=payload_for_tool,
                    logger=self.logger,
                    status_updater=lambda a,b,c: self.logger(f"Tool Status Update: {b} - {c}", "DETAIL"),
                    workflow_context_id=f"agent_host_step_{i}",
                    mode='EXECUTE',
                    job_status_updater=None
                )
                if isinstance(result_from_tool, Exception):
                    raise result_from_tool
                if isinstance(result_from_tool, dict) and "payload" in result_from_tool:
                    current_payload = result_from_tool["payload"]
                last_observation = json.dumps(current_payload, default=str)
                conversation_history.append({"role": "user", "content": f"Observation: {last_observation}"})
            except Exception as e:
                last_observation = f"An error occurred: {e}"
                self.logger(f"Error during agent cycle: {e}", "ERROR")
                conversation_history.append({"role": "user", "content": f"Observation: {last_observation}"})
                if self.event_bus: self.event_bus.publish("AGENT_HOST_DISPLAY_UPDATE", {"node_id": host_node_id, "text": f"❌ Error:\n{e}"})
        return "Max steps reached.", conversation_history
    def _get_tools_prompt_from_nodes(self, tool_nodes: list) -> str:
        """
        Generates a string listing available tools for the AI's prompt.
        """
        tools_list = []
        plugin_manager = self.kernel.get_service("plugin_manager_service")
        for node_data in tool_nodes:
            manifest = None
            component_id = node_data.get('module_id')
            if self.module_manager:
                manifest = self.module_manager.get_manifest(component_id)
            if not manifest and plugin_manager:
                manifest = plugin_manager.get_manifest(component_id)
            if manifest:
                tools_list.append(
                    f"- tool_id: {manifest.get('id')}\n  name: {manifest.get('name')}\n  description: {manifest.get('description')}"
                )
        return "\n".join(tools_list)
