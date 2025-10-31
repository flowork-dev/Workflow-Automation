#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\execution\CheckpointManager.py JUMLAH BARIS 58 
#######################################################################

class CheckpointManager:
    """
    Abstracts the process of saving and loading workflow state (checkpoints).
    This keeps the main executor clean from state management details.
    """
    def __init__(self, kernel):
        """
        Initializes the checkpoint manager.
        Args:
            kernel: The main application kernel to access state manager.
        """
        self.kernel = kernel
        self.state_manager = self.kernel.get_service("state_manager")
    def save(self, context_id: str, node_id: str, payload: dict, node_name: str):
        """
        Saves the current state of the workflow as a checkpoint.
        Args:
            context_id: The unique ID for the current workflow execution.
            node_id: The ID of the node after which the state is being saved.
            payload: The payload to save.
            node_name: The name of the node for logging purposes.
        """
        if not self.state_manager:
            self.kernel.write_to_log("CheckpointManager Error: StateManager service not available.", "ERROR")
            return
        checkpoint_key = f"checkpoint::{context_id}"
        checkpoint_data = {
            "node_id": node_id,
            "payload": payload
        }
        self.state_manager.set(checkpoint_key, checkpoint_data)
        self.kernel.write_to_log(f"CHECKPOINT: Workflow state saved after node '{node_name}'.", "INFO")
    def load(self, context_id: str):
        """
        Loads a checkpoint for a given workflow context.
        Args:
            context_id: The unique ID for the workflow execution.
        Returns:
            A tuple (resume_node_id, resume_payload) or (None, None) if not found.
        """
        if not self.state_manager:
            return None, None
        checkpoint_key = f"checkpoint::{context_id}"
        saved_checkpoint = self.state_manager.get(checkpoint_key)
        if saved_checkpoint and isinstance(saved_checkpoint, dict):
            resume_node_id = saved_checkpoint.get("node_id")
            resume_payload = saved_checkpoint.get("payload")
            if resume_node_id and resume_payload is not None:
                self.state_manager.delete(checkpoint_key) # Consume the checkpoint
                return resume_node_id, resume_payload
        return None, None
