#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\core\output_schema.py JUMLAH BARIS 21 
#######################################################################

from typing import Dict, Any
class OutputVar:
    """Defines a single variable that a module guarantees to output."""
    def __init__(self, display_name: str, var_type: str, description: str = ""):
        self.display_name = display_name
        self.var_type = var_type
        self.description = description
class OutputSchema:
    """Manages the collection of output variables for a module."""
    def __init__(self, variables: Dict[str, OutputVar]):
        self.variables = variables
def create_output_schema(**kwargs: OutputVar) -> OutputSchema:
    """Factory function to easily create an OutputSchema instance."""
    return OutputSchema(kwargs)
