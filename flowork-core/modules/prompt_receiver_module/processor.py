#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\modules\prompt_receiver_module\processor.py JUMLAH BARIS 53 
#######################################################################

from flowork_kernel.api_contract import BaseModule, IExecutable, IDataPreviewer
class PromptReceiverModule(BaseModule, IExecutable, IDataPreviewer):
    """
    [REFACTORED] No longer an active listener. This module now acts as a passive
    entry point for workflows initiated by UI widgets. Its execute method
    simply passes the payload it receives to the next node.
    """
    TIER = "free"
    def __init__(self, module_id, services):
        super().__init__(module_id, services)
        self.node_instance_id = None
    def on_canvas_load(self, node_id: str):
        """
        Called by the CanvasManager right after this node is placed on the canvas.
        """
        self.node_instance_id = node_id
        self.logger(
            f"Receiver node '{self.node_instance_id}' is ready on the canvas.", "INFO"
        )  # English Log
    def execute(
        self, payload, config, status_updater, mode="EXECUTE", **kwargs
    ):  # ADD CODE
        """
        When this node is triggered, it simply passes the received payload
        to its output port to continue the flow.
        """
        self.node_instance_id = config.get(
            "__internal_node_id", self.node_instance_id or self.module_id
        )
        status_updater(f"Passing data through...", "INFO")  # English Log
        status_updater("Data received and passed.", "SUCCESS")  # English Log
        return {"payload": payload, "output_name": "output"}
    def _copy_node_id_to_clipboard(self, node_id):
        """Copies the node ID to the clipboard."""
        pass
    def get_data_preview(self, config: dict):
        """
        TODO: Implement the data preview logic for this module.
        This method should return a small, representative sample of the data
        that the 'execute' method would produce.
        It should run quickly and have no side effects.
        """
        self.logger(
            f"'get_data_preview' is not yet implemented for {self.module_id}", "WARN"
        )
        return [{"status": "preview not implemented"}]
