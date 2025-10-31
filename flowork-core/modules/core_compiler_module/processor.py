#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\modules\core_compiler_module\processor.py JUMLAH BARIS 83 
#######################################################################

import os
import json
import re
from flowork_kernel.api_contract import BaseModule, IExecutable, IDataPreviewer
class CoreCompilerModule(BaseModule, IExecutable, IDataPreviewer):
    """
    This module reads .flowork files from core_services and generates
    the corresponding Python service classes in generated_services.
    """
    TIER = "architect"
    def __init__(self, module_id, services):
        super().__init__(module_id, services)
        self.core_services_path = os.path.join(self.kernel.project_root_path, "core_services")
        self.generated_services_path = os.path.join(self.kernel.project_root_path, "generated_services")
    def _sanitize_for_method_name(self, name):
        """Converts 'Some Name' to 'some_name'."""
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('[\s-]+', '_', s1).lower()
    def execute(self, payload: dict, config: dict, status_updater, mode='EXECUTE', **kwargs): # ADD CODE
        status_updater("Starting Core Service compilation...", "INFO")
        os.makedirs(self.generated_services_path, exist_ok=True)
        root_init_path = os.path.join(self.generated_services_path, "__init__.py")
        if not os.path.exists(root_init_path):
            with open(root_init_path, 'w') as f:
                pass # Create empty file
        for filename in os.listdir(self.core_services_path):
            if not filename.endswith(".flowork"):
                continue
            preset_path_rel = os.path.join("core_services", filename).replace("\\", "/")
            service_id = filename.replace(".flowork", "")
            class_name = "".join(word.capitalize() for word in service_id.split('_')) + "Service"
            status_updater(f"Processing service workflow: {filename}", "INFO")
            service_dir = os.path.join(self.generated_services_path, f"{service_id}_service")
            os.makedirs(service_dir, exist_ok=True)
            sub_init_path = os.path.join(service_dir, "__init__.py")
            if not os.path.exists(sub_init_path):
                 with open(sub_init_path, 'w') as f:
                    pass
            service_file_path = os.path.join(service_dir, "service.py")
            try:
                with open(os.path.join(self.core_services_path, filename), 'r', encoding='utf-8') as f:
                    workflow_data = json.load(f)
                nodes = {node['id']: node for node in workflow_data.get('nodes', [])}
                connections = workflow_data.get('connections', [])
                all_node_ids = set(nodes.keys())
                nodes_with_incoming = set(conn['to'] for conn in connections)
                start_node_ids = all_node_ids - nodes_with_incoming
                code_lines = [
                    "from flowork_kernel.kernel_logic import ServiceWorkflowProxy",
                    "from flowork_kernel.services.base_service import BaseService",
                    "",
                    f"class {class_name}(BaseService):",
                    "    def __init__(self, kernel, service_id: str):",
                    "        super().__init__(kernel, service_id)",
                    f"        self.proxy = ServiceWorkflowProxy(kernel, service_id, \"{preset_path_rel}\")",
                    ""
                ]
                if not start_node_ids:
                    status_updater(f"WARNING: No start nodes found in {filename}. Service will have no methods.", "WARN")
                else:
                    for start_node_id in start_node_ids:
                        method_name = self._sanitize_for_method_name(nodes[start_node_id]['name'])
                        code_lines.append(f"    def {method_name}(self, *args, **kwargs):")
                        code_lines.append(f"        return self.proxy.{method_name}(*args, **kwargs)")
                        code_lines.append("")
                with open(service_file_path, 'w', encoding='utf-8') as f:
                    f.write("\n".join(code_lines))
                status_updater(f"Successfully generated service file at: {os.path.relpath(service_file_path, self.kernel.project_root_path)}", "SUCCESS")
            except Exception as e:
                status_updater(f"Failed to process {filename}: {e}", "ERROR")
        return {"payload": payload, "output_name": "success"}
    def get_data_preview(self, config: dict):
        """
        Provides a sample of what this module might output for the Data Canvas.
        """
        return [{'status': 'preview_not_available', 'reason': 'This is a system compiler action.'}]
