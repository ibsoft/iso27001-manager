import hashlib
from datetime import datetime, timedelta
from flask_login import UserMixin
from app.extensions import db, bcrypt

user_roles = db.Table(
    "user_roles",
    db.Column("user_id", db.Integer, db.ForeignKey("user.id"), primary_key=True),
    db.Column("role_id", db.Integer, db.ForeignKey("role.id"), primary_key=True),
)


class User(UserMixin, db.Model):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128), nullable=False)
    first_name = db.Column(db.String(64), nullable=False)
    last_name = db.Column(db.String(64), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    is_mfa_enabled = db.Column(db.Boolean, default=False)
    mfa_secret = db.Column(db.String(32), nullable=True)
    login_attempts = db.Column(db.Integer, default=0)
    last_login_attempt = db.Column(db.DateTime, nullable=True)
    last_login = db.Column(db.DateTime, nullable=True)
    password_changed_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    phone_number = db.Column(db.String(32), nullable=True)
    mobile_phone = db.Column(db.String(32), nullable=True)
    timezone = db.Column(db.String(64), nullable=True, default="UTC")
    default_language = db.Column(db.String(8), nullable=True)
    avatar_url = db.Column(db.String(512), nullable=True)
    auth_source = db.Column(db.String(16), nullable=False, default="local", comment="local|ldap|saml")

    roles = db.relationship("Role", secondary=user_roles, lazy="subquery",
                            backref=db.backref("users", lazy=True))

    department_id = db.Column(db.Integer, db.ForeignKey("department.id"), nullable=True)
    manager_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)

    department = db.relationship("Department", backref=db.backref("members", lazy="dynamic"),
                                 foreign_keys=[department_id])
    manager = db.relationship("User", backref=db.backref("managed_users", lazy="dynamic"),
                              remote_side="User.id", foreign_keys=[manager_id])

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def gravatar_url(self):
        email_hash = hashlib.md5(self.email.lower().encode()).hexdigest()
        return f"https://www.gravatar.com/avatar/{email_hash}?s=400&d=identicon&r=g"

    @property
    def profile_image_url(self):
        return self.avatar_url or self.gravatar_url

    @property
    def role_names(self):
        return [role.name for role in self.roles]

    @property
    def password(self):
        raise AttributeError("password is not readable")

    @password.setter
    def password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

    def verify_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

    def has_role(self, role_name):
        return any(role.name == role_name for role in self.roles)

    def has_permission(self, permission_codename):
        codenames = {perm.codename for role in self.roles for perm in role.permissions}
        if permission_codename in codenames:
            return True
        if not permission_codename.endswith("_write") and (permission_codename + "_write") in codenames:
            return True
        return False

    @property
    def is_ldap_user(self):
        return self.auth_source == "ldap"

    def is_locked(self):
        if self.login_attempts >= 5 and self.last_login_attempt:
            lockout_end = self.last_login_attempt + timedelta(minutes=15)
            return datetime.utcnow() < lockout_end
        return False

    def increment_login_attempts(self):
        self.login_attempts += 1
        self.last_login_attempt = datetime.utcnow()

    def reset_login_attempts(self):
        self.login_attempts = 0
        self.last_login_attempt = None

    def __repr__(self):
        return f"<User {self.username}>"


class Role(db.Model):
    __tablename__ = "role"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32), unique=True, nullable=False)
    description = db.Column(db.String(256), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    permissions = db.relationship("Permission", secondary="role_permissions",
                                  lazy="subquery")

    def __repr__(self):
        return f"<Role {self.name}>"


role_permissions = db.Table(
    "role_permissions",
    db.Column("role_id", db.Integer, db.ForeignKey("role.id"), primary_key=True),
    db.Column("permission_id", db.Integer, db.ForeignKey("permission.id"), primary_key=True),
)


class Permission(db.Model):
    __tablename__ = "permission"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    codename = db.Column(db.String(64), unique=True, nullable=False)
    description = db.Column(db.String(256), nullable=True)

    def __repr__(self):
        return f"<Permission {self.codename}>"


class SystemSetting(db.Model):
    __tablename__ = "system_setting"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64), unique=True, nullable=False, index=True)
    value = db.Column(db.String(512), nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)

    updated_by = db.relationship("User", backref="system_settings", foreign_keys=[updated_by_id])

    @classmethod
    def get(cls, key, default=None):
        setting = cls.query.filter_by(key=key).first()
        return setting.value if setting else default

    @classmethod
    def set(cls, key, value, user_id=None):
        setting = cls.query.filter_by(key=key).first()
        if setting:
            setting.value = value
            setting.updated_by_id = user_id
        else:
            setting = cls(key=key, value=value, updated_by_id=user_id)
            db.session.add(setting)
        db.session.commit()

    def __repr__(self):
        return f"<SystemSetting {self.key}={self.value}>"


class Department(db.Model):
    __tablename__ = "department"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    head_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    head = db.relationship("User", backref=db.backref("headed_department", uselist=False),
                           foreign_keys=[head_id], remote_side="User.id")

    def __repr__(self):
        return f"<Department {self.name}>"


class UserSession(db.Model):
    __tablename__ = "user_session"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    session_id = db.Column(db.String(255), nullable=False, unique=True)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_activity = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref=db.backref("sessions", lazy="dynamic", cascade="all, delete-orphan"))
