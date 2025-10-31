#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-gateway\app\helpers\cache.py JUMLAH BARIS 61 
#######################################################################

from app.extensions import permission_cache, cache_lock, db
from app.models import RegisteredEngine, EngineShare, User
from flask import current_app # Untuk mendapatkan app_context
from threading import Lock
class DummyCache:
    """A minimal in-memory cache placeholder."""
    def get(self, key):
        """Simulate fetching a value."""
        return None
    def set(self, key, value, timeout=0):
        """Simulate setting a value."""
        pass
    def delete(self, key):
        """Simulate deleting a key."""
        pass
    def init_app(self, app):
        """Mock init for Flask extension pattern."""
        pass
cache = DummyCache()
def check_permission_with_cache(user_id, engine_id):
    """
    (REPLACED CODE - Roadmap 2.2)
    Checks user permissions against a cache before execution.
    For now, it returns True to allow the app to fully load.
    (English Hardcode)
    """
    cache_key = f"{user_id}:{engine_id}"
    with cache_lock:
        cached_result = permission_cache.get(cache_key)
        if cached_result is not None:
            return cached_result # Langsung return jika ada di cache
    with current_app.app_context():
        engine = db.session.get(RegisteredEngine, engine_id) # (PERBAIKAN) Pakai .get untuk Primary Key
        if not engine:
            with cache_lock:
                permission_cache[cache_key] = False # Cache kegagalan
            return False # Engine tidak ada
        if engine.user_id == user_id:
            with cache_lock:
                permission_cache[cache_key] = True # Simpan ke cache
            return True
        share = EngineShare.query.filter_by(shared_with_user_id=user_id, engine_id=engine_id).first()
        if share:
            with cache_lock:
                permission_cache[cache_key] = True # Simpan ke cache
            return True
    with cache_lock:
        permission_cache[cache_key] = False # Cache juga kegagalan
    return False
def clear_permission_cache(user_id, engine_id):
    cache_key = f"{user_id}:{engine_id}"
    with cache_lock:
        if cache_key in permission_cache:
            del permission_cache[cache_key]
