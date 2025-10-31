#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-gateway\app\cache.py JUMLAH BARIS 23 
#######################################################################

from flask_caching import Cache # Assuming standard Flask cache dependency
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
