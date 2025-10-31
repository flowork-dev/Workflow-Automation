#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-gateway\seed_dev_engine.py JUMLAH BARIS 83 
#######################################################################

import os
import sys
import secrets
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash
APP_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, APP_DIR) # (PERBAIKAN) Seharusnya APP_DIR, bukan os.path.dirname(APP_DIR)
dotenv_path = os.path.join(os.path.dirname(APP_DIR), ".env")
load_dotenv(dotenv_path)
try:
    from app import create_app
    from app.extensions import db
    from app.models import User, RegisteredEngine
except ImportError as e:
    print(f"Error importing Flask app components: {e}", file=sys.stderr)
    print(f"Current sys.path: {sys.path}", file=sys.stderr)
    print("Ensure this script is run from the 'flowork-gateway' directory or that the path is correct.", file=sys.stderr)
    sys.exit(1)
DEFAULT_ENGINE_NAME = "Default Dev Engine"
DEFAULT_USER_EMAIL = "flowork@flowork.cloud"
ENGINE_ID_FROM_ENV = os.getenv("FLOWORK_ENGINE_ID")
ENGINE_TOKEN_FROM_ENV = os.getenv("FLOWORK_ENGINE_TOKEN")
def seed_default_engine():
    """
    (PERBAIKAN) Seeds or syncs the default development engine using credentials
    from the .env file.
    """
    app = create_app()
    with app.app_context():
        print("--- Flowork Gateway Development Engine Seeder ---")
        if not ENGINE_ID_FROM_ENV or not ENGINE_TOKEN_FROM_ENV:
            print(f"FATAL ERROR: FLOWORK_ENGINE_ID or FLOWORK_ENGINE_TOKEN is not set in the environment.", file=sys.stderr)
            print(f"Please check your docker-compose.yml and .env file.", file=sys.stderr)
            print(f"Read ID: {ENGINE_ID_FROM_ENV}, Read Token: {ENGINE_TOKEN_FROM_ENV[:5] if ENGINE_TOKEN_FROM_ENV else 'NONE'}...")
            print("\n--- Development Engine Seeding Failed ---")
            sys.exit(1) # Gagal seeding jika var tidak ada
        dev_user = User.query.filter_by(email=DEFAULT_USER_EMAIL).first()
        if not dev_user:
            print(f"ERROR: Development user '{DEFAULT_USER_EMAIL}' not found. Please run 'create_admin.py' first or check the email address.")
            print("\n--- Development Engine Seeding Failed ---")
            return
        print(f"Found user '{dev_user.username}' (ID: {dev_user.id}). Checking for engine ID: {ENGINE_ID_FROM_ENV}...")
        existing_engine = db.session.get(RegisteredEngine, ENGINE_ID_FROM_ENV) # (PERBAIKAN) Gunakan db.session.get
        try:
            token_hash = generate_password_hash(ENGINE_TOKEN_FROM_ENV, method="pbkdf2:sha256")
            if existing_engine:
                print(f"Engine '{existing_engine.name}' (ID: {ENGINE_ID_FROM_ENV}) already exists.")
                print(f"Re-syncing token hash in database...")
                existing_engine.engine_token_hash = token_hash
                existing_engine.user_id = dev_user.id # Pastikan owner-nya benar
                existing_engine.name = DEFAULT_ENGINE_NAME # Pastikan namanya benar
                db.session.add(existing_engine)
            else:
                print(f"Engine ID '{ENGINE_ID_FROM_ENV}' not found. Creating it now...")
                new_engine = RegisteredEngine(
                    id=ENGINE_ID_FROM_ENV, # Gunakan ID dari .env
                    user_id=dev_user.id,
                    name=DEFAULT_ENGINE_NAME,
                    engine_token_hash=token_hash, # Gunakan hash dari token .env
                    status='offline' # Status awal
                )
                db.session.add(new_engine)
            db.session.commit()
            print(f"[SUCCESS] Default development engine is now synced with your .env file.")
            print(f"          Engine Name: {DEFAULT_ENGINE_NAME}")
            print(f"          Engine ID  : {ENGINE_ID_FROM_ENV}")
        except Exception as e:
            db.session.rollback()
            print(f"ERROR: Failed to create or sync default engine: {e}")
            import traceback
            traceback.print_exc(file=sys.stderr)
            print("\n--- Development Engine Seeding Failed ---")
            return
        print("\n--- Development Engine Seeding Complete ---")
if __name__ == "__main__":
    seed_default_engine()
