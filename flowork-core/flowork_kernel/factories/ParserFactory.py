#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\factories\ParserFactory.py JUMLAH BARIS 26 
#######################################################################

class ParserFactory:
    """
    The central factory for creating data parser instances.
    This is the only class that should directly talk to the FormatterManagerService.
    """
    @staticmethod
    def create_parser(kernel, formatter_id: str):
        """
        Creates a formatter instance based on the requested ID.
        Args:
            kernel: The main kernel instance.
            formatter_id (str): The ID of the desired formatter (e.g., 'csv_formatter').
        Returns:
            A formatter instance object, or None if not found.
        """
        formatter_manager = kernel.get_service("formatter_manager_service")
        if formatter_manager:
            return formatter_manager.get_formatter(formatter_id)
        return None
