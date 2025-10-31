#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-gateway\app\routes\execution.py JUMLAH BARIS 60 
#######################################################################

import time # [ADD] Added for retry delay
from sqlalchemy.exc import OperationalError # [ADD] Added for specific lock catching
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import ExecutionJob, Engine, EngineShare, User
from app.extensions import db
from app.helpers.cache import check_permission_with_cache # Kita akan buat ini di Langkah 2.2
exec_bp = Blueprint('execution', __name__)
@exec_bp.route('/api/v1/execute/workflow/<string:workflow_id>', methods=['POST'])
@jwt_required()
def queue_workflow_execution(workflow_id):
    user_id = get_jwt_identity()
    data = request.json
    engine_id = data.get('engine_id')
    payload = data.get('payload') # Ini adalah JSON workflow-nya
    if not engine_id or not payload:
        return jsonify({"error": "engine_id and payload are required"}), 400
    if not check_permission_with_cache(user_id, engine_id):
        return jsonify({"error": "Forbidden or engine not found"}), 403
    try:
        new_job = ExecutionJob(
            workflow_id=workflow_id,
            user_id=user_id,
            engine_id=engine_id,
            payload=payload,
            status='pending' # Status awal: pending
        )
        max_retries = 3
        retry_delay_seconds = 0.05 # 50ms
        for attempt in range(max_retries):
            try:
                db.session.add(new_job)
                db.session.commit()
                return jsonify({
                    "message": "Job queued successfully",
                    "job_id": new_job.id
                }), 202
            except OperationalError as e:
                db.session.rollback()
                if "database is locked" in str(e) and attempt < max_retries - 1: # English Hardcode
                    print(f"WARN: Database locked on API endpoint, retrying (Attempt {attempt + 1})...") # English Hardcode
                    time.sleep(retry_delay_seconds)
                else:
                    print(f"ERROR: Failed to commit job after retries or due to non-lock error: {e}") # English Hardcode
                    return jsonify({"error": "Failed to queue job (server busy)"}), 503 # 503 Service Unavailable is more appropriate # English Hardcode
            except Exception as e:
                db.session.rollback()
                print(f"Error saat queue job: {e}")
                return jsonify({"error": "Failed to queue job"}), 500
    except Exception as e:
        db.session.rollback()
        print(f"Error saat queue job (luar retry): {e}")
        return jsonify({"error": "Failed to queue job"}), 500
