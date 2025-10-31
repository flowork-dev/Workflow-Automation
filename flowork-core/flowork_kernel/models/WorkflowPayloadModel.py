#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\models\WorkflowPayloadModel.py JUMLAH BARIS 18 
#######################################################################

from pydantic import BaseModel, Field
from typing import Dict, Any, List
class WorkflowPayloadModel(BaseModel):
    """
    Defines the standard structure for the payload object that flows
    between nodes in a workflow.
    This ensures that the payload always contains a 'data' dictionary
    and a 'history' list, preventing unexpected KeyError exceptions.
    """
    data: Dict[str, Any] = Field(default_factory=dict)
    history: List[Any] = Field(default_factory=list)
