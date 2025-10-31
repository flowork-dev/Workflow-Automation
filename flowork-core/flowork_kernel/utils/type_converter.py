#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\utils\type_converter.py JUMLAH BARIS 19 
#######################################################################

def to_number(value):
    """
    Safely converts a value to an integer or float.
    Returns the number if successful, otherwise returns None.
    """
    try:
        return int(value)
    except (ValueError, TypeError):
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
