#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\utils\payload_helper.py JUMLAH BARIS 22 
#######################################################################

def get_nested_value(d, key_path):
    """
    Safely retrieves a value from a nested dictionary using a dot-separated path.
    Example: get_nested_value(payload, 'data.user.name')
    """
    if not key_path or not isinstance(key_path, str):
        return None
    parts = key_path.split('.')
    val = d
    for part in parts:
        if isinstance(val, dict) and part in val:
            val = val[part]
        else:
            return None
    return val
