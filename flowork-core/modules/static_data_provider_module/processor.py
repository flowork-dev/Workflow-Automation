#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\modules\static_data_provider_module\processor.py JUMLAH BARIS 94 
#######################################################################

import json
from flowork_kernel.api_contract import (
    BaseModule,
    IExecutable,
    IDataPreviewer,
    IDynamicOutputSchema,
    IDynamicPorts,
)
class StaticDataProviderModule(
    BaseModule, IExecutable, IDataPreviewer, IDynamicOutputSchema, IDynamicPorts
):
    """
    Module to inject various static data types into a workflow.
    Serves as a powerful starting point or testing tool.
    """
    TIER = "free"
    def __init__(self, module_id, services):
        super().__init__(module_id, services)
    def execute(self, payload, config, status_updater, mode="EXECUTE", **kwargs):
        status_updater("Injecting static data...", "INFO")
        variables_to_set = config.get("variables_to_set", [])
        output_data = {}
        log_message = "Injecting static data into payload:\n"
        if not variables_to_set:
            status_updater("No data configured to inject.", "INFO")
        else:
            for var_item in variables_to_set:
                var_name = var_item.get("name")
                var_value = var_item.get("value")
                if var_name:
                    output_data[var_name] = var_value
                    log_message += f"  - '{var_name}': '{str(var_value)[:100]}...'\n"
        if isinstance(payload, dict):
            if "data" not in payload or not isinstance(payload["data"], dict):
                payload["data"] = {}
            payload["data"].update(output_data)
        else:
            payload = {"data": output_data, "history": []}
        self.logger(log_message, "DETAIL")
        status_updater("Data injected successfully.", "SUCCESS")
        final_payload = {"payload": payload}
        if (
            variables_to_set
            and len(variables_to_set) > 0
            and variables_to_set[0].get("name")
        ):
            final_payload["output_name"] = variables_to_set[0].get("name")
        else:
            final_payload["output_name"] = "success"
        return final_payload
    def get_dynamic_output_schema(self, config):
        schema = []
        variables = config.get("variables_to_set", [])
        for var in variables:
            var_name = var.get("name")
            if var_name:
                schema.append(
                    {
                        "name": f"data.{var_name}",
                        "type": "string",
                        "description": f"Static data for '{var_name}'.",
                    }
                )
        return schema
    def get_dynamic_ports(self, config):
        ports = []
        variables = config.get("variables_to_set", [])
        for var in variables:
            var_name = var.get("name")
            if var_name:
                ports.append(
                    {
                        "name": var_name,
                        "display_name": var_name,
                        "tooltip": f"Outputs the entire payload, specifically for the '{var_name}' data path.",
                    }
                )
        ports.insert(0, {"name": "success", "display_name": "Success"})
        return ports
    def get_data_preview(self, config: dict):
        variables_to_set = config.get("variables_to_set", [])
        preview_data = {
            var.get("name"): var.get("value")
            for var in variables_to_set
            if var.get("name")
        }
        return preview_data
