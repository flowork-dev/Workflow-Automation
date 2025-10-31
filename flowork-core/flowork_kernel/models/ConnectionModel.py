#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\models\ConnectionModel.py JUMLAH BARIS 22 
#######################################################################

from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID, uuid4
class ConnectionModel(BaseModel):
    """
    Represents the data structure for a connection between two nodes.
    (COMMENT) [PERBAIKAN] Mengganti 'from' dan 'to' menjadi 'source' dan 'target' untuk konsistensi dengan frontend dan menghindari reserved keywords.
    """
    id: UUID = Field(default_factory=uuid4)
    source: UUID
    target: UUID
    source_port_name: Optional[str] = None
    target_port_name: Optional[str] = None
    class Config:
        allow_population_by_field_name = True
