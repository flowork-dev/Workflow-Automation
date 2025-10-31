#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-gateway\app\routes\user_state.py JUMLAH BARIS 96 
#######################################################################

from flask import Blueprint, jsonify, request, current_app
from ..extensions import db
from ..models import User, State # Import State model
from ..helpers import crypto_auth_required # Gunakan crypto auth untuk endpoint user
user_state_bp = Blueprint("user_state", __name__, url_prefix="/api/v1/user/state")
FAVORITE_PRESETS_KEY = "favorite_presets" # English Hardcode
FAVORITE_COMPONENTS_KEY = "favorite_components" # English Hardcode
@user_state_bp.route(f"/{FAVORITE_PRESETS_KEY}", methods=["GET"])
@crypto_auth_required
def get_favorite_presets(current_user):
    """
    Mengambil daftar ID preset favorit untuk pengguna saat ini.
    """
    try:
        state_entry = State.query.filter_by(user_id=current_user.id, key=FAVORITE_PRESETS_KEY).first()
        if state_entry and state_entry.value:
            favorites = state_entry.value if isinstance(state_entry.value, list) else []
            current_app.logger.info(f"[State Route] Retrieved {len(favorites)} favorite presets for user {current_user.id}") # English Log
            return jsonify(favorites)
        else:
            current_app.logger.info(f"[State Route] No favorite presets found for user {current_user.id}") # English Log
            return jsonify([])
    except Exception as e:
        current_app.logger.error(f"[State Route] Error fetching favorite presets for user {current_user.id}: {e}") # English Log
        return jsonify({"error": "Failed to retrieve favorite presets."}), 500 # English Hardcode
@user_state_bp.route(f"/{FAVORITE_PRESETS_KEY}", methods=["PUT"])
@crypto_auth_required
def set_favorite_presets(current_user):
    """
    Menyimpan (mengganti) seluruh daftar ID preset favorit untuk pengguna saat ini.
    Menerima JSON array dalam body request.
    """
    data = request.get_json()
    if not isinstance(data, list):
        return jsonify({"error": "Request body must be a JSON array of preset IDs."}), 400 # English Hardcode
    try:
        state_entry = State.query.filter_by(user_id=current_user.id, key=FAVORITE_PRESETS_KEY).first()
        if not state_entry:
            state_entry = State(user_id=current_user.id, key=FAVORITE_PRESETS_KEY)
            db.session.add(state_entry)
        state_entry.value = data
        db.session.commit()
        current_app.logger.info(f"[State Route] Updated favorite presets for user {current_user.id}. Count: {len(data)}") # English Log
        return jsonify({"status": "success", "message": "Favorite presets updated."}) # English Hardcode
    except Exception as e:
        db.session.rollback() # Rollback jika terjadi error
        current_app.logger.error(f"[State Route] Error saving favorite presets for user {current_user.id}: {e}") # English Log
        return jsonify({"error": "Failed to save favorite presets."}), 500 # English Hardcode
@user_state_bp.route(f"/{FAVORITE_COMPONENTS_KEY}", methods=["GET"])
@crypto_auth_required
def get_favorite_components(current_user):
    """
    Fetches the list of favorite component IDs for the current user.
    """
    try:
        state_entry = State.query.filter_by(user_id=current_user.id, key=FAVORITE_COMPONENTS_KEY).first()
        if state_entry and state_entry.value:
            favorites = state_entry.value if isinstance(state_entry.value, list) else []
            current_app.logger.info(f"[State Route] Retrieved {len(favorites)} favorite components for user {current_user.id}") # English Log
            return jsonify(favorites)
        else:
            current_app.logger.info(f"[State Route] No favorite components found for user {current_user.id}") # English Log
            return jsonify([])
    except Exception as e:
        current_app.logger.error(f"[State Route] Error fetching favorite components for user {current_user.id}: {e}") # English Log
        return jsonify({"error": "Failed to retrieve favorite components."}), 500 # English Hardcode
@user_state_bp.route(f"/{FAVORITE_COMPONENTS_KEY}", methods=["PUT"])
@crypto_auth_required
def set_favorite_components(current_user):
    """
    Saves (replaces) the entire list of favorite component IDs for the current user.
    Accepts a JSON array in the request body.
    """
    data = request.get_json()
    if not isinstance(data, list):
        return jsonify({"error": "Request body must be a JSON array of component IDs."}), 400 # English Hardcode
    try:
        state_entry = State.query.filter_by(user_id=current_user.id, key=FAVORITE_COMPONENTS_KEY).first()
        if not state_entry:
            state_entry = State(user_id=current_user.id, key=FAVORITE_COMPONENTS_KEY)
            db.session.add(state_entry)
        state_entry.value = data # Simpan list ID
        db.session.commit()
        current_app.logger.info(f"[State Route] Updated favorite components for user {current_user.id}. Count: {len(data)}") # English Log
        return jsonify({"status": "success", "message": "Favorite components updated."}) # English Hardcode
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"[State Route] Error saving favorite components for user {current_user.id}: {e}") # English Log
        return jsonify({"error": "Failed to save favorite components."}), 500 # English Hardcode
