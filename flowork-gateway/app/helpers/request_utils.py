#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-gateway\app\helpers\request_utils.py JUMLAH BARIS 35 
#######################################################################

from flask import request, abort, jsonify
import json
import logging
logger = logging.getLogger(__name__)
def get_request_data(optional=False):
    """
    Parses incoming request data, supporting application/json, form data,
    and text data. Returns an empty dict if data is not found and optional=True.
    (English Hardcode)
    """
    if request.method == 'GET':
        return request.args.to_dict()
    if request.is_json:
        try:
            return request.get_json()
        except Exception as e:
            logger.error(f"Failed to parse JSON request: {e}")
            if not optional:
                abort(400, description="Invalid JSON format in request body.")
            return {}
    if request.form:
        return request.form.to_dict()
    if request.args:
        return request.args.to_dict()
    if optional:
        return {}
    else:
        abort(400, description="Missing request data. Expected JSON or form data.")
