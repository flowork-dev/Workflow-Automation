#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\core\input_schema.py JUMLAH BARIS 25 
#######################################################################

from typing import Dict, Any
class InputVar:
    """Defines a single expected input variable for a module's payload."""
    def __init__(self, display_name: str, var_type: str, required: bool = False, description: str = ""):
        self.display_name = display_name
        self.var_type = var_type
        self.required = required
        self.description = description
class InputSchema:
    """Manages the collection of input variables for a module."""
    def __init__(self, variables: Dict[str, InputVar]):
        self.variables = variables
    def get_var(self, key: str, payload: Dict[str, Any]) -> Any:
        """Safely retrieves a variable's value from a payload."""
        return payload.get('data', {}).get(key)
def create_input_schema(**kwargs: InputVar) -> InputSchema:
    """Factory function to easily create an InputSchema instance."""
    return InputSchema(kwargs)
