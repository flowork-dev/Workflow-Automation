#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-gateway\app\routes\user.py JUMLAH BARIS 281 
#######################################################################

from flask import Blueprint, jsonify, request, current_app
from werkzeug.security import generate_password_hash
import secrets
import time
import datetime
import uuid
import requests
import os
import json # [ADD] Kita butuh ini untuk SSE
from functools import wraps
from ..models import User, RegisteredEngine, Subscription, EngineShare
from ..extensions import db, sse_message_queue
from ..helpers import token_required, crypto_auth_required, get_request_data, calculate_effective_permissions
from ..globals import pending_auths, engine_vitals_cache, engine_url_map, engine_last_seen_cache, engine_last_seen_lock
from eth_account.messages import encode_defunct
from web3.auto import w3
try:
    from cryptography.hazmat.primitives import hashes as crypto_hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
user_bp = Blueprint("user", __name__) # [MODIFIED] Hapus url_prefix, biarkan __init__.py yang atur
@user_bp.route("/license", methods=["GET"])
@crypto_auth_required
def get_user_license(current_user):
    """
    Men-generate dan menandatangani sertifikat lisensi untuk pengguna yang terotentikasi.
    """
    if not CRYPTO_AVAILABLE:
        return jsonify({"error": "Cryptography library is unavailable on the server."}), 500 # English Hardcode
    private_key_pem = os.getenv("FLOWORK_MASTER_PRIVATE_KEY")
    if not private_key_pem:
        current_app.logger.critical("FLOWORK_MASTER_PRIVATE_KEY is not set in .env!") # English Hardcode
        return jsonify({"error": "Server is not configured for license signing."}), 500 # English Hardcode
    try:
        private_key = serialization.load_pem_private_key(private_key_pem.encode(), password=None)
        user_tier, _ = calculate_effective_permissions(current_user)
        expires_at = current_user.subscription.expires_at if current_user.subscription else None
        if not expires_at:
            expires_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=365*100) # 100 years
        license_data = {
            "license_id": f"flw-lic-{uuid.uuid4()}",
            "user_id": current_user.public_address,
            "tier": user_tier,
            "issued_at": datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z",
            "valid_until": expires_at.isoformat().replace('+00:00', 'Z'),
        }
        message_to_sign = json.dumps({"data": license_data}, sort_keys=True, separators=(',', ':')).encode('utf-8')
        signature = private_key.sign(
            message_to_sign,
            padding.PSS(
                mgf=padding.MGF1(crypto_hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            crypto_hashes.SHA256()
        )
        final_certificate = {
            "data": license_data,
            "signature": signature.hex()
        }
        return jsonify(final_certificate)
    except Exception as e:
        current_app.logger.error(f"Failed to generate license certificate: {e}") # English Hardcode
        return jsonify({"error": "Failed to generate license.", "details": str(e)}), 500 # English Hardcode
@user_bp.route("/engines/select-for-auth", methods=["POST"])
@token_required
def select_engine_for_auth(current_user):
    data = get_request_data()
    req_id = data.get("request_id")
    engine_id = data.get("engine_id")
    if not req_id or not engine_id:
        return jsonify({"error": "request_id and engine_id are required."}), 400 # English Hardcode
    engine = RegisteredEngine.query.filter_by(
        id=engine_id, user_id=current_user.id
    ).first()
    if not engine:
        return jsonify({"error": "Engine not found or permission denied."}), 404 # English Hardcode
    new_plaintext_token = f"dev_engine_{secrets.token_hex(16)}"
    engine.engine_token_hash = generate_password_hash(
        new_plaintext_token, method="pbkdf2:sha256"
    )
    db.session.commit()
    pending_auths[req_id] = {"token": new_plaintext_token, "timestamp": time.time()}
    current_app.logger.info(f"User {current_user.email} authorized engine {engine.name} via dashboard. Token ready for claim by Core req_id: {req_id}") # English Hardcode
    return (
        jsonify(
            {
                "status": "success",
                "message": "Engine selected and authorized. Core can now claim the new token.", # English Hardcode
            }
        ),
        200,
    )
@user_bp.route('/engines', methods=['GET'])
@crypto_auth_required
def get_user_engines(current_user):
    """
    Mengembalikan daftar engine yang terdaftar milik user saat ini.
    """
    try:
        engines = RegisteredEngine.query.filter_by(user_id=current_user.id).order_by(RegisteredEngine.name).all()
        engine_list = []
        current_time = time.time()
        ONLINE_THRESHOLD_SECONDS = 120
        with engine_last_seen_lock:
            last_seen_snapshot = engine_last_seen_cache.copy()
        for e in engines:
            last_seen_timestamp = last_seen_snapshot.get(e.id, 0)
            status = 'offline' # English Hardcode
            if (current_time - last_seen_timestamp) < ONLINE_THRESHOLD_SECONDS:
                status = 'online' # English Hardcode
            engine_list.append({
                'id': e.id,
                'name': e.name,
                'status': status,
                'last_seen': datetime.datetime.fromtimestamp(last_seen_timestamp).isoformat() if last_seen_timestamp > 0 else None
            })
        return jsonify(engine_list)
    except Exception as e:
        current_app.logger.error(f"Error fetching engines for user {current_user.id}: {e}") # English Hardcode
        return jsonify({"error": "Failed to fetch engine list."}), 500 # English Hardcode
@user_bp.route('/engines', methods=['POST'])
@crypto_auth_required
def register_new_engine(current_user):
    """Mendaftarkan engine baru untuk user saat ini."""
    data = request.get_json()
    name = data.get('name')
    if not name:
        return jsonify({'error': 'Engine name is required'}), 400 # English Hardcode
    try:
        raw_token = f"dev_engine_{secrets.token_hex(16)}"
        token_hash = generate_password_hash(raw_token, method="pbkdf2:sha256")
        new_engine = RegisteredEngine(
            user_id=current_user.id,
            name=name,
            engine_token_hash=token_hash,
            status='offline' # English Hardcode
        )
        db.session.add(new_engine)
        db.session.commit()
        current_app.logger.info(f"User {current_user.public_address} registered new engine: '{name}' (ID: {new_engine.id})") # English Hardcode
        return jsonify({
            'id': new_engine.id,
            'name': new_engine.name,
            'status': new_engine.status,
            'raw_token': raw_token
        }), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error registering engine for user {current_user.id}: {e}") # English Hardcode
        return jsonify({"error": "Failed to register new engine."}), 500 # English Hardcode
@user_bp.route('/engines/<string:engine_id>', methods=['DELETE'])
@crypto_auth_required
def delete_user_engine(current_user, engine_id):
    """Menghapus engine milik user saat ini berdasarkan ID engine."""
    try:
        engine = RegisteredEngine.query.filter_by(id=engine_id, user_id=current_user.id).first()
        if not engine:
            return jsonify({'error': 'Engine not found or not owned by user'}), 404 # English Hardcode
        with engine_last_seen_lock:
            engine_last_seen_cache.pop(engine_id, None)
        engine_vitals_cache.pop(engine_id, None)
        engine_url_map.pop(engine_id, None)
        db.session.delete(engine)
        db.session.commit()
        current_app.logger.info(f"User {current_user.public_address} deleted engine: '{engine.name}' (ID: {engine_id})") # English Hardcode
        try:
            message_data = {
                "event": "engine_deleted", # English Hardcode
                "data": {"engine_id": engine_id},
                "user_id": current_user.id # PENTING untuk filtering SSE
            }
            sse_message_queue.put(json.dumps(message_data))
        except Exception as e:
            current_app.logger.error(f"Failed to publish SSE for engine_deleted: {e}") # English Hardcode
        return jsonify({'message': 'Engine deleted successfully'}) # English Hardcode
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting engine {engine_id} for user {current_user.id}: {e}") # English Hardcode
        return jsonify({"error": "Failed to delete engine."}), 500 # English Hardcode
@user_bp.route("/engines/<engine_id>/reset-token", methods=["POST"])
@crypto_auth_required
def reset_engine_token_legacy(current_user, engine_id):
    """
    Menghasilkan token baru untuk engine yang sudah ada.
    """
    engine = RegisteredEngine.query.filter_by(
        id=engine_id, user_id=current_user.id
    ).first()
    if not engine:
        return jsonify({"error": "Engine not found or permission denied."}), 404 # English Hardcode
    new_plaintext_token = f"dev_engine_{secrets.token_hex(16)}"
    token_hash = generate_password_hash(new_plaintext_token, method="pbkdf2:sha256")
    engine.engine_token_hash = token_hash
    db.session.commit()
    current_app.logger.info(f"User {current_user.public_address} reset token for engine: '{engine.name}' (ID: {engine_id})") # English Hardcode
    return (
        jsonify(
            {
                "message": f"Token for engine '{engine.name}' has been reset.", # English Hardcode
                "token": new_plaintext_token,
                "engine_id": engine.id,
            }
        ),
        200,
    )
@user_bp.route("/engines/<string:engine_id>/update-name", methods=["PUT"])
@crypto_auth_required
def update_engine_name_legacy(current_user, engine_id):
    """Updates the name of an existing engine."""
    engine = RegisteredEngine.query.filter_by(id=engine_id, user_id=current_user.id).first()
    if not engine:
        return jsonify({"error": "Engine not found or permission denied."}), 404 # English Hardcode
    data = request.get_json()
    new_name = data.get("name")
    if not new_name:
        return jsonify({"error": "New name is required."}), 400 # English Hardcode
    old_name = engine.name
    engine.name = new_name
    db.session.commit()
    current_app.logger.info(f"User {current_user.public_address} renamed engine '{old_name}' to '{new_name}' (ID: {engine_id})") # English Hardcode
    status = 'offline' # English Hardcode
    with engine_last_seen_lock:
        if (time.time() - engine_last_seen_cache.get(engine_id, 0)) < 120 :
            status = 'online' # English Hardcode
    try:
        message_data = {
            "event": "engine_status_update", # English Hardcode
            "data": {"engine_id": engine_id, "name": new_name, "status": status},
            "user_id": current_user.id
        }
        sse_message_queue.put(json.dumps(message_data))
    except Exception as e:
        current_app.logger.error(f"Failed to publish SSE for engine_status_update: {e}") # English Hardcode
    return jsonify({"message": f"Engine '{new_name}' updated successfully."}), 200 # English Hardcode
@user_bp.route('/shared-engines', methods=['GET'])
@crypto_auth_required
def get_shared_engines(current_user):
    """Mengembalikan daftar engine yang di-share PADA user ini."""
    try:
        shares = EngineShare.query.filter_by(shared_with_user_id=current_user.id)\
            .join(RegisteredEngine, EngineShare.engine_id == RegisteredEngine.id)\
            .join(User, RegisteredEngine.user_id == User.id)\
            .options(db.contains_eager(EngineShare.engine).contains_eager(RegisteredEngine.user))\
            .order_by(RegisteredEngine.name)\
            .all()
        shared_engine_list = []
        current_time = time.time()
        ONLINE_THRESHOLD_SECONDS = 120
        with engine_last_seen_lock:
            last_seen_snapshot = engine_last_seen_cache.copy()
        for share in shares:
            engine = share.engine
            owner = engine.user
            last_seen_timestamp = last_seen_snapshot.get(engine.id, 0)
            status = 'offline' # English Hardcode
            if (current_time - last_seen_timestamp) < ONLINE_THRESHOLD_SECONDS:
                status = 'online' # English Hardcode
            shared_engine_list.append({
                'id': engine.id,
                'name': engine.name,
                'status': status,
                'owner': {
                    'user_id': owner.id,
                    'username': owner.username,
                    'email': owner.email
                },
                'shared_at': share.shared_at.isoformat() if share.shared_at else None
            })
        return jsonify(shared_engine_list)
    except Exception as e:
        current_app.logger.error(f"Error fetching shared engines for user {current_user.id}: {e}") # English Log
        return jsonify({"error": "Failed to fetch shared engine list."}), 500 # English Hardcode
