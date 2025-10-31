#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-gateway\app\routes\proxy.py JUMLAH BARIS 263 
#######################################################################

from flask import Blueprint, request, jsonify, make_response
import requests
import os
from ..helpers import token_required
from ..globals import get_next_core_server, engine_url_map
proxy_bp = Blueprint("proxy", __name__, url_prefix="/api/v1")
@proxy_bp.route("/system-data/components/<component_type>", methods=["GET"])
def proxy_component_list(component_type):
    """
    Proxies requests for component lists (modules, plugins, etc.) to a healthy core server.
    This route is protected by the service-to-service GATEWAY_SECRET_TOKEN (X-API-Key),
    making it accessible to other backend services like Momod API without a user session.
    """
    if component_type not in ["modules", "plugins", "tools", "triggers"]:
        return jsonify({"error": "Invalid component type"}), 400
    core_server_url = get_next_core_server()
    if not core_server_url:
        return (
            jsonify(
                {
                    "error": "No healthy or active Core Engine available to serve component list.",
                    "details": "Please ensure at least one Core Engine is running and connected to the Gateway.",
                }
            ),
            503,
        )
    target_url = f"{core_server_url}/api/v1/{component_type}"
    api_key = os.getenv("GATEWAY_SECRET_TOKEN")
    headers = {"X-API-Key": api_key} if api_key else {}
    try:
        resp = requests.get(
            target_url, headers=headers, timeout=10, params=request.args
        )
        resp.raise_for_status()
        response = make_response(resp.content, resp.status_code)
        for h, v in resp.headers.items():
            if h.lower() not in ["content-encoding", "transfer-encoding", "connection"]:
                response.headers[h] = v
        return response
    except requests.exceptions.RequestException as e:
        return (
            jsonify(
                {
                    "error": "Gateway could not reach Core Server for component list.",
                    "details": str(e),
                }
            ),
            503,  # (PERBAIKAN) Mengembalikan 503 agar Momod API tahu service tidak tersedia
        )
@proxy_bp.route("/health", methods=["GET"])
def proxy_health_check():
    core_server_url = get_next_core_server()
    if not core_server_url:
        return jsonify({"error": "No healthy Core Servers available"}), 503
    target_url = f"{core_server_url}/health"
    headers = {
        k: v
        for k, v in request.headers
        if k.lower() not in ["host", "authorization", "cookie"]
    }
    api_key = os.getenv("GATEWAY_SECRET_TOKEN")
    if api_key:
        headers["X-API-Key"] = api_key
    try:
        resp = requests.get(target_url, headers=headers, timeout=5)
        response = make_response(resp.content, resp.status_code)
        for h, v in resp.headers.items():
            if h.lower() not in ["content-encoding", "transfer-encoding", "connection"]:
                response.headers[h] = v
        return response
    except requests.exceptions.RequestException as e:
        return (
            jsonify(
                {
                    "error": "Gateway could not reach Core Server for health check.",
                    "details": str(e),
                }
            ),
            503,
        )
@proxy_bp.route("/news", methods=["GET"])
def proxy_news_request():
    core_server_url = get_next_core_server()
    if not core_server_url:
        return jsonify({"error": "No healthy Core Servers available"}), 503
    target_url = f"{core_server_url}/api/v1/news"
    headers = {
        k: v
        for k, v in request.headers
        if k.lower() not in ["host", "authorization", "cookie"]
    }
    api_key = os.getenv("GATEWAY_SECRET_TOKEN")
    if api_key:
        headers["X-API-Key"] = api_key
    try:
        resp = requests.get(
            target_url, headers=headers, params=request.args, timeout=15
        )
        excluded_headers = [
            "content-encoding",
            "content-length",
            "transfer-encoding",
            "connection",
        ]
        response_headers = [
            (n, v)
            for n, v in resp.raw.headers.items()
            if n.lower() not in excluded_headers
        ]
        return make_response(resp.content, resp.status_code, response_headers)
    except requests.exceptions.RequestException as e:
        return (
            jsonify(
                {
                    "error": "Gateway could not reach Core Server for news.",
                    "details": str(e),
                }
            ),
            503,
        )
@proxy_bp.route("/localization/<lang_code>", methods=["GET"])
def proxy_localization_request(lang_code):
    core_server_url = get_next_core_server()
    if not core_server_url:
        return jsonify({"error": "No healthy Core Servers available"}), 503
    target_url = f"{core_server_url}/api/v1/localization/{lang_code}"
    headers = {
        k: v
        for k, v in request.headers
        if k.lower() not in ["host", "authorization", "cookie"]
    }
    api_key = os.getenv("GATEWAY_SECRET_TOKEN")
    if api_key:
        headers["X-API-Key"] = api_key
    try:
        resp = requests.get(
            target_url, headers=headers, params=request.args, timeout=15
        )
        excluded_headers = [
            "content-encoding",
            "content-length",
            "transfer-encoding",
            "connection",
        ]
        response_headers = [
            (n, v)
            for n, v in resp.raw.headers.items()
            if n.lower() not in excluded_headers
        ]
        return make_response(resp.content, resp.status_code, response_headers)
    except requests.exceptions.RequestException as e:
        return (
            jsonify(
                {"error": "Gateway could not reach Core Server.", "details": str(e)}
            ),
            503,
        )
@proxy_bp.route("/components/<path:subpath>", methods=["GET"])
def proxy_component_assets(subpath):
    core_server_url = get_next_core_server()
    if not core_server_url:
        return jsonify({"error": "No healthy Core Servers available"}), 503
    target_url = f"{core_server_url}/api/v1/components/{subpath}"
    api_key = os.getenv("GATEWAY_SECRET_TOKEN")
    headers = {"X-API-Key": api_key} if api_key else {}
    try:
        resp = requests.get(
            target_url, headers=headers, stream=True, timeout=10, params=request.args
        )
        excluded_headers = [
            "content-encoding",
            "content-length",
            "transfer-encoding",
            "connection",
        ]
        headers = [
            (name, value)
            for (name, value) in resp.raw.headers.items()
            if name.lower() not in excluded_headers
        ]
        response = make_response(resp.content, resp.status_code)
        for name, value in headers:
            response.headers[name] = value
        return response
    except requests.exceptions.RequestException as e:
        return (
            jsonify(
                {"error": "Gateway could not reach Core Server.", "details": str(e)}
            ),
            503,
        )
@proxy_bp.route("/<path:subpath>", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
@token_required
def proxy_request(current_user, subpath):
    from flask import current_app
    from ..helpers import get_active_engine_for_user
    gateway_handled_routes = [
        "auth/", "presets", "user/", "dashboard/", "billing/", "engine/",
        "system-data/", "news", "localization/", "components/"
    ]
    target_engine_id = request.headers.get("X-Flowork-Engine-ID")
    core_server_url = None
    if target_engine_id and target_engine_id in engine_url_map:
        core_server_url = engine_url_map[target_engine_id]
    else:
        active_engine_id_for_user = get_active_engine_for_user(current_user.id)
        if active_engine_id_for_user and active_engine_id_for_user in engine_url_map:
            core_server_url = engine_url_map[active_engine_id_for_user]
        else:
            core_server_url = get_next_core_server()
    if not core_server_url:
        return (
            jsonify({"error": "No healthy or active Core Engine available for this user"}), # English Hardcode
            503,
        )
    target_url = f"{core_server_url}/api/v1/{subpath}"
    headers = {
        k: v for k, v in request.headers if k.lower() not in ["host", "authorization"]
    }
    api_key = os.getenv("GATEWAY_SECRET_TOKEN")
    if api_key:
        headers["X-API-Key"] = api_key
    if current_user:
        headers["X-Flowork-User-ID"] = str(current_user.id)
        if "X-Flowork-Engine-ID" not in headers and target_engine_id:
            headers["X-Flowork-Engine-ID"] = str(target_engine_id)
    try:
        resp = requests.request(
            method=request.method,
            url=target_url,
            headers=headers,
            data=request.get_data(),
            cookies=request.cookies,
            allow_redirects=False,
            timeout=30,
            params=request.args,
        )
        excluded_headers = [
            "content-encoding",
            "content-length",
            "transfer-encoding",
            "connection",
        ]
        response_headers = [
            (n, v)
            for n, v in resp.raw.headers.items()
            if n.lower() not in excluded_headers
        ]
        return make_response(resp.content, resp.status_code, response_headers)
    except requests.exceptions.RequestException as e:
        return (
            jsonify(
                {"error": "Gateway could not reach Core Server.", "details": str(e)}
            ),
            503,
        )
