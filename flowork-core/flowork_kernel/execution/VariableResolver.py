#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\execution\VariableResolver.py JUMLAH BARIS 49 
#######################################################################

import re
class VariableResolver:
    """
    A dedicated class for resolving variable placeholders within a node's configuration.
    It recursively handles dictionaries, lists, and strings.
    """
    def __init__(self, kernel):
        """
        Initializes the resolver with a kernel instance to access services.
        Args:
            kernel: The main application kernel.
        """
        self.kernel = kernel
    def resolve(self, config_item: any) -> any:
        """
        Recursively resolves variable placeholders in a given configuration item.
        Args:
            config_item: The configuration item (string, dict, list) to resolve.
        Returns:
            The configuration item with all placeholders replaced by their actual values.
        """
        variable_manager = self.kernel.get_service("variable_manager")
        if isinstance(config_item, dict):
            return {k: self.resolve(v) for k, v in config_item.items()}
        elif isinstance(config_item, list):
            return [self.resolve(elem) for elem in config_item]
        elif isinstance(config_item, str):
            pattern = r'\{\{vars\.([A-Z0-9_]+)\}\}'
            match_full = re.fullmatch(pattern, config_item)
            if match_full:
                var_name = match_full.group(1)
                if variable_manager: # MODIFIED: Use the locally fetched instance
                    return variable_manager.get_variable(var_name)
                return config_item # Fallback if service not found
            def replace_match(match):
                var_name = match.group(1)
                if variable_manager: # MODIFIED: Use the locally fetched instance
                    value = variable_manager.get_variable(var_name)
                    return str(value) if value is not None else match.group(0)
                return match.group(0) # Fallback if service not found
            return re.sub(pattern, replace_match, config_item)
        return config_item
