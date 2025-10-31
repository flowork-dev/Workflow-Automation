#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\plugins\agent_host\processor.py JUMLAH BARIS 73 
#######################################################################

from flowork_kernel.api_contract import BaseModule, IExecutable, IDataPreviewer
import json
import time
class AgentHost(BaseModule, IExecutable, IDataPreviewer):
    TIER = "architect"
    def __init__(self, module_id, services):
        super().__init__(module_id, services)
        self.agent_executor = services.get("agent_executor_service")
        self.workflow_executor = self.kernel.get_service("workflow_executor_service")
    def execute(self, payload: dict, config: dict, status_updater, mode='EXECUTE', **kwargs): # ADD CODE
        if not self.agent_executor:
            return {"payload": {"data": {"error": "AgentExecutorService is not available, cannot run agent."}}, "output_name": "error"}
        node_instance_id = config.get('__internal_node_id')
        connected_tools = kwargs.get('connected_tools', [])
        connected_brain_node = kwargs.get('connected_brain')
        connected_prompt_node = kwargs.get('connected_prompt')
        if not connected_brain_node:
            error_msg = "Agent Host 'AI Brain' port is not connected." # English Hardcode
            if 'data' not in payload or not isinstance(payload['data'], dict): payload['data'] = {}
            payload['data']['error'] = error_msg
            return {"payload": payload, "output_name": "error"}
        if not connected_prompt_node:
            error_msg = "Agent Host 'Prompt' port is not connected." # English Hardcode
            if 'data' not in payload or not isinstance(payload['data'], dict): payload['data'] = {}
            payload['data']['error'] = error_msg
            return {"payload": payload, "output_name": "error"}
        status_updater("Getting prompt template from connected node...", "INFO") # English Log
        sub_workflow_result = self.workflow_executor.execute_workflow_synchronous(
            nodes={connected_prompt_node['id']: connected_prompt_node},
            connections={},
            initial_payload=payload,
            logger=self.logger, status_updater=lambda a,b,c: None,
            workflow_context_id=f"get_template_for_agent", mode=mode,
            job_status_updater=None
        )
        prompt_template_payload = sub_workflow_result.get('payload', {}) if isinstance(sub_workflow_result, dict) else {}
        from flowork_kernel.utils.payload_helper import get_nested_value
        prompt_template = get_nested_value(prompt_template_payload, 'data.final_prompt')
        if not prompt_template:
            self.logger("Could not find 'data.final_prompt', trying fallback 'data.prompt_template'", "DEBUG") # English Log
            prompt_template = get_nested_value(prompt_template_payload, 'data.prompt_template')
        if not prompt_template or not isinstance(prompt_template, str):
            error_msg = "The connected Prompt node did not return a valid string template in 'data.final_prompt' or 'data.prompt_template'." # English Hardcode
            return {"payload": {"data": {"error": error_msg}}, "output_name": "error"}
        brain_config = connected_brain_node.get('config_values', {})
        ai_brain_endpoint = brain_config.get('selected_ai_provider')
        if not ai_brain_endpoint:
            error_msg = "Connected Brain node does not have an AI Provider selected." # English Hardcode
            if 'data' not in payload or not isinstance(payload['data'], dict): payload['data'] = {}
            payload['data']['error'] = error_msg
            return {"payload": payload, "output_name": "error"}
        final_answer, interaction_log = self.agent_executor.run_dynamic_agent_synchronous(
            initial_payload=payload,
            full_prompt_template=prompt_template,
            connected_tools=connected_tools,
            ai_brain_endpoint=ai_brain_endpoint,
            status_updater=status_updater,
            host_node_id=node_instance_id
        )
        if 'data' not in payload or not isinstance(payload['data'], dict):
            payload['data'] = {}
        payload['data']['agent_final_answer'] = final_answer
        payload['data']['agent_interaction_log'] = interaction_log
        return {"payload": payload, "output_name": "success"}
    def get_data_preview(self, config: dict):
        return [{'status': 'preview_not_available', 'reason': 'Agent execution is a live, complex process dependent on connected nodes.'}] # English Hardcode
