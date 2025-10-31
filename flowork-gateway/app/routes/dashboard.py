#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-gateway\app\routes\dashboard.py JUMLAH BARIS 73 
#######################################################################

from flask import Blueprint, jsonify, current_app
import requests
import os
from datetime import datetime, timedelta
from collections import Counter, defaultdict
from sqlalchemy import func
from ..helpers import crypto_auth_required, get_active_engine_for_user
from ..globals import engine_url_map
from ..models import User, RegisteredEngine, EngineShare
from ..extensions import db
dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/api/v1/dashboard")
def _get_live_stats_from_core(user_id, app):
    """
    (PERBAIKAN) Helper to fetch live data (active jobs, system overview) from the user's
    active core engine (owned OR the first active shared engine).
    Uses the modified `get_active_engine_for_user` helper.
    """
    app.logger.info(f"[Gateway Dashboard] Fetching live stats for user_id: {user_id}") # English Log
    core_user_id = None
    user = User.query.get(user_id)
    if user:
        core_user_id = user.public_address # Gunakan public address sebagai ID untuk Core
    else:
        app.logger.warning(f"[_get_live_stats_from_core] User ID {user_id} not found in Gateway DB.") # English Log
        return {"active_jobs": [], "system_overview": {}} # English Hardcode
    if not core_user_id:
        app.logger.warning(f"[_get_live_stats_from_core] User {user_id} has no public_address set.") # English Log
        return {"active_jobs": [], "system_overview": {}} # English Hardcode
    active_engine_id = get_active_engine_for_user(user_id) # Gunakan helper yang sudah dimodifikasi
    core_server_url = None
    if active_engine_id and active_engine_id in engine_url_map:
        core_server_url = engine_url_map[active_engine_id]
        app.logger.info(f"[Gateway Dashboard] Found active engine URL: {core_server_url} for engine_id: {active_engine_id} (User: {user_id})") # English Log
    else:
        app.logger.warning(f"[Gateway Dashboard] No active engine URL found in `engine_url_map` for engine_id: {active_engine_id} (User: {user_id}). Cannot fetch live stats.") # English Log
        return {"active_jobs": [], "system_overview": {}} # Return empty data if no active engine URL
    target_url = f"{core_server_url}/api/v1/engine/live-stats"
    api_key = os.getenv("GATEWAY_SECRET_TOKEN")
    headers = {"X-API-Key": api_key} if api_key else {}
    headers["X-Flowork-User-ID"] = core_user_id
    app.logger.info(f"[Gateway Dashboard] Calling Core Engine endpoint: {target_url} with User-ID header: {core_user_id[:10]}...") # English Log
    try:
        resp = requests.get(target_url, headers=headers, timeout=5)
        resp.raise_for_status()
        live_data = resp.json()
        app.logger.info(f"[Gateway Dashboard] Successfully fetched live stats from Core Engine {active_engine_id}. Active jobs: {len(live_data.get('active_jobs', []))}") # English Log
        return live_data
    except requests.exceptions.RequestException as e:
        app.logger.error(
            f"[Gateway Dashboard] Could not fetch live stats from engine {core_server_url}: {e}" # English Hardcode
        )
        return {"active_jobs": [], "system_overview": {}} # Return empty data on failure
@dashboard_bp.route("/summary", methods=["GET"])
@crypto_auth_required
def get_dashboard_summary(current_user):
    """
    (REMASTERED - PERBAIKAN) Generates dashboard summary.
    Fetches ALL stats (live and historical) directly from the user's Core Engine.
    """
    app = current_app._get_current_object()
    live_stats = _get_live_stats_from_core(current_user.id, app) # Gunakan current_user.id internal
    summary_data = {
        **live_stats, # Data dari Core (sekarang berisi active_jobs, system_overview, DAN STATISTIK)
    }
    app.logger.info(f"[Gateway Dashboard] Returning summary for user {current_user.id}. Active Jobs: {len(summary_data.get('active_jobs',[]))}") # English Log
    return jsonify(summary_data)
