#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-gateway\app\routes\momod.py JUMLAH BARIS 66 
#######################################################################

import jwt
import datetime
from flask import Blueprint, request, jsonify, current_app
from werkzeug.security import check_password_hash
from sqlalchemy.orm import joinedload
from app.models import AdminUser, Role, Permission
from app.extensions import db
from app.helpers import get_request_data
momod_bp = Blueprint("momod", __name__, url_prefix="/api/v1/momod")
@momod_bp.route("/auth/login", methods=["POST"])
def admin_login():
    """
    Menangani permintaan login dari antarmuka moderator (momod).
    """
    data = get_request_data()
    if not data or not data.get("username") or not data.get("password"):
        return jsonify({"error": "Username and password are required."}), 400
    admin_user = (
        AdminUser.query.options(
            joinedload(AdminUser.roles).joinedload(Role.permissions)
        )
        .filter_by(username=data["username"])
        .first()
    )
    if not admin_user or not check_password_hash(
        admin_user.password_hash, data["password"]
    ):
        current_app.logger.warning(
            f"Admin login failed for user '{data.get('username')}': Invalid credentials."
        )
        return jsonify({"error": "Invalid credentials"}), 401
    current_app.logger.info(f"Admin login successful for user '{admin_user.username}'.")
    permissions = set()
    for role in admin_user.roles:
        for perm in role.permissions:
            permissions.add(perm.name)
    secret_key = current_app.config["SECRET_KEY"]
    token = jwt.encode(
        {
            "admin_id": str(admin_user.id),
            "is_admin": True,
            "permissions": list(permissions),
            "exp": datetime.datetime.now(datetime.timezone.utc)
            + datetime.timedelta(hours=8),
        },
        secret_key,
        algorithm="HS256",
    )
    return jsonify(
        {
            "message": "Admin login successful",
            "token": token,
            "user": {
                "username": admin_user.username,
                "roles": [role.name for role in admin_user.roles],
                "permissions": list(permissions),
            },
        }
    )
