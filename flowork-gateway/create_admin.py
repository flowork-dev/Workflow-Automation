#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-gateway\create_admin.py JUMLAH BARIS 167 
#######################################################################

import sys
import os
import argparse
import secrets
from eth_account import Account
from werkzeug.security import generate_password_hash
from getpass import getpass
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from app import create_app, db
from app.models import AdminUser, Role, Permission, Plan, User, Subscription, PlanPrice
Account.enable_unaudited_hdwallet_features()
parser = argparse.ArgumentParser(
    description="Flowork Gateway Admin User & Initial Data Seeder"
)
parser.add_argument(
    "--username", default="flowork", help="Username for the admin and regular user."
)
parser.add_argument(
    "--email",
    default="flowork@flowork.cloud",
    help="Email for the corresponding regular user.",
)
parser.add_argument(
    "--password", default="Aola-#1987", help="Password for the admin and user."
)
parser.add_argument(
    "--reset", action="store_true", help="Flag to reset password if user exists."
)
args = parser.parse_args()
app = create_app()
with app.app_context():
    print("--- Flowork Gateway Initializer ---")
    username = args.username
    email = args.email
    password = args.password
    admin_user_to_modify = AdminUser.query.filter_by(username=username).first()
    if admin_user_to_modify:
        if args.reset:
            print(
                f"Admin User '{username}' exists. Resetting password and verifying roles."
            )
        else:
            print(f"Skipping admin user creation: '{username}' already exists.")
    else:
        print(f"Admin User '{username}' not found. Creating new admin user.")
        admin_user_to_modify = AdminUser(username=username)
    admin_user_to_modify.password_hash = generate_password_hash(
        password, method="pbkdf2:sha256"
    )
    superadmin_role = Role.query.filter_by(name="superadmin").first()
    if not superadmin_role:
        print("Creating 'superadmin' role...")
        superadmin_role = Role(name="superadmin", description="Full system access")
        db.session.add(superadmin_role)
    all_permissions = [
        "dashboard:read", "dashboard:read_financial", "plan:read", "plan:update",
        "plan:create", "plan:delete", "users:read", "users:create", "users:update",
        "users:delete", "system:read", "system:update", "features:read",
        "features:create", "features:update", "features:delete",
    ]
    for perm_name in all_permissions:
        permission = Permission.query.filter_by(name=perm_name).first()
        if not permission:
            permission = Permission(name=perm_name)
            db.session.add(permission)
        if permission not in superadmin_role.permissions:
            superadmin_role.permissions.append(permission)
    if superadmin_role not in admin_user_to_modify.roles:
        admin_user_to_modify.roles.append(superadmin_role)
        print(f"Assigned 'superadmin' role to admin user '{username}'.")
    if not admin_user_to_modify in db.session:
        db.session.add(admin_user_to_modify)
    print(f"Admin user '{username}' configured.")
    print("Checking for corresponding regular user...")
    regular_user = User.query.filter_by(email=email).first()
    if not regular_user:
        print(f"Regular user for '{email}' not found. Creating now...")
        priv_key_bytes = secrets.token_bytes(32)
        new_account = Account.from_key(priv_key_bytes)
        new_private_key_hex = new_account.key.hex() # Ini string tanpa 0x
        new_public_address = new_account.address # Ini string DENGAN 0x
        full_private_key = f"0x{new_private_key_hex}"
        print("\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print("!!!            CRITICAL: NEW ADMIN ACCOUNT IDENTITY GENERATED            !!!")
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print(f"!!! Public Address (Username): {new_public_address}")
        print(f"!!! LOGIN PRIVATE KEY (Copy This): {full_private_key}")
        print("!!! (This key is required to log in via the GUI)")
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n")
        hashed_password = generate_password_hash(password, method="pbkdf2:sha256")
        new_regular_user = User(
            username=username,
            email=email,
            password_hash=hashed_password,
            status="active",
            public_address=new_public_address
        )
        db.session.add(new_regular_user)
        db.session.flush() # Get the new user ID
        free_subscription = Subscription(user_id=new_regular_user.id, tier="architect")
        db.session.add(free_subscription)
        print(
            f"Successfully created regular user '{username}' with email '{email}' and an architect subscription."
        )
    else:
        print(
            f"Corresponding regular user with email '{email}' already exists. Skipping creation."
        )
        if not regular_user.public_address:
            priv_key_bytes = secrets.token_bytes(32)
            new_account = Account.from_key(priv_key_bytes)
            new_private_key_hex = new_account.key.hex() # Ini string tanpa 0x
            new_public_address = new_account.address # Ini string DENGAN 0x
            full_private_key = f"0x{new_private_key_hex}"
            print("\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            print("!!! CRITICAL: NEW IDENTITY GENERATED (FOR EXISTING USER) !!!")
            print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            print(f"!!! Public Address (Username): {new_public_address}")
            print(f"!!! LOGIN PRIVATE KEY (Copy This): {full_private_key}")
            print("!!! (This key is required to log in via the GUI)")
            print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n")
            regular_user.public_address = new_public_address
            print(f"Updated existing user '{email}' with new public address: {new_public_address}")
    default_plans_data = {
        "free": {
            "name": "Standard",
            "description": "Base plan for all users.",
            "is_public": True,
            "max_executions": None, # Unlimited in Open Core
            "features": [
                "Unlimited Self-Hosted Engines",
                "Full Workflow Designer Access",
                "All Core Nodes",
                "Community Support",
            ],
            "prices": [], # No pricing tiers for Open Core base plan
        },
    }
    print("\n--- Seeding and Verifying Default Plan Structure ---")
    for plan_id, data in default_plans_data.items():
        plan = Plan.query.filter_by(id=plan_id).first()
        if not plan:
            print(f"Plan '{plan_id}' not found. Creating it...")
            plan = Plan(id=plan_id)
            db.session.add(plan)
        plan.name = data["name"]
        plan.description = data["description"]
        plan.is_public = data["is_public"]
        plan.max_executions = data["max_executions"]
        plan.features = data["features"]
        print(f"Plan '{plan_id}' structure configured.")
        PlanPrice.query.filter_by(plan_id=plan_id).delete()
        print(f" -> Removed any existing price tiers for '{plan_id}'.")
    try:
        db.session.commit()
        print("\n--- Initialization Complete ---")
    except Exception as e:
        db.session.rollback()
        print(f"\n--- Initialization FAILED: {e} ---")
        print("Please check database connection and schema.")
