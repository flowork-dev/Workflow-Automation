#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-gateway\app\globals.py JUMLAH BARIS 91 
#######################################################################

import threading
import time
import random
import requests
import os
import json
from collections import deque, defaultdict
import hmac
engine_last_seen_cache = {}
engine_last_seen_lock = threading.Lock()
active_engine_sessions = {}
engine_session_map = {}
engine_url_map = {}
engine_vitals_cache = {}
job_statuses = {}
job_statuses_lock = threading.Lock()
gui_sessions = {}
g_core_servers = []
g_server_lock = threading.Lock()
HEALTH_CHECK_INTERVAL = 10
healthy_core_servers = []
health_lock = threading.Lock()
traffic_log = deque(maxlen=100)
request_counter = 0
counter_lock = threading.Lock()
pending_auths = {}
RATE_LIMIT_ATTEMPTS = 20
RATE_LIMIT_WINDOW = 60
connection_attempts = defaultdict(list)
rate_limit_lock = threading.Lock()
def perform_health_checks(app):
    """
    Versi baru yang menerima 'app' agar bisa mengakses logger.
    (PERBAIKAN KUNCI) Logika diubah total untuk memeriksa engine yang terhubung secara internal.
    """
    global healthy_core_servers
    while True:
        with app.app_context():
            current_healthy = []
            servers_to_check = list(engine_url_map.values())
            app.logger.info(
                f"[MATA-MATA HEALTH-CHECK] Akan memeriksa server internal: {servers_to_check}"
            )
            for server_url in servers_to_check:
                try:
                    resp = requests.get(f"{server_url}/health", timeout=2)
                    if resp.status_code == 200 and resp.json().get("status") == "ready":
                        current_healthy.append(server_url)
                        app.logger.info(
                            f"[MATA-MATA HEALTH-CHECK] Server {server_url} SEHAT!"
                        )
                    else:
                        app.logger.warning(
                            f"[MATA-MATA HEALTH-CHECK] Server {server_url} TIDAK SEHAT, status code: {resp.status_code}"
                        )
                except requests.exceptions.RequestException as e:
                    app.logger.error(
                        f"[MATA-MATA HEALTH-CHECK] Gagal total menghubungi server {server_url}: {e}"
                    )
            with health_lock:
                healthy_core_servers = current_healthy
                app.logger.info(
                    f"[MATA-MATA HEALTH-CHECK] Daftar server yang sehat sekarang: {healthy_core_servers}"
                )
        time.sleep(HEALTH_CHECK_INTERVAL)
def get_next_core_server():
    with health_lock:
        if not healthy_core_servers:
            return None
        return random.choice(healthy_core_servers)
def load_servers(app):
    """Membaca konfigurasi server dari servers.json"""
    global g_core_servers
    APP_DIR = os.path.dirname(os.path.abspath(__file__))
    SERVER_CONFIG_FILE = os.path.join(APP_DIR, "..", "servers.json")
    with g_server_lock:
        if not os.path.exists(SERVER_CONFIG_FILE):
            g_core_servers = []
        else:
            try:
                with open(SERVER_CONFIG_FILE, "r") as f:
                    g_core_servers = json.load(f)
            except:
                g_core_servers = []
