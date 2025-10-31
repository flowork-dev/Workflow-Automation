#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\utils\file_helper.py JUMLAH BARIS 25 
#######################################################################

import re
def sanitize_filename(name: str) -> str:
    """
    Cleans a string to make it a valid filename.
    It removes characters that are illegal in Windows, Linux, and macOS filenames,
    and replaces whitespace with underscores.
    Args:
        name (str): The original filename or string.
    Returns:
        str: A sanitized, safe filename.
    """
    if not isinstance(name, str):
        name = str(name)
    sanitized = re.sub(r'[<>:"/\\|?*]', '', name)
    sanitized = re.sub(r'\s+', '_', sanitized)
    if not sanitized:
        return "unnamed_file"
    return sanitized
