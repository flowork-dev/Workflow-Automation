#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-gateway\app\helpers\permission_utils.py JUMLAH BARIS 35 
#######################################################################

import logging
try:
    from ..models import Role, Permission
except ImportError:
    class DummyRole: pass
    class DummyPermission: pass
    Role = DummyRole
    Permission = DummyPermission
logger = logging.getLogger(__name__)
def calculate_effective_permissions(user_or_admin_user):
    """
    Calculates the combined set of permissions based on the roles assigned to a User or AdminUser.
    Returns:
        A set of permission names (strings).
    """
    if not hasattr(user_or_admin_user, 'roles'):
        return set()
    effective_permissions = set()
    try:
        for role in user_or_admin_user.roles:
            if hasattr(role, 'permissions'):
                for permission in role.permissions:
                    if hasattr(permission, 'name'):
                        effective_permissions.add(permission.name)
    except Exception as e:
        logger.error(f"Error calculating permissions for user {getattr(user_or_admin_user, 'id', 'unknown')}: {e}")
        return set()
    return effective_permissions
