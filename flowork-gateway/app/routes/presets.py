#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-gateway\app\routes\presets.py JUMLAH BARIS 93 
#######################################################################

from flask import Blueprint, jsonify
from ..models import Preset, PresetVersion
from ..extensions import db
from ..helpers import token_required, get_request_data
presets_bp = Blueprint("presets", __name__, url_prefix="/api/v1/presets")
@presets_bp.route("", methods=["GET"], endpoint="get_presets_list") # ADDED: endpoint="get_presets_list"
@token_required
def get_presets_list(current_user):
    try:
        presets = (
            Preset.query.filter_by(user_id=current_user.id)
            .order_by(Preset.name.asc())
            .all()
        )
        preset_list = [{"id": p.name, "name": p.name} for p in presets]
        return jsonify(preset_list)
    except Exception as e:
        return jsonify({"error": "Failed to fetch presets from database."}), 500
@presets_bp.route("/<preset_name>", methods=["GET"], endpoint="get_preset_data") # ADDED: endpoint="get_preset_data"
@token_required
def get_preset_data(current_user, preset_name):
    try:
        preset = Preset.query.filter_by(
            user_id=current_user.id, name=preset_name
        ).first()
        if preset:
            return jsonify(preset.workflow_data)
        else:
            return jsonify({"error": "Preset not found."}), 404
    except Exception as e:
        return jsonify({"error": "Failed to fetch preset data."}), 500
@presets_bp.route("", methods=["POST"], endpoint="save_preset_data") # ADDED: endpoint="save_preset_data"
@token_required
def save_preset_data(current_user):
    data = get_request_data()
    preset_name = data.get("name")
    workflow_data = data.get("workflow_data")
    if not preset_name or workflow_data is None:
        return (
            jsonify({"error": "Request body must contain 'name' and 'workflow_data'."}),
            400,
        )
    try:
        preset = Preset.query.filter_by(
            user_id=current_user.id, name=preset_name
        ).first()
        if preset:
            new_version = PresetVersion(
                preset_id=preset.id,
                workflow_data=preset.workflow_data,
                version_message="Auto-versioned before saving new changes.",
            )
            db.session.add(new_version)
            preset.workflow_data = workflow_data
            preset.updated_at = db.func.now()
        else:
            new_preset = Preset(
                user_id=current_user.id,
                name=preset_name,
                workflow_data=workflow_data,
            )
            db.session.add(new_preset)
        db.session.commit()
        return (
            jsonify({"status": "success", "message": f"Preset '{preset_name}' saved."}),
            201,
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to save preset to database."}), 500
@presets_bp.route("/<preset_name>", methods=["DELETE"], endpoint="delete_preset_data") # ADDED: endpoint="delete_preset_data"
@token_required
def delete_preset_data(current_user, preset_name):
    try:
        preset = Preset.query.filter_by(
            user_id=current_user.id, name=preset_name
        ).first()
        if preset:
            db.session.delete(preset)
            db.session.commit()
            return "", 204
        else:
            return jsonify({"error": "Preset not found."}), 404
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to delete preset."}), 500
