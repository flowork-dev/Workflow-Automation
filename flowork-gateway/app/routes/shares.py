#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-gateway\app\routes\shares.py JUMLAH BARIS 125 
#######################################################################

from flask import Blueprint, jsonify, request, current_app
from ..extensions import db, socketio # <-- PENAMBAHAN KODE: import socketio
from ..models import User, RegisteredEngine, EngineShare
from ..helpers import crypto_auth_required # Menggunakan auth kripto untuk operasi user
from ..globals import engine_session_map # <-- PENAMBAHAN KODE: import engine_session_map
shares_bp = Blueprint("shares", __name__, url_prefix="/api/v1/engines")
def _notify_engine_to_refresh_auth(engine_id):
    """Kirim event ke Core Engine untuk refresh daftar otorisasi."""
    engine_sid = None
    for sid, info in engine_session_map.items():
        if info.get("engine_id") == engine_id:
            engine_sid = sid
            break
    if engine_sid:
        current_app.logger.info(f"[Gateway Share] Notifying engine {engine_id} (sid: {engine_sid}) to refresh its auth list.") # English Log
        socketio.emit('force_refresh_auth_list', {}, namespace='/engine-socket', to=engine_sid) # English Hardcode
    else:
        current_app.logger.warning(f"[Gateway Share] Could not find active socket session for engine {engine_id} to send auth refresh notification.") # English Log
@shares_bp.route("/<string:engine_id>/shares", methods=["POST"])
@crypto_auth_required
def grant_share(current_user, engine_id):
    """
    Memberikan akses share engine ke user lain (berdasarkan username ATAU public address).
    Hanya pemilik engine yang bisa melakukan ini.
    """
    engine = RegisteredEngine.query.filter_by(id=engine_id, user_id=current_user.id).first()
    if not engine:
        return jsonify({"error": "Engine not found or you are not the owner."}), 404 # English Hardcode
    data = request.get_json()
    share_identifier = data.get("share_with_identifier")
    if not share_identifier:
        return jsonify({"error": "Missing 'share_with_identifier' field (username or public_address)."}), 400 # English Hardcode
    identifier_lower = share_identifier.lower()
    user_to_share_with = User.query.filter(
        (db.func.lower(User.username) == identifier_lower) | (db.func.lower(User.public_address) == identifier_lower)
    ).first()
    if not user_to_share_with:
        return jsonify({"error": "User not found with that username or public address."}), 404 # English Hardcode
    if user_to_share_with.id == current_user.id:
        return jsonify({"error": "Cannot share engine with yourself."}), 400 # English Hardcode
    existing_share = EngineShare.query.filter_by(
        engine_id=engine_id, shared_with_user_id=user_to_share_with.id
    ).first()
    if existing_share:
        return jsonify({"error": "Engine is already shared with this user."}), 409 # English Hardcode
    try:
        new_share = EngineShare(
            engine_id=engine_id,
            shared_with_user_id=user_to_share_with.id
        )
        db.session.add(new_share)
        db.session.commit()
        current_app.logger.info(f"User {current_user.id} shared engine {engine_id} with user {user_to_share_with.id} (identifier: {identifier_lower})") # English Log
        _notify_engine_to_refresh_auth(engine_id)
        return jsonify({
            "message": "Engine shared successfully.", # English Hardcode
            "share_id": new_share.id,
            "shared_with": {
                "user_id": user_to_share_with.id,
                "email": user_to_share_with.email,
                "public_address": user_to_share_with.public_address,
                "username": user_to_share_with.username,
                "shared_at": new_share.shared_at.isoformat() if new_share.shared_at else None
            }
        }), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to grant share for engine {engine_id}: {e}") # English Log
        return jsonify({"error": "Failed to grant share."}), 500 # English Hardcode
@shares_bp.route("/<string:engine_id>/shares/<string:shared_user_id>", methods=["DELETE"])
@crypto_auth_required
def revoke_share(current_user, engine_id, shared_user_id):
    """
    Mencabut akses share engine dari user tertentu.
    Hanya pemilik engine yang bisa melakukan ini.
    """
    engine = RegisteredEngine.query.filter_by(id=engine_id, user_id=current_user.id).first()
    if not engine:
        return jsonify({"error": "Engine not found or you are not the owner."}), 404 # English Hardcode
    share_to_delete = EngineShare.query.filter_by(
        engine_id=engine_id, shared_with_user_id=shared_user_id
    ).first()
    if not share_to_delete:
        return jsonify({"error": "Share record not found."}), 404 # English Hardcode
    try:
        db.session.delete(share_to_delete)
        db.session.commit()
        current_app.logger.info(f"User {current_user.id} revoked share for engine {engine_id} from user {shared_user_id}") # English Log
        _notify_engine_to_refresh_auth(engine_id)
        return jsonify({"message": "Share revoked successfully."}), 200 # English Hardcode
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to revoke share for engine {engine_id}: {e}") # English Log
        return jsonify({"error": "Failed to revoke share."}), 500 # English Hardcode
@shares_bp.route("/<string:engine_id>/shares", methods=["GET"])
@crypto_auth_required
def get_engine_shares(current_user, engine_id):
    """
    Mengambil daftar user yang memiliki akses share ke engine ini.
    Hanya pemilik engine yang bisa melihat ini.
    """
    engine = RegisteredEngine.query.filter_by(id=engine_id, user_id=current_user.id).first()
    if not engine:
        return jsonify({"error": "Engine not found or you are not the owner."}), 404 # English Hardcode
    shares = db.session.query(EngineShare, User).join(
        User, EngineShare.shared_with_user_id == User.id
    ).filter(EngineShare.engine_id == engine_id).all()
    shared_users_list = [
        {
            "user_id": share_record.shared_with_user_id,
            "email": user_record.email,
            "public_address": user_record.public_address,
            "username": user_record.username,
            "shared_at": share_record.shared_at.isoformat() if share_record.shared_at else None
        }
        for share_record, user_record in shares
    ]
    return jsonify(shared_users_list)
