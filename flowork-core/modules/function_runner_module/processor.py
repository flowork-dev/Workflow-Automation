#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\modules\function_runner_module\processor.py JUMLAH BARIS 59 
#######################################################################

import traceback
from flowork_kernel.api_contract import BaseModule, IExecutable #, IConfigurableUI
from flowork_kernel.api_contract import IDataPreviewer
class FunctionRunnerModule(BaseModule, IExecutable, IDataPreviewer): #, IConfigurableUI
    TIER = "architect"
    def __init__(self, module_id, services):
        super().__init__(module_id, services)
    def execute(self, payload: dict, config: dict, status_updater, mode='EXECUTE', **kwargs): # ADD CODE
        code_to_run = config.get("function_code", "")
        if not code_to_run:
            return payload
        exec_globals = {
            '__builtins__': {
                'print': self.logger,
                'abs': abs, 'all': all, 'any': any, 'bin': bin, 'bool': bool, 'bytearray': bytearray,
                'bytes': bytes, 'callable': callable, 'chr': chr, 'complex': complex, 'delattr': delattr,
                'dict': dict, 'dir': dir, 'divmod': divmod, 'enumerate': enumerate, 'filter': filter,
                'float': float, 'format': format, 'frozenset': frozenset, 'getattr': getattr,
                'hasattr': hasattr, 'hash': hash, 'hex': hex, 'id': id, 'int': int, 'isinstance': isinstance,
                'issubclass': issubclass, 'iter': iter, 'len': len, 'list': list, 'map': map, 'max': max,
                'min': min, 'next': next, 'object': object, 'oct': oct, 'ord': ord, 'pow': pow,
                'property': property, 'range': range, 'repr': repr, 'reversed': reversed, 'round': round,
                'set': set, 'setattr': setattr, 'slice': slice, 'sorted': sorted, 'str': str,
                'sum': sum, 'super': super, 'tuple': tuple, 'type': type, 'zip': zip
            }
        }
        exec_locals = {
            "payload": payload,
            "log": self.logger,
            "kernel": self.kernel,
            "args": payload.get('data', {}).get('args', ()),
            "kwargs": payload.get('data', {}).get('kwargs', {})
        }
        try:
            exec(code_to_run, exec_globals, exec_locals)
            return exec_locals.get("payload")
        except Exception as e:
            error_trace = traceback.format_exc()
            self.logger(f"Error executing Function Runner (Nano) code:\n{error_trace}", "ERROR")
            payload['error'] = str(e)
            return {"payload": payload, "output_name": "error"}
    def create_properties_ui(self, parent_frame, get_current_config, available_vars):
        pass
    def get_data_preview(self, config: dict):
        """
        TODO: Implement the data preview logic for this module.
        This method should return a small, representative sample of the data
        that the 'execute' method would produce.
        It should run quickly and have no side effects.
        """
        self.logger(f"'get_data_preview' is not yet implemented for {self.module_id}", 'WARN')
        return [{'status': 'preview not implemented'}]
