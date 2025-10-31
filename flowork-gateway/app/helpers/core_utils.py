#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-gateway\app\helpers\core_utils.py JUMLAH BARIS 40 
#######################################################################

import logging
try:
    from flowork_kernel.singleton import Singleton
    from flowork_kernel.api_contract import UserContext
except ImportError:
    class Singleton:
        @staticmethod
        def get_service(name):
            return None
    class UserContext:
        def __init__(self, **kwargs):
            pass
logger = logging.getLogger(__name__)
def _inject_user_data_to_core(user_id, subscription_data, permissions):
    """
    Injects essential user data into the Core Engine's execution context.
    This is required when the Gateway delegates a task to the in-process Core Kernel.
    """
    try:
        core_service = Singleton.get_service("user_context_service")
        if core_service:
            context = UserContext(
                user_id=user_id,
                subscription=subscription_data,
                permissions=permissions
            )
            core_service.set_current_user_context(context)
            logger.debug(f"Injected user {user_id} context to Core.")
        else:
            logger.warning("Core user_context_service not found for injection.")
    except Exception as e:
        logger.error(f"Failed to inject user data to Core: {e}")
    pass
