#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\models\ManifestModel.py JUMLAH BARIS 48 
#######################################################################

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
class PropertyModel(BaseModel):
    id: str
    type: str
    label: str
    description: Optional[str] = ""
    default: Optional[Any] = None
class PortModel(BaseModel):
    name: str
    display_name: str
    tooltip: Optional[str] = ""
class OutputSchemaModel(BaseModel):
    name: str
    type: str
    description: Optional[str] = ""
class DisplayPropertiesModel(BaseModel):
    color: Optional[str] = "#6c757d"  # default secondary color
    text_color: Optional[str] = "#FFFFFF"
class ManifestModel(BaseModel):
    id: str
    name: str
    author: str
    description: str
    type: str # e.g., "ACTION", "LOGIC", "DASHBOARD_WIDGET"
    entry_point: str
    version: Optional[str] = "1.0"
    requires_input: Optional[bool] = True
    properties: List[PropertyModel] = Field(default_factory=list)
    output_ports: List[PortModel] = Field(default_factory=list)
    requires_services: List[str] = Field(default_factory=list)
    permissions: List[str] = Field(default_factory=list)
    output_schema: List[OutputSchemaModel] = Field(default_factory=list)
    display_properties: Optional[DisplayPropertiesModel] = Field(default_factory=DisplayPropertiesModel)
    is_system: Optional[bool] = False # For widgets
    config_ui_entry_point: Optional[str] = None # For triggers
    is_service: Optional[bool] = False # For service plugins
    main_processor_file: Optional[str] = None
    dependencies_file: Optional[str] = None
    supported_languages: List[str] = Field(default_factory=list)
    is_paused: Optional[bool] = False
