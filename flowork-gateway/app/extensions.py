import queue
from threading import Lock # [ADD] Import Lock
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_cors import CORS
from cachetools import TTLCache
# (ADD) Import SocketIO
from flask_socketio import SocketIO

db = SQLAlchemy()
jwt = JWTManager()
migrate = Migrate()
cors = CORS()
socketio = SocketIO() # (ADD) Initialize SocketIO

sse_message_queue = queue.Queue()
permission_cache = TTLCache(maxsize=10000, ttl=300)
cache_lock = Lock()