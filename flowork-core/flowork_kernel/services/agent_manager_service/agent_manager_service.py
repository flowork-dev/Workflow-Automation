#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\services\agent_manager_service\agent_manager_service.py JUMLAH BARIS 53 
#######################################################################

from ..base_service import BaseService
from flowork_kernel.models.AgentModel import AgentModel
import uuid
class AgentManagerService(BaseService):
    """
    Manages the lifecycle (CRUD) of AI Agents within the Flowork ecosystem.
    """
    STATE_KEY = "ai_agents"
    def __init__(self, kernel, service_id: str):
        super().__init__(kernel, service_id)
        self.state_manager = self.kernel.get_service("state_manager")
        self.kernel.write_to_log("Service 'AgentManager' initialized.", "DEBUG")
    def get_all_agents(self) -> list[dict]:
        """Returns a list of all configured agents."""
        agents_dict = self.state_manager.get(self.STATE_KEY, {})
        return list(agents_dict.values())
    def get_agent(self, agent_id: str) -> dict | None:
        """Retrieves a single agent by its ID."""
        agents_dict = self.state_manager.get(self.STATE_KEY, {})
        return agents_dict.get(str(agent_id))
    def save_agent(self, agent_data: dict) -> dict:
        """Creates or updates an agent."""
        try:
            if 'id' not in agent_data or not agent_data['id']:
                agent_data['id'] = str(uuid.uuid4())
            else:
                agent_data['id'] = str(agent_data['id'])
            agent_model = AgentModel(**agent_data)
            agents_dict = self.state_manager.get(self.STATE_KEY, {})
            agents_dict[str(agent_model.id)] = agent_model.model_dump(mode='json')
            self.state_manager.set(self.STATE_KEY, agents_dict)
            self.kernel.write_to_log(f"Agent '{agent_model.name}' saved with ID {agent_model.id}", "SUCCESS")
            return agent_model.model_dump(mode='json')
        except Exception as e:
            self.kernel.write_to_log(f"Failed to save agent: {e}", "ERROR")
            return {"error": str(e)}
    def delete_agent(self, agent_id: str) -> bool:
        """Deletes an agent by its ID."""
        agents_dict = self.state_manager.get(self.STATE_KEY, {})
        if agent_id in agents_dict:
            del agents_dict[agent_id]
            self.state_manager.set(self.STATE_KEY, agents_dict)
            self.kernel.write_to_log(f"Agent with ID {agent_id} has been deleted.", "INFO")
            return True
        self.kernel.write_to_log(f"Attempted to delete non-existent agent with ID {agent_id}.", "WARN")
        return False
