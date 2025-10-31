#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-gateway\app\models.py JUMLAH BARIS 284 
#######################################################################

import uuid
import datetime
from sqlalchemy import (
    Text, ForeignKey, DateTime, String, Boolean, Integer, JSON,
    Table, Column, UniqueConstraint, Numeric, Float
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID # Tetap ada jika diperlukan oleh migrasi lama
from .extensions import db
from werkzeug.security import generate_password_hash, check_password_hash
plan_capabilities = Table(
    "plan_capabilities",
    db.metadata,
    Column("plan_id", String, ForeignKey("plans.id"), primary_key=True),
    Column("capability_id", String, ForeignKey("capabilities.id"), primary_key=True),
)
admin_roles_table = Table(
    "admin_roles",
    db.metadata,
    Column("admin_user_id", String, ForeignKey("admin_users.id"), primary_key=True),
    Column("role_id", String, ForeignKey("roles.id"), primary_key=True),
)
role_permissions_table = Table(
    "role_permissions",
    db.metadata,
    Column("role_id", String, ForeignKey("roles.id"), primary_key=True),
    Column("permission_id", String, ForeignKey("permissions.id"), primary_key=True),
)
class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.String, primary_key=True, default=lambda: str(uuid.uuid4()))
    public_address = db.Column(db.String, unique=True, nullable=True, index=True)
    username = db.Column(db.String, nullable=False)
    email = db.Column(db.String, unique=True, nullable=False)
    password_hash = db.Column(db.String, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    status = db.Column(db.String, nullable=False, default="active") # English Hardcode
    last_login_ip = db.Column(db.String, nullable=True)
    engines = relationship("RegisteredEngine", back_populates="user", lazy=True, cascade="all, delete-orphan")
    subscription = relationship("Subscription", back_populates="user", uselist=False, cascade="all, delete-orphan")
    backup = relationship("UserBackup", back_populates="user", uselist=False, cascade="all, delete-orphan")
    presets = relationship("Preset", back_populates="user", lazy=True, cascade="all, delete-orphan")
    workflows = relationship("Workflow", back_populates="owner", lazy=True, cascade="all, delete-orphan")
    variables = relationship("Variable", back_populates="user", lazy=True, cascade="all, delete-orphan")
    states = relationship("State", back_populates="user", lazy=True, cascade="all, delete-orphan")
    scheduled_tasks = relationship("ScheduledTask", back_populates="user", lazy=True, cascade="all, delete-orphan")
    execution_metrics = relationship("ExecutionMetric", back_populates="user", lazy=True, cascade="all, delete-orphan")
    submissions = relationship("MarketplaceSubmission", back_populates="submitter", lazy=True)
    shared_engines_access = relationship("EngineShare", back_populates="shared_with_user", lazy="dynamic") # Engine yang bisa diakses user ini
    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method="pbkdf2:sha256")
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
class RegisteredEngine(db.Model):
    __tablename__ = "registered_engines"
    id = db.Column(db.String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String, db.ForeignKey("users.id"), nullable=False)
    engine_token_hash = db.Column(db.String, unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    name = db.Column(db.String, nullable=False, server_default="My Engine") # English Hardcode
    status = db.Column(db.String, default="offline") # English Hardcode
    last_seen = db.Column(db.DateTime, nullable=True)
    user = relationship("User", back_populates="engines")
    scheduled_tasks = relationship("ScheduledTask", back_populates="engine", lazy=True, cascade="all, delete-orphan")
    execution_metrics = relationship("ExecutionMetric", back_populates="engine", lazy=True, cascade="all, delete-orphan")
    shares = relationship("EngineShare", back_populates="engine", lazy="dynamic", cascade="all, delete-orphan") # Daftar share untuk engine ini
class EngineShare(db.Model):
    __tablename__ = "engine_shares"
    id = db.Column(db.Integer, primary_key=True) # Pakai Integer saja lebih simpel
    engine_id = db.Column(db.String, db.ForeignKey("registered_engines.id", ondelete="CASCADE"), nullable=False, index=True)
    shared_with_user_id = db.Column(db.String, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    shared_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    engine = relationship("RegisteredEngine", back_populates="shares")
    shared_with_user = relationship("User", back_populates="shared_engines_access")
    __table_args__ = (UniqueConstraint('engine_id', 'shared_with_user_id', name='uq_engine_share'),)
class Plan(db.Model):
    __tablename__ = "plans"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    is_public = Column(Boolean, default=True, nullable=False)
    max_executions = Column(Integer, nullable=True)
    features = Column(JSON, nullable=True)
    capabilities = relationship("Capability", secondary=plan_capabilities, lazy="subquery", back_populates="plans")
    prices = relationship("PlanPrice", back_populates="plan", lazy=True, cascade="all, delete-orphan")
    subscriptions = relationship("Subscription", back_populates="plan", lazy=True)
class Capability(db.Model):
    __tablename__ = "capabilities"
    id = Column(String, primary_key=True)
    description = Column(Text)
    plans = relationship("Plan", secondary=plan_capabilities, back_populates="capabilities")
class PlanPrice(db.Model):
    __tablename__ = "plan_prices"
    id = Column(db.Integer, primary_key=True)
    plan_id = Column(String, ForeignKey("plans.id"), nullable=False)
    duration_months = Column(db.Integer, nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="USD") # English Hardcode
    paypal_plan_id = Column(String, unique=True, nullable=True)
    plan = relationship("Plan", back_populates="prices")
class Subscription(db.Model):
    __tablename__ = "subscriptions"
    id = db.Column(db.String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String, db.ForeignKey("users.id"), unique=True, nullable=False)
    tier = db.Column(db.String, db.ForeignKey("plans.id"), nullable=False, default="architect") # Default 'architect'
    expires_at = db.Column(db.DateTime, nullable=True)
    provider_subscription_id = db.Column(db.String, nullable=True, unique=True)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    user = relationship("User", back_populates="subscription")
    plan = relationship("Plan", back_populates="subscriptions")
class FeatureFlag(db.Model):
    __tablename__ = "feature_flags"
    id = Column(String, primary_key=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=False)
    rollout_rules = Column(JSON, nullable=True) # Menggantikan rollout_percentage
    allowed_users = Column(JSON, nullable=True) # Menggantikan allowed_user_ids
class UserBackup(db.Model):
    __tablename__ = "user_backups"
    id = db.Column(db.String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String, db.ForeignKey("users.id"), unique=True, nullable=False)
    backup_file_path = db.Column(db.String, nullable=True) # Dibuat nullable
    salt_b64 = db.Column(db.String, nullable=True) # Dibuat nullable
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    user = relationship("User", back_populates="backup")
class Preset(db.Model):
    __tablename__ = "presets"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    workflow_data = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    user = relationship("User", back_populates="presets")
    versions = relationship("PresetVersion", back_populates="preset", lazy=True, cascade="all, delete-orphan")
    __table_args__ = (UniqueConstraint('user_id', 'name', name='uq_user_preset_name'),)
class PresetVersion(db.Model):
    __tablename__ = "preset_versions"
    id = Column(Integer, primary_key=True)
    preset_id = Column(String, ForeignKey("presets.id", ondelete="CASCADE"), nullable=False)
    workflow_data = Column(JSON, nullable=False)
    version_message = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    preset = relationship("Preset", back_populates="versions")
class Workflow(db.Model):
    __tablename__ = "workflows"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_id = Column(String, ForeignKey("users.id"), nullable=False)
    preset_name = Column(String, nullable=False)
    friendly_name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    owner = relationship("User", back_populates="workflows")
    shares = relationship("WorkflowShare", back_populates="workflow", lazy=True, cascade="all, delete-orphan")
    __table_args__ = (UniqueConstraint('owner_id', 'preset_name', name='uq_owner_preset'),)
class WorkflowShare(db.Model):
    __tablename__ = "workflow_shares"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workflow_id = Column(String, ForeignKey("workflows.id"), nullable=False)
    share_token = Column(String, unique=True, nullable=False)
    permission_level = Column(String, nullable=False)
    link_name = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    workflow = relationship("Workflow", back_populates="shares")
class Variable(db.Model):
    __tablename__ = "variables"
    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    value_data = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    user = relationship("User", back_populates="variables")
    __table_args__ = (UniqueConstraint('user_id', 'name', name='uq_user_variable_name'),)
class State(db.Model):
    __tablename__ = "states"
    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    key = Column(String, nullable=False)
    value = Column(JSON, nullable=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    user = relationship("User", back_populates="states")
    __table_args__ = (UniqueConstraint('user_id', 'key', name='uq_user_state_key'),)
class ScheduledTask(db.Model):
    __tablename__ = "scheduled_tasks"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    engine_id = Column(String, ForeignKey("registered_engines.id"), nullable=False)
    task_type = Column(String, nullable=False)
    scheduled_for = Column(DateTime, nullable=False)
    os_task_name = Column(String, unique=True, nullable=False)
    status = Column(String, nullable=False, default="pending") # English Hardcode
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    user = relationship("User", back_populates="scheduled_tasks")
    engine = relationship("RegisteredEngine", back_populates="scheduled_tasks")
class ExecutionMetric(db.Model):
    __tablename__ = "execution_metrics"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    engine_id = Column(String, ForeignKey("registered_engines.id"), nullable=False)
    workflow_context_id = Column(String, nullable=False, index=True)
    preset_name = Column(String, nullable=True)
    node_id = Column(String, nullable=False)
    node_name = Column(String, nullable=True)
    module_id = Column(String, nullable=True)
    status = Column(String, nullable=False)
    execution_time_ms = Column(Float, nullable=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    user = relationship("User", back_populates="execution_metrics")
    engine = relationship("RegisteredEngine", back_populates="execution_metrics")
class MarketplaceSubmission(db.Model):
    __tablename__ = "marketplace_submissions"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    submitter_user_id = Column(String, ForeignKey("users.id"), nullable=False)
    component_id = Column(String, nullable=False)
    component_type = Column(String, nullable=False)
    version = Column(String, nullable=False)
    status = Column(String, nullable=False, default="pending") # English Hardcode
    submitted_at = Column(DateTime, default=datetime.datetime.utcnow)
    reviewed_at = Column(DateTime, nullable=True)
    admin_notes = Column(Text, nullable=True)
    staged_file_path = Column(String, nullable=True) # Ditambahkan kembali di migrasi e6a0...
    submitter = relationship("User", back_populates="submissions")
class GloballyDisabledComponent(db.Model):
    __tablename__ = "globally_disabled_components"
    component_id = Column(String, primary_key=True)
    reason = Column(Text, nullable=False)
    disabled_at = Column(DateTime, default=datetime.datetime.utcnow)
class AdminUser(db.Model):
    __tablename__ = "admin_users"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    roles = relationship("Role", secondary=admin_roles_table, back_populates="admins")
    audit_logs = relationship("AuditLog", back_populates="admin", lazy="selectin")
class Role(db.Model):
    __tablename__ = "roles"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, unique=True, nullable=False)
    description = Column(String)
    admins = relationship("AdminUser", secondary=admin_roles_table, back_populates="roles")
    permissions = relationship("Permission", secondary=role_permissions_table, back_populates="roles", lazy="joined") # <-- FIXED back_populates to 'roles'
class Permission(db.Model):
    __tablename__ = "permissions"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, unique=True, nullable=False)
    roles = relationship("Role", secondary=role_permissions_table, back_populates="permissions")
class AuditLog(db.Model):
    __tablename__ = "audit_logs"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    admin_id = Column(String, ForeignKey("admin_users.id"), nullable=False)
    action = Column(String, nullable=False)
    target_resource = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    ip_address = Column(String, nullable=True)
    admin = relationship("AdminUser", back_populates="audit_logs")
class ExecutionJob(db.Model):
    __tablename__ = "execution_jobs"
    id = db.Column(db.String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False)
    target_engine_id = db.Column(db.String, db.ForeignKey('registered_engines.id'), nullable=True)
    workflow_id = db.Column(db.String(255), nullable=False)
    payload = db.Column(JSON, nullable=False)
    status = db.Column(db.String(50), default='PENDING', nullable=False) # English Hardcode: PENDING, DISPATCHED, COMPLETED, FAILED
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    error_message = db.Column(db.Text, nullable=True)
    user = relationship("User")
    engine = relationship("RegisteredEngine")
    def __repr__(self):
        return f"<ExecutionJob {self.id} Status: {self.status}>"
Engine = RegisteredEngine
try:
    from .models.user import User as SubmoduleUser # Renaming to avoid conflict during definition
    from .models.user import AdminUser as SubmoduleAdminUser # If AdminUser is also in the submodule
except ImportError:
    pass # Ignore if submodule doesn't exist, as primary models are defined above
