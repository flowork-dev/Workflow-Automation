#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\services\ai_architect_service\ai_architect_service.py JUMLAH BARIS 99 
#######################################################################

import json
import os
import re
from ..base_service import BaseService
try:
    from llama_cpp import Llama
    LLAMA_CPP_AVAILABLE = True
except ImportError:
    LLAMA_CPP_AVAILABLE = False
class AiArchitectService(BaseService):
    """
    [MODIFIKASI] Menambah ukuran context window untuk model lokal.
    """
    def __init__(self, kernel, service_id: str):
        super().__init__(kernel, service_id)
        self.module_manager = self.kernel.get_service("module_manager_service")
        self.ai_manager = self.kernel.get_service("ai_provider_manager_service")
        self.kernel.write_to_log("Service 'AiArchitectService' initialized.", "DEBUG")
    def _get_available_tools_prompt(self):
        if not self.module_manager:
            return "No tools available."
        tools = []
        for mod_id, mod_data in self.module_manager.loaded_modules.items():
            manifest = mod_data.get("manifest", {})
            if manifest.get("type") not in ["LOGIC", "ACTION", "CONTROL_FLOW"]:
                continue
            if "ui_provider" in manifest.get("permissions", []):
                continue
            tool_info = f"- module_id: {mod_id}\n  name: {manifest.get('name')}\n  description: {manifest.get('description')}"
            tools.append(tool_info)
        return "\n".join(tools)
    def generate_workflow_from_prompt(self, user_prompt: str):
        if not self.ai_manager:
            raise ConnectionError("AIProviderManagerService is not available.")
        available_tools = self._get_available_tools_prompt()
        system_prompt = f"""
You are an expert Flowork workflow architect. Your task is to design a workflow based on the user's request.
You have the following modules (tools) available to you:
--- AVAILABLE TOOLS ---
{available_tools}
--- END OF TOOLS ---
Based on the user's request, you must return ONLY a valid JSON object.
The JSON object must have two keys: "nodes" and "connections".
- The "nodes" array should contain objects, each with a unique "id" (use a placeholder like "node_1", "node_2"), "name", "module_id" (from the tool list), and initial x/y coordinates.
- The "connections" array should contain objects connecting the nodes using their placeholder IDs in the "from" and "to" fields.
- The first node should ALWAYS be the "set_variable_module" with the name "START".
Example of a valid response for a simple request:
{{
  "nodes": [
    {{
      "id": "node_1",
      "name": "START",
      "module_id": "set_variable_module",
      "x": 100,
      "y": 100
    }},
    {{
      "id": "node_2",
      "name": "Tampilkan Popup Sederhana",
      "module_id": "debug_popup_module",
      "x": 300,
      "y": 100
    }}
  ],
  "connections": [
    {{
      "from": "node_1",
      "to": "node_2"
    }}
  ]
}}
Now, design a workflow for the following user request. Remember to only use the tools provided and return ONLY the JSON object.
"""
        self.kernel.write_to_log("AI Architect is consulting the default Text AI...", "INFO")
        full_prompt = f"{system_prompt}\n\nUSER REQUEST: \"{user_prompt}\""
        response = self.ai_manager.query_ai_by_task('text', full_prompt)
        if "error" in response:
            raise ConnectionError(f"AI Architect failed: {response['error']}")
        response_text = response.get("data", "{}").strip()
        try:
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if not json_match:
                raise ValueError("No valid JSON object found in the AI's response.")
            json_string = json_match.group(0)
            workflow_graph = json.loads(json_string)
            if "nodes" not in workflow_graph or "connections" not in workflow_graph:
                raise ValueError("AI response is missing 'nodes' or 'connections' key.")
            self.kernel.write_to_log("AI Architect successfully generated a workflow graph.", "SUCCESS")
            return workflow_graph
        except (json.JSONDecodeError, ValueError) as e:
            self.kernel.write_to_log(f"AI Architect failed to parse the LLM response: {e}\nRaw response: {response_text}", "ERROR")
            raise ValueError(f"The AI returned an invalid workflow structure. Raw Response: {response_text}. Error: {e}")
