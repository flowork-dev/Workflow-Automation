#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\services\community_addon_service\community_addon_service.py JUMLAH BARIS 35 
#######################################################################

import os
from ..base_service import BaseService
class CommunityAddonService(BaseService):
    """
    (REMASTERED - OPEN CORE) Manages community addons.
    In Open Core MVP, upload functionality is disabled.
    """
    def __init__(self, kernel, service_id: str):
        super().__init__(kernel, service_id)
        self.logger = self.kernel.write_to_log
        self.logger("CommunityAddonService: Initialized (Upload Disabled in Open Core MVP).", "INFO") # English Hardcode
    def upload_component(self, comp_type, component_id, description, tier):
        """
        (MODIFIED - OPEN CORE) This function is disabled.
        """
        self.logger(f"Attempted to upload component '{component_id}' - Operation disabled in Open Core MVP.", "WARN") # English Hardcode
        return False, "Component upload to the marketplace is disabled in this version." # English Hardcode
    def upload_model(
        self, model_filepath: str, model_id: str, description: str, tier: str
    ):
        """
        (MODIFIED - OPEN CORE) This function is disabled.
        """
        self.logger(f"Attempted to upload model '{model_id}' - Operation disabled in Open Core MVP.", "WARN") # English Hardcode
        return (
            False,
            "Model upload to the marketplace is disabled in this version.", # English Hardcode
        )
