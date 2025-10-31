#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-gateway\app\routes\auth.py JUMLAH BARIS 94 
#######################################################################

import jwt
import datetime
import threading
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import create_access_token
from werkzeug.security import generate_password_hash, check_password_hash
from ..models import User, Subscription
from ..extensions import db
from ..helpers import (
    get_request_data,
    token_required,
    crypto_auth_required,
    calculate_effective_permissions,
    _inject_user_data_to_core,
)
auth_bp = Blueprint("auth", __name__, url_prefix="/api/v1/auth")
@auth_bp.route("/register", methods=["POST"])
def register():
    """
    (REMASTERED) Stubbed endpoint. Registration is handled locally/cryptographically by the client.
    """
    return jsonify({"error": "Not Implemented: Registration is handled by the client identity generation."}), 501 # English Hardcode
@auth_bp.route("/login", methods=["POST"])
def login():
    """
    (REMASTERED) Stubbed endpoint. Login is handled via cryptographic challenge (see /api/v1/auth/profile).
    """
    return jsonify({"error": "Not Implemented: Login is handled via cryptographic challenge."}), 501 # English Hardcode
@auth_bp.route("/logout", methods=["POST"])
@crypto_auth_required # Sebaiknya di-autentikasi juga
def handle_logout(current_user): # Menerima current_user
    """
    Handles a logout request. In a stateless crypto-auth system,
    this mainly serves to acknowledge the client's session termination.
    """
    current_app.logger.info(f"[Gateway Auth] Received logout request from user {current_user.public_address[:10]}...") # English log
    return jsonify(
        {"message": "Logout acknowledged by Gateway."} # English Hardcode
    )
@auth_bp.route("/profile", methods=["GET"])
@crypto_auth_required # Ini adalah endpoint "login"
def get_profile(current_user): # Menerima current_user dari decorator crypto
    """
    (REMASTERED) Mengembalikan profil user berdasarkan verifikasi tanda tangan kripto.
    Ini adalah endpoint "login" yang sebenarnya.
    (MODIFIKASI OPSI A) Sekarang juga membuat dan mengembalikan JWT Token.
    """
    if not current_user:
        current_app.logger.warning("[Gateway Auth Profile] Access denied: User object not found after crypto auth.") # English log
        return jsonify({"error": "Authentication failed or user not found."}), 401 # English Hardcode
    try:
        db.session.refresh(current_user)
        if current_user.subscription:
            db.session.refresh(current_user.subscription)
    except Exception as e:
        current_app.logger.error(f"[Gateway Auth Profile] Failed to refresh user/subscription data: {e}") # English log
        db.session.rollback()
    user_tier = current_user.subscription.tier if current_user.subscription else "free" # English Hardcode
    effective_permissions = [] # Placeholder, karena logic calculate_effective_permissions tidak ada di file
    expires_at = (
        current_user.subscription.expires_at.isoformat().replace('+00:00', 'Z')
        if current_user.subscription and current_user.subscription.expires_at
        else None
    )
    effective_username = current_user.username
    if effective_username.startswith("user_") and effective_username.endswith("..."):
        effective_username = current_user.public_address
    elif '@' in effective_username: # Jika username lama adalah email
        effective_username = current_user.public_address
    jwt_identity = current_user.id
    access_token = create_access_token(identity=jwt_identity, expires_delta=datetime.timedelta(days=1))
    user_data_response = {
        "user_id": current_user.public_address, # ID utama adalah public address
        "email": current_user.email,
        "username": effective_username, # (PERBAIKAN) Gunakan username yang sudah divalidasi
        "public_address": current_user.public_address,
        "tier": user_tier,
        "permissions": effective_permissions,
        "license_expires_at": expires_at,
        "token": access_token # (PENAMBAHAN KODE) Kirim JWT ke GUI
    }
    def inject_with_context(app, data):
        with app.app_context():
            _inject_user_data_to_core(data)
    app_context = current_app._get_current_object()
    current_app.logger.info(f"[Gateway Auth Profile] Profile data sent for user {current_user.public_address[:10]}...") # English log
    return jsonify(user_data_response)
