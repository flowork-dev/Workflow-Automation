#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-gateway\app\routes\system.py JUMLAH BARIS 93 
#######################################################################

from flask import Blueprint, jsonify, current_app, request
from ..helpers import engine_token_required, admin_token_required
from ..models import GloballyDisabledComponent, Capability, Plan
from ..extensions import db # , redis_client <-- DIHAPUS
system_bp = Blueprint("system", __name__, url_prefix="/api/v1/system")
@system_bp.route("/health", methods=["GET"])
def health_check():
    """
    Endpoint sederhana untuk Docker health check.
    Merespons jika server Flask berjalan dan DB (SQLite) terkoneksi.
    """
    try:
        db.session.execute(db.text("SELECT 1"))
        return jsonify({"status": "healthy", "database": "connected"}), 200 # English Hardcode
    except Exception as e:
        current_app.logger.error(f"[Gateway Health] Health check failed: {e}") # English Hardcode
        return jsonify({"status": "unhealthy", "database": "disconnected", "error": str(e)}), 503 # English Hardcode
@system_bp.route("/disabled-components", methods=["GET"])
@engine_token_required
def get_disabled_components():
    """
    Provides a list of globally disabled component IDs.
    This endpoint is intended to be called by Core Engines to sync their kill switch list.
    """
    try:
        disabled_components = GloballyDisabledComponent.query.all()
        disabled_ids = [c.component_id for c in disabled_components]
        return jsonify(disabled_ids)
    except Exception as e:
        current_app.logger.error(
            f"[Gateway System Route] Failed to fetch disabled components: {e}" # English Hardcode
        )
        return jsonify({"error": "Failed to fetch system configuration."}), 500 # English Hardcode
@system_bp.route("/capabilities", methods=["GET"])
@admin_token_required # Membutuhkan token admin (dari Momod GUI)
def get_all_capabilities(**kwargs): # Terima **kwargs
    """
    Fetches a list of all available system capabilities.
    """
    try:
        capabilities = Capability.query.order_by(Capability.id).all()
        return jsonify([{"id": c.id, "description": c.description} for c in capabilities])
    except Exception as e:
        current_app.logger.error(f"[Gateway System Route] Failed to fetch capabilities: {e}") # English Hardcode
        return jsonify({"error": "Failed to fetch capabilities."}), 500 # English Hardcode
@system_bp.route("/plans/<plan_id>/capabilities", methods=["PUT"])
@admin_token_required # Membutuhkan token admin (dari Momod GUI)
def update_plan_capabilities(plan_id, **kwargs):
    """
    Updates the list of capabilities associated with a specific plan.
    """
    if 'admin_permissions' in kwargs and 'plan:update' not in kwargs['admin_permissions']:
        return jsonify({"error": "Admin permission 'plan:update' required."}), 403 # English Hardcode
    data = request.get_json()
    if data is None or 'capability_ids' not in data:
        return jsonify({"error": "Missing 'capability_ids' in request body."}), 400 # English Hardcode
    plan = Plan.query.options(db.joinedload(Plan.capabilities)).filter_by(id=plan_id).first()
    if not plan:
        return jsonify({"error": "Plan not found."}), 404 # English Hardcode
    try:
        new_capability_ids = set(data.get('capability_ids', []))
        plan.capabilities = [cap for cap in plan.capabilities if cap.id in new_capability_ids]
        current_cap_ids = {cap.id for cap in plan.capabilities}
        caps_to_add = new_capability_ids - current_cap_ids
        if caps_to_add:
            new_caps = Capability.query.filter(Capability.id.in_(caps_to_add)).all()
            for cap in new_caps:
                plan.capabilities.append(cap)
        db.session.commit()
        current_app.logger.info(f"[Gateway System Route] Capabilities for plan '{plan_id}' updated. (Cache invalidation skipped - No Redis)") # English Hardcode
        db.session.refresh(plan)
        plan_data = {
            "id": plan.id,
            "name": plan.name,
            "description": plan.description,
            "is_public": plan.is_public,
            "max_executions": plan.max_executions,
            "features": plan.features,
            "capabilities": [{"id": c.id, "description": c.description} for c in plan.capabilities],
            "prices": [{"duration_months": p.duration_months, "price": float(p.price)} for p in plan.prices]
        }
        return jsonify(plan_data)
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"[Gateway System Route] Failed to update plan capabilities: {e}") # English Hardcode
        return jsonify({"error": "Failed to update plan capabilities."}), 500 # English Hardcode
