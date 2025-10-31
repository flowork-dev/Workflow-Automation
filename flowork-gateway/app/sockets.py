#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-gateway\app\sockets.py JUMLAH BARIS 350 
#######################################################################

import time
import jwt # Keep jwt import for potential admin usage elsewhere? Maybe remove later if unused.
import datetime
from flask import request, current_app
from flask_socketio import emit, disconnect, join_room, leave_room
from werkzeug.security import check_password_hash
from .extensions import socketio, db
from .models import RegisteredEngine, User, Subscription
from web3.auto import w3
from eth_account.messages import encode_defunct
from .helpers import calculate_effective_permissions, _inject_user_data_to_core
from .globals import (
    active_engine_sessions,
    engine_session_map,
    gui_sessions,
    rate_limit_lock,
    connection_attempts,
    RATE_LIMIT_ATTEMPTS,
    RATE_LIMIT_WINDOW,
    engine_url_map,
    engine_vitals_cache,
    engine_last_seen_cache,
    engine_last_seen_lock,
)
def register_socket_handlers(app):
    @socketio.on("rpc_response_from_engine", namespace="/engine-socket")
    def handle_rpc_response_from_engine(data):
        """
        Menerima respons RPC dari Core Engine (yang dipicu oleh GUI)
        dan meneruskannya kembali ke room GUI user yang benar.
        """
        session_info = engine_session_map.get(request.sid)
        if not session_info:
            app.logger.warning(f"[Gateway RPC] Received RPC response from unauthed engine session: {request.sid}", "WARN") # English Hardcode
            return
        user_id = session_info.get("user_id") # ID internal User DB
        if not user_id:
            app.logger.warning(f"[Gateway RPC] No user_id found for engine session {request.sid}", "WARN") # English Hardcode
            return
        app.logger.debug(f"[Gateway RPC] Forwarding RPC response (type: {data.get('type', 'N/A')}) from Engine {session_info.get('engine_id')} to User Room {user_id}") # English Hardcode
        socketio.emit(
            "rpc_response_from_engine", # Ini adalah event 'catch-all' yang baru
            data,
            to=user_id,
            namespace="/gui-socket"
        )
    @socketio.on("connect", namespace="/gui-socket")
    def handle_gui_connect():
        signature = request.headers.get("X-Signature")
        public_address = request.headers.get("X-User-Address")
        message = request.headers.get("X-Signed-Message")
        app.logger.info(f"[Gateway GUI Connect] Attempt from {request.remote_addr}. Address: {public_address[:10] if public_address else 'N/A'}...") # English log
        if not all([signature, public_address, message]):
            app.logger.warning(
                f"[Gateway GUI] Connection attempt without signature headers from {request.remote_addr}. Denied." # English log
            )
            return False # Tolak koneksi
        try:
            encoded_message = encode_defunct(text=message)
            recovered_address = w3.eth.account.recover_message(
                encoded_message, signature=signature
            )
            if recovered_address.lower() != public_address.lower():
                app.logger.warning(f"[Gateway GUI Auth] Invalid signature. Expected {public_address}, got {recovered_address}. Denied.") # English log
                return False # Tanda tangan tidak cocok
            with app.app_context(): # Pastikan dalam konteks aplikasi
                current_user = User.query.filter(
                    User.public_address.ilike(public_address)
                ).first()
                if not current_user:
                    app.logger.info(f"[Gateway GUI Auth] New address '{public_address}' detected. Auto-registration needed (implement if required). Denied for now.") # English log
                    return False
                user_id = current_user.id # Gunakan ID internal user dari DB
                if user_id not in gui_sessions:
                    gui_sessions[user_id] = set()
                gui_sessions[user_id].add(request.sid)
                join_room(user_id) # Masukkan session ke room user_id
                app.logger.info(
                    f"[Gateway GUI] Client connected & authenticated for user {user_id} (Address: {public_address[:10]}...) with session ID: {request.sid}" # English log
                )
                engine_statuses = []
                user_engines = RegisteredEngine.query.filter_by(user_id=user_id).all()
                for eng in user_engines:
                    engine_statuses.append({
                        "engine_id": eng.id,
                        "name": eng.name,
                        "status": eng.status,
                        "last_seen": eng.last_seen.isoformat() if eng.last_seen else None,
                        "vitals": engine_vitals_cache.get(eng.id, None)
                    })
                emit("initial_engine_statuses", engine_statuses, to=request.sid)
                return True # Koneksi diterima
        except Exception as e:
            app.logger.error(f"[Gateway GUI Auth] Signature verification failed: {e}. Connection denied.") # English log
            return False # Tolak koneksi karena error verifikasi
    @socketio.on("disconnect", namespace="/gui-socket")
    def handle_gui_disconnect():
        session_id = request.sid
        user_id_disconnected = None # Untuk logging
        for user_id, sessions in list(gui_sessions.items()):
            if session_id in sessions:
                sessions.remove(session_id)
                leave_room(user_id)
                user_id_disconnected = user_id
                if not sessions:
                    del gui_sessions[user_id]
                break # Keluar loop setelah user ditemukan
        if user_id_disconnected:
             app.logger.info(
                f"[Gateway GUI] Client disconnected for user {user_id_disconnected} with session ID: {session_id}" # English log
             )
        else:
             app.logger.warning(
                 f"[Gateway GUI] Client disconnected but session ID {session_id} not found in user map." # English log
             )
    @socketio.on("rpc_forward_to_engine", namespace="/gui-socket")
    def handle_rpc_forward_to_engine(data):
        """
        Menerima pesan RPC 'catch-all' dari GUI (misalnya 'execute_workflow', 'request_presets_list')
        dan meneruskannya ke Core Engine yang aktif milik user tersebut.
        """
        user_id_from_session = None
        for uid, sids in gui_sessions.items():
            if request.sid in sids:
                user_id_from_session = uid
                break
        if not user_id_from_session:
             app.logger.warning(f"[Gateway RPC] Received 'rpc_forward_to_engine' from unknown/unauthed GUI session: {request.sid}") # English Hardcode
             emit("error", {"message": "Authentication required for RPC."}, to=request.sid) # English Hardcode
             return
        current_user = None
        with app.app_context():
            current_user = User.query.get(user_id_from_session)
        if not current_user or not current_user.public_address:
             app.logger.error(f"[Gateway RPC] Cannot forward RPC: User {user_id_from_session} not found or missing public_address.") # English Hardcode
             emit("error", {"message": "User account configuration error."}, to=request.sid) # English Hardcode
             return
        engine_id_from_header = data.get('engine_id') # Asumsi GUI menambahkannya ke payload
        target_engine_id = engine_id_from_header # or get_active_engine_for_user(user_id_from_session)
        if not target_engine_id:
            app.logger.warning(f"[Gateway RPC] User {user_id_from_session} requested RPC but no target or active engine found.") # English Hardcode
            emit(
                "rpc_response_from_engine", # Kirim balik sebagai respons
                {"type": "error", "message": "No active or specified engine found to run the workflow."}, # English Hardcode
                to=request.sid,
            )
            return
        engine_sid_to_send = next(
            (
                sid
                for sid, info in engine_session_map.items()
                if info.get("engine_id") == target_engine_id
            ),
            None,
        )
        if not engine_sid_to_send:
            app.logger.error(f"[Gateway RPC] Target/Active engine ID {target_engine_id} found but no corresponding socket session. Engine might be offline.") # English Hardcode
            emit(
                "rpc_response_from_engine", # Kirim balik sebagai respons
                {"type": "error", "message": f"Engine '{target_engine_id[:8]}...' is offline or unreachable."}, # English Hardcode
                to=request.sid,
            )
            return
        app.logger.info(f"[Gateway RPC] Forwarding RPC (type: {data.get('payload', {}).get('type', 'N/A')}) from GUI {request.sid} to Engine {engine_sid_to_send} (Engine ID: {target_engine_id})") # English Hardcode
        socketio.emit(
            "execute_rpc_from_gui", # Event baru yang didengarkan oleh Core Engine
            data,
            to=engine_sid_to_send,
            namespace="/engine-socket"
        )
    @socketio.on("connect", namespace="/engine-socket")
    def handle_engine_connect(auth=None): # Terima argumen auth opsional
        ip_address = request.remote_addr
        with rate_limit_lock:
            now = time.time()
            connection_attempts[ip_address] = [t for t in connection_attempts[ip_address] if now - t < RATE_LIMIT_WINDOW]
            if len(connection_attempts[ip_address]) >= RATE_LIMIT_ATTEMPTS:
                app.logger.warning(f"[Gateway RateLimit] Too many connection attempts from {ip_address}. Disconnecting.") # English log
                disconnect()
                return False # Tolak koneksi
            connection_attempts[ip_address].append(now)
        app.logger.info(f"[Gateway Engine] Client connected with sid: {request.sid} from IP: {ip_address}") # English log
    @socketio.on("auth", namespace="/engine-socket")
    def handle_engine_auth(data):
        if not data:
            app.logger.warning(f"[Gateway Engine] Auth attempt failed: No data provided by {request.sid}.") # English log
            emit("auth_failed", {"message": "Auth payload is required."}) # English log
            disconnect()
            return
        engine_token = data.get("token")
        engine_id = data.get("engine_id")
        if not engine_token or not engine_id:
            app.logger.warning(f"[Gateway Engine] Auth attempt failed: 'token' or 'engine_id' missing from payload by {request.sid}.") # English log
            emit("auth_failed", {"message": "Token and Engine ID are required."}) # English log
            disconnect()
            return
        app.logger.info(f"[Gateway Engine] Received auth attempt from {request.sid} for Engine ID: {engine_id}") # English log
        with app.app_context(): # Pastikan dalam konteks aplikasi Flask untuk akses DB
            engine_found = None
            try:
                engine_found = db.session.get(RegisteredEngine, engine_id) # Fast lookup by Primary Key
                if not engine_found or not check_password_hash(engine_found.engine_token_hash, engine_token):
                    engine_found = None # Reset jika hash tidak cocok atau ID tidak ditemukan
            except Exception as e:
                 app.logger.error(f"[Gateway Engine] Database error during engine authentication: {e}") # English log
                 emit("auth_failed", {"message": "Server error during authentication."}) # English log
                 disconnect()
                 return
            if engine_found:
                user_id = engine_found.user_id # ID Internal User (bukan public address)
                session_id = request.sid
                with engine_last_seen_lock:
                    engine_last_seen_cache[engine_id] = time.time()
                if user_id not in active_engine_sessions:
                    active_engine_sessions[user_id] = set()
                active_engine_sessions[user_id].add(session_id)
                engine_session_map[session_id] = {
                    "user_id": user_id,
                    "engine_id": engine_id,
                }
                try:
                    engine_found.status = "online" # English log
                    engine_found.last_seen = db.func.now() # Gunakan fungsi DB untuk waktu
                    db.session.add(engine_found)
                    db.session.commit()
                except Exception as e:
                    app.logger.error(f"[Gateway Engine] Failed to update engine status in DB for {engine_id}: {e}") # English log
                    db.session.rollback()
                app.logger.info(f"[Gateway Engine] Auth successful for engine '{engine_found.name}' (ID: {engine_id}), user: {user_id}, sid: {session_id}") # English log
                emit(
                    "auth_success",
                    {
                        "message": f"Successfully authenticated as engine '{engine_found.name}'." # English log
                    },
                )
                socketio.emit(
                    "engine_status_update",
                    {
                        "engine_id": engine_id,
                        "name": engine_found.name,
                        "status": "online", # English log
                        "last_seen": engine_found.last_seen.isoformat() if engine_found.last_seen else None,
                        "vitals": engine_vitals_cache.get(engine_id, None)
                    },
                    to=user_id, # Kirim ke room user (ID internal)
                    namespace="/gui-socket",
                )
            else:
                app.logger.warning(
                    f"[Gateway Engine] Authentication failed for Engine ID: {engine_id} (Token prefix: {engine_token[:8]}...) from {request.sid}. Invalid ID or Token." # English log
                )
                emit("auth_failed", {"message": "Invalid engine ID or token."}) # English log
                disconnect() # Putuskan koneksi jika token salah
    @socketio.on("register_engine_http_info", namespace="/engine-socket")
    def handle_register_engine_http_info(data):
        session_info = engine_session_map.get(request.sid)
        if session_info:
            engine_id = session_info.get("engine_id")
            http_url = data.get("http_url")
            if engine_id and http_url:
                engine_url_map[engine_id] = http_url
                app.logger.info(
                    f"[Gateway] Engine '{engine_id}' registered its HTTP address: {http_url}" # English log
                )
            else:
                app.logger.warning(f"[Gateway] Received invalid HTTP info from engine session {request.sid}: {data}") # English log
        else:
             app.logger.warning(f"[Gateway] Received HTTP info from unknown/unauthed engine session: {request.sid}") # English log
    @socketio.on("engine_vitals_update", namespace="/engine-socket")
    def handle_engine_vitals_update(data):
        session_info = engine_session_map.get(request.sid)
        if session_info:
            user_id = session_info.get("user_id") # ID Internal User
            engine_id = session_info.get("engine_id")
            if user_id and engine_id:
                with engine_last_seen_lock:
                    engine_last_seen_cache[engine_id] = time.time()
                engine_vitals_cache[engine_id] = data
                payload = {"engine_id": engine_id, "vitals": data}
                socketio.emit(
                    "engine_vitals_update", payload, to=user_id, namespace="/gui-socket"
                )
            else:
                 app.logger.warning(f"[Gateway] Vitals update from engine session {request.sid} missing user/engine ID in map.") # English log
        else:
            app.logger.warning(f"[Gateway] Received vitals from unknown/unauthed engine session: {request.sid}") # English log
    @socketio.on("job_status", namespace="/engine-socket")
    def handle_job_status(data):
        app.logger.debug(f"[Gateway Socket] Received deprecated 'job_status' event from {request.sid}. Ignoring.") # English log
    @socketio.on("disconnect", namespace="/engine-socket")
    def handle_engine_disconnect():
        app.logger.info(f"[Gateway Engine] Client disconnected: {request.sid}") # English log
        with app.app_context(): # Pastikan dalam konteks aplikasi
            session_info = engine_session_map.pop(request.sid, None)
            if not session_info:
                app.logger.warning(f"[Gateway Engine] Disconnect from unknown or already cleaned up session: {request.sid}") # English log
                return
            engine_id = session_info.get("engine_id")
            user_id = session_info.get("user_id") # ID Internal User
            if engine_id:
                engine_url_map.pop(engine_id, None)
                engine_vitals_cache.pop(engine_id, None)
            if (
                user_id in active_engine_sessions
                and request.sid in active_engine_sessions[user_id]
            ):
                active_engine_sessions[user_id].remove(request.sid)
                if not active_engine_sessions[user_id]: # Jika ini session terakhir user
                    del active_engine_sessions[user_id]
            is_still_active = any(
                s_info["engine_id"] == engine_id
                for s_info in engine_session_map.values()
            )
            if not is_still_active and engine_id:
                try:
                    engine = db.session.get(RegisteredEngine, engine_id) # Gunakan get() untuk primary key
                    if engine:
                        engine.status = "offline" # English log
                        db.session.add(engine)
                        db.session.commit()
                        app.logger.info(f"[Gateway Engine] Engine {engine_id} marked as offline in DB.") # English log
                        if user_id: # Pastikan user_id ada
                            socketio.emit(
                                "engine_status_update",
                                {
                                    "engine_id": engine_id,
                                    "name": engine.name,
                                    "status": "offline", # English log
                                    "last_seen": (
                                        engine.last_seen.isoformat()
                                        if engine.last_seen
                                        else None
                                    ),
                                    "vitals": None
                                },
                                to=user_id, # Kirim ke room user (ID internal)
                                namespace="/gui-socket",
                            )
                    else:
                        app.logger.warning(f"[Gateway Engine] Engine {engine_id} not found in DB during disconnect.") # English log
                except Exception as e:
                    app.logger.error(f"[Gateway Engine] Failed to update engine {engine_id} status to offline in DB: {e}") # English log
                    db.session.rollback()
