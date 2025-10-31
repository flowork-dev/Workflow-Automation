#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-gateway\app\routes\engine.py JUMLAH BARIS 109 
#######################################################################

from flask import Blueprint, jsonify, request, current_app
from functools import wraps
import time
import os
import hmac
from ..models import RegisteredEngine, User, EngineShare
from werkzeug.security import check_password_hash
from ..globals import (
    pending_auths,
    engine_vitals_cache,
)
from ..extensions import db # Impor db
engine_bp = Blueprint("engine", __name__, url_prefix="/api/v1/engine")
def engine_internal_token_required(f):
    """Decorator untuk memeriksa X-Engine-Token"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        engine_token = request.headers.get("X-Engine-Token")
        if not engine_token:
            current_app.logger.warning(f"[AUTHZ] Engine call failed: Missing X-Engine-Token.") # English Hardcode
            return jsonify({"error": "Engine token is required."}), 401 # English Hardcode
        engine_found = None
        all_engines = RegisteredEngine.query.all()
        for engine in all_engines:
            if check_password_hash(engine.engine_token_hash, engine_token):
                engine_found = engine
                break
        if not engine_found:
            current_app.logger.warning(f"[AUTHZ] Engine call failed: Invalid engine token provided.") # English Hardcode
            return jsonify({"error": "Invalid engine token."}), 401 # English Hardcode
        request.engine_db_instance = engine_found
        return f(*args, **kwargs)
    return decorated_function
@engine_bp.route("/get-engine-auth-info", methods=["GET"])
@engine_internal_token_required
def get_engine_auth_info():
    """
    Endpoint ini HANYA untuk dipanggil oleh Core Engine saat startup.
    Engine mengirimkan token uniknya untuk otentikasi (via decorator).
    Gateway merespons dengan DAFTAR alamat publik (User ID) yang
    diizinkan mengakses engine ini (pemilik DAN yang di-share).
    """
    engine_found = getattr(request, 'engine_db_instance', None)
    if not engine_found:
        current_app.logger.error("[AUTHZ] CRITICAL: Engine instance not found in request context after decorator!") # English Hardcode
        return jsonify({"error": "Internal server error during authorization."}), 500 # English Hardcode
    try:
        authorized_addresses = set()
        owner = User.query.filter_by(id=engine_found.user_id).first()
        if not owner or not owner.public_address:
            current_app.logger.error(f"[AUTHZ] Engine {engine_found.name} is valid but owner (User ID: {engine_found.user_id}) or public_address is missing!") # English Hardcode
            return jsonify({"error": "Engine owner account is not properly configured."}), 500 # English Hardcode
        authorized_addresses.add(owner.public_address.lower()) # Tambahkan pemilik
        shares = EngineShare.query.filter_by(engine_id=engine_found.id).all()
        for share in shares:
            shared_user = User.query.get(share.shared_with_user_id)
            if shared_user and shared_user.public_address:
                authorized_addresses.add(shared_user.public_address.lower())
            else:
                current_app.logger.warning(f"[AUTHZ] Share record found for user ID {share.shared_with_user_id} but user or public_address is missing.") # English Log
        unique_authorized_addresses = list(authorized_addresses)
        current_app.logger.info(f"[AUTHZ] Successfully provided authorization list for engine '{engine_found.name}'. Count: {len(unique_authorized_addresses)}") # English Hardcode
        current_app.logger.debug(f"[AUTHZ] Sample Authorized for '{engine_found.name}': {unique_authorized_addresses[:3]}") # English Hardcode
        return jsonify({"authorized_addresses": unique_authorized_addresses})
    except Exception as e:
        current_app.logger.error(f"[AUTHZ] CRITICAL Error in /get-engine-auth-info for engine {engine_found.id}: {e}") # English Hardcode
        import traceback
        current_app.logger.error(traceback.format_exc())
        return jsonify({"error": "Internal server error during authorization."}), 500 # English Hardcode
@engine_bp.route("/internal/vitals", methods=["GET"])
@engine_internal_token_required # Gunakan decorator yang sama
def get_all_vitals():
    """
    Provides a snapshot of the last known vitals for all connected engines.
    Internal endpoint for Momod API.
    """
    return jsonify(engine_vitals_cache)
@engine_bp.route("/claim-token", methods=["GET"])
@engine_internal_token_required # Gunakan decorator yang sama (atau @engine_token_required jika beda level akses)
def claim_token():
    """
    Endpoint ini dipanggil oleh Core Engine (Dashboard Server) untuk mengklaim
    token otentikasi baru setelah user menyelesaikan otorisasi di web UI.
    """
    req_id = request.args.get("req_id")
    if not req_id:
        return jsonify({"error": "Request ID is required."}), 400 # English Hardcode
    current_time = time.time()
    for key in list(pending_auths.keys()):
        if current_time - pending_auths[key]["timestamp"] > 300: # 5 menit expiry
            del pending_auths[key]
    auth_data = pending_auths.pop(req_id, None)
    if auth_data and auth_data.get("token"):
        current_app.logger.info(
            f"[AUTH] Token successfully claimed by Core Engine for request ID: {req_id}" # English Hardcode
        )
        return jsonify({"status": "success", "token": auth_data["token"]}) # English Hardcode
    else:
        current_app.logger.warning(
            f"[AUTH] Failed to claim token: Request ID '{req_id}' not found or expired for Core Engine." # English Hardcode
        )
        return jsonify({"error": "Token not found or expired."}), 404 # English Hardcode
