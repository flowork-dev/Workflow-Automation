#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\models\NodeModel.py JUMLAH BARIS 22 
#######################################################################

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from uuid import UUID, uuid4
class NodeModel(BaseModel):
    """
    Represents the data structure for a single node in a workflow.
    Ensures that every node has a consistent and valid set of attributes.
    """
    id: UUID = Field(default_factory=uuid4)
    name: str
    x: float
    y: float
    module_id: str
    description: Optional[str] = ""
    config_values: Dict[str, Any] = Field(default_factory=dict)
