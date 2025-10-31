import os
import sys
import threading
import logging
from flask import Flask, jsonify
from app.config import Config
from app.extensions import db, jwt, migrate, cors, sse_message_queue

# (COMMENT) This path logic seems correct based on the Dockerfile
GATEWAY_ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
CORE_ROOT_PATH = os.path.join(GATEWAY_ROOT_PATH, 'flowork-core')
# (COMMENT) Make sure PYTHONPATH is set so this import works
sys.path.insert(0, GATEWAY_ROOT_PATH) # (COMMENT) Add gateway root
sys.path.insert(0, CORE_ROOT_PATH) # (COMMENT) Add core root

try:
    from flowork_kernel.kernel import Kernel
    from flowork_kernel.services.job_worker_service.job_worker_service import JobWorkerService
    from flowork_kernel.services.community_addon_service.community_addon_service import CommunityAddonService
except ImportError as e:
    print(f"FATAL ERROR: Tidak bisa import flowork_kernel. Cek Dockerfile PYTHONPATH. {e}")
    Kernel = None
    JobWorkerService = None
    CommunityAddonService = None

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # (COMMENT) JWT Config for SSE
    app.config["JWT_QUERY_STRING_NAME"] = "token"
    app.config["JWT_QUERY_STRING_ENABLED"] = True

    # (COMMENT) Init extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    CORS_ORIGINS = [
        "https://flowork.cloud",
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ]
    cors.init_app(app, resources={r"/api/v1/*": {"origins": CORS_ORIGINS}}, supports_credentials=True)
    logger.info(f"CORS enabled for origins: {CORS_ORIGINS}")

    # (COMMENT) Register JWT error handlers
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return jsonify({"error": "Token is invalid"}), 401

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({"error": "Token has expired"}), 401

    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return jsonify({"error": "Authorization token is missing"}), 401

    # (COMMENT) Register Blueprints
    with app.app_context():
        from app.routes.auth import auth_bp
        from app.routes.engine import engine_bp
        from app.routes.execution import exec_bp
        from app.routes.streaming import stream_bp
        from app.routes.user import user_bp
        from app.routes.user_state import user_state_bp
        from app.routes.system import system_bp
        from app.routes.dashboard import dashboard_bp
        from app.routes.components import comp_bp
        # (COMMENT) Import rute baru
        from app.routes.shares import shares_bp
        from app.routes.workflow_shares import workflow_shares_bp

        app.register_blueprint(auth_bp, url_prefix='/api/v1/auth')
        app.register_blueprint(engine_bp, url_prefix='/api/v1/user')
        app.register_blueprint(exec_bp, url_prefix='/api/v1/execute')
        app.register_blueprint(stream_bp, url_prefix='/api/v1/stream')
        app.register_blueprint(user_bp, url_prefix='/api/v1/user')
        app.register_blueprint(user_state_bp, url_prefix='/api/v1/user/state')
        app.register_blueprint(system_bp, url_prefix='/api/v1/system')
        app.register_blueprint(dashboard_bp, url_prefix='/api/v1/dashboard')
        app.register_blueprint(comp_bp, url_prefix='/api/v1/components')
        # (COMMENT) Register rute baru
        app.register_blueprint(shares_bp)
        app.register_blueprint(workflow_shares_bp)

        logger.info("All blueprints registered.") # Ini udah jalan

    # (COMMENT) Start Background Services
    if JobWorkerService and CommunityAddonService:
        with app.app_context():
            logger.info("Starting background services...") # Ini udah jalan
            app.kernel = Kernel(project_root_path=CORE_ROOT_PATH)

            app.job_worker = JobWorkerService(app.kernel, app) # [MODIFIED]
            worker_thread = threading.Thread(target=app.job_worker.start)
            worker_thread.daemon = True
            worker_thread.start()
            logger.info("JobWorkerService started.")

            app.installer_service = CommunityAddonService(app.kernel, "community_addon_service") # [MODIFIED] (Pass service_id)

            # (COMMENT) This line was the error: AttributeError: 'Kernel' object has no attribute 'register_service'
            # app.kernel.register_service("community_addon_service", app.installer_service) # English Hardcode

            # (FIX) Manually assign the service to the kernel's service dictionary.
            app.kernel.services["community_addon_service"] = app.installer_service # English Hardcode

            logger.info("CommunityAddonService registered.")
    else:
        logger.error("FATAL: Worker services (JobWorkerService or CommunityAddonService) not found.")

    return app