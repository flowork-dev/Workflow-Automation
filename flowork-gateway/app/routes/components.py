#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-gateway\app\routes\components.py JUMLAH BARIS 78 
#######################################################################

from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
import logging
comp_bp = Blueprint('components', __name__)
logger = logging.getLogger(__name__)
@comp_bp.route('/', methods=['GET'])
@jwt_required()
def get_component_list():
    """
    [NEW] Mengambil daftar komponen (modules, plugins, tools, triggers).
    """
    user_id = get_jwt_identity()
    comp_type = request.args.get('type')
    if not comp_type:
        return jsonify({"error": "Query parameter 'type' is required"}), 400
    try:
        installer_service = current_app.kernel.get_service("community_addon_service")
        if not installer_service:
            logger.error("CommunityAddonService not found in kernel.")
            return jsonify({"error": "Server configuration error"}), 500
        component_list = installer_service.get_component_list_for_user(comp_type, user_id)
        return jsonify(component_list), 200
    except Exception as e:
        logger.error(f"Error fetching component list for type {comp_type}: {e}")
        return jsonify({"error": f"Failed to fetch component list: {e}"}), 500
@comp_bp.route('/install', methods=['POST'])
@jwt_required()
def request_component_install():
    """
    [NEW] Menerima request instalasi komponen (Async).
    """
    user_id = get_jwt_identity()
    data = request.json
    comp_type = data.get('component_type')
    comp_id = data.get('component_id')
    if not comp_type or not comp_id:
        return jsonify({"error": "component_type and component_id are required"}), 400
    try:
        installer_service = current_app.kernel.get_service("community_addon_service")
        if not installer_service:
            logger.error("CommunityAddonService not found in kernel.")
            return jsonify({"error": "Server configuration error"}), 500
        installer_service.start_installation_async(comp_type, comp_id, user_id)
        logger.info(f"User {user_id} requested install for {comp_id}. Job passed to worker.")
        return jsonify({"message": "Installation request received"}), 202
    except Exception as e:
        logger.error(f"Error requesting component install for {comp_id}: {e}")
        return jsonify({"error": f"Failed to request installation: {e}"}), 500
@comp_bp.route('/uninstall', methods=['POST'])
@jwt_required()
def request_component_uninstall():
    """
    [NEW] Menerima request un-instalasi komponen (Async).
    """
    user_id = get_jwt_identity()
    data = request.json
    comp_type = data.get('component_type')
    comp_id = data.get('component_id')
    if not comp_type or not comp_id:
        return jsonify({"error": "component_type and component_id are required"}), 400
    try:
        installer_service = current_app.kernel.get_service("community_addon_service")
        if not installer_service:
            logger.error("CommunityAddonService not found in kernel.")
            return jsonify({"error": "Server configuration error"}), 500
        installer_service.start_uninstallation_async(comp_type, comp_id, user_id)
        logger.info(f"User {user_id} requested uninstall for {comp_id}. Job passed to worker.")
        return jsonify({"message": "Uninstallation request received"}), 202
    except Exception as e:
        logger.error(f"Error requesting component uninstall for {comp_id}: {e}")
        return jsonify({"error": f"Failed to request uninstallation: {e}"}), 500
