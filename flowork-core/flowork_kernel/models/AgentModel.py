#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\models\AgentModel.py JUMLAH BARIS 21 
#######################################################################

from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import UUID, uuid4
class AgentModel(BaseModel):
    """
    Defines the data structure for an autonomous AI Agent.
    Each agent has a brain (an AI model) and a set of tools (modules) it can use.
    """
    id: UUID = Field(default_factory=uuid4)
    name: str
    description: Optional[str] = ""
    brain_model_id: str = Field(..., description="The ID of the GGUF model file that acts as the agent's brain.")
    tool_ids: List[str] = Field(default_factory=list, description="A list of module_ids that this agent is allowed to use as tools.")
    prompt_template: Optional[str] = ""
