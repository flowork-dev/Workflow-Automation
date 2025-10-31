#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-gateway\app\routes\streaming.py JUMLAH BARIS 38 
#######################################################################

import json
import queue
import time
import logging
from flask import Blueprint, Response, stream_with_context, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..extensions import sse_message_queue
logger = logging.getLogger(__name__)
stream_bp = Blueprint('streaming', __name__) # [MODIFIED] Sesuai __init__.py
@stream_bp.route('/events', methods=['GET']) # [MODIFIED] Path dari __init__.py
@jwt_required()
def stream_events():
    user_id = get_jwt_identity()
    logger.info(f"SSE stream requested by user: {user_id}. Stream starting...") # English Hardcode
    def generate_events():
        print(f"User {user_id} connected to SSE stream.") # English Hardcode
        while True:
            try:
                message_str = sse_message_queue.get(timeout=10)
                try:
                    message_data = json.loads(message_str)
                    if message_data.get('user_id') == user_id:
                        yield f"data: {message_str}\n\n"
                except json.JSONDecodeError:
                    print(f"SSE: Corrupted message in queue: {message_str}") # English Hardcode
            except queue.Empty:
                yield ": heartbeat\n\n" # English Hardcode
            except Exception as e:
                print(f"SSE stream error: {e}") # English Hardcode
                time.sleep(1)
    return Response(stream_with_context(generate_events()), mimetype='text/event-stream')
