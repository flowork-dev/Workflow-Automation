#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-gateway\app\helpers\auth_utils.py JUMLAH BARIS 115 
#######################################################################

from flask import jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from functools import wraps
import logging
from web3.auto import w3
from eth_account.messages import encode_defunct
from werkzeug.security import check_password_hash # Used for checking hashed engine token
try:
    from ..models import User, AdminUser, RegisteredEngine
except ImportError:
    class DummyUser: pass
    class DummyAdminUser: pass
    class DummyRegisteredEngine: pass
    User = DummyUser
    AdminUser = DummyAdminUser
    RegisteredEngine = DummyRegisteredEngine
logger = logging.getLogger(__name__)
def token_required(admin_required=False):
    """
    Decorator factory that checks for a valid JWT token and loads the User/Admin context.
    If admin_required=True, it verifies if the user is an AdminUser.
    """
    def _token_factory_decorator(fn):
        @wraps(fn)
        @jwt_required()
        def wrapped_view_with_auth(*args, **kwargs):
            current_user_id = get_jwt_identity()
            admin_user = AdminUser.query.filter_by(id=current_user_id).first()
            if admin_user:
                kwargs['current_user'] = admin_user
                kwargs['is_admin'] = True
                return fn(*args, **kwargs)
            regular_user = User.query.filter_by(id=current_user_id).first()
            if regular_user:
                if admin_required:
                    return jsonify({"msg": "Admin access required"}), 403
                kwargs['current_user'] = regular_user
                kwargs['is_admin'] = False
                return fn(*args, **kwargs)
            if not admin_user and not regular_user:
                logger.warning(f"User with ID {current_user_id} in token not found. Token is valid but user record missing.")
                return jsonify({"msg": "Invalid token identity"}), 401
            return fn(*args, **kwargs)
        wrapped_view_with_auth.__name__ = fn.__name__
        wrapped_view_with_auth.__qualname__ = fn.__qualname__
        return wrapped_view_with_auth
    return _token_factory_decorator
def crypto_auth_required(fn):
    """
    Decorator that verifies the message signature (signed with private key)
    against the Public Address provided in the request headers.
    Loads the User object associated with the Public Address.
    """
    @wraps(fn)
    def decorator(*args, **kwargs):
        public_address = request.headers.get('X-Flowork-Public-Address')
        signature = request.headers.get('X-Flowork-Signature')
        message = request.headers.get('X-Flowork-Message') # The message that was signed
        if not all([public_address, signature, message]):
            return jsonify({"msg": "Missing crypto auth headers"}), 401
        try:
            encoded_message = encode_defunct(text=message)
            recovered_address = w3.eth.account.recover_message(
                encoded_message,
                signature=signature
            )
        except Exception as e:
            logger.error(f"Crypto verification failed: {e}")
            return jsonify({"msg": "Signature verification failed"}), 401
        if recovered_address.lower() != public_address.lower():
            return jsonify({"msg": "Signature does not match Public Address"}), 401
        user = User.query.filter_by(public_address=public_address).first()
        admin_user = AdminUser.query.filter_by(username='awenk').first()
        if user:
            kwargs['current_user'] = user
            kwargs['is_admin'] = False
        elif admin_user and public_address.lower() == admin_user.public_address.lower():
            kwargs['current_user'] = admin_user
            kwargs['is_admin'] = True
        else:
            return jsonify({"msg": "User not registered for this Public Address"}), 404
        return fn(*args, **kwargs)
    return decorator
def engine_token_required(fn):
    """
    Decorator that checks for a valid engine token hash provided in the request headers.
    Loads the RegisteredEngine object. (System route required)
    """
    @wraps(fn)
    def decorator(*args, **kwargs):
        engine_token = request.headers.get('X-Flowork-Engine-Token')
        engine_id = request.headers.get('X-Flowork-Engine-ID') # Assuming ID is also provided
        if not all([engine_token, engine_id]):
            return jsonify({"msg": "Missing engine authentication headers"}), 401
        found_engine = RegisteredEngine.query.filter_by(id=engine_id).first()
        if not found_engine:
            return jsonify({"msg": "Engine not registered"}), 404
        if not check_password_hash(found_engine.engine_token_hash, engine_token):
            return jsonify({"msg": "Invalid engine token"}), 401
        kwargs['current_engine'] = found_engine
        return fn(*args, **kwargs)
    return decorator
def admin_token_required(fn):
    """
    Decorator that ensures a valid user token and verifies they have AdminUser roles.
    This is an alias wrapper around the token_required factory function.
    """
    return token_required(admin_required=True)(fn)
