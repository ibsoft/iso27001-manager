"""LDAP / Active Directory authentication service.

On successful authentication, auto-creates a local user account
with role='user' if one doesn't exist yet.
"""

import re
from datetime import datetime
from flask import current_app
from ldap3 import Server, Connection, ALL, SUBTREE
from ldap3.core.exceptions import LDAPException, LDAPBindError, LDAPSocketOpenError


def _get_settings():
    """Read LDAP settings from SystemSetting table."""
    from app.models.user import SystemSetting

    return {
        "enabled": SystemSetting.get("ldap_enabled", "0") == "1",
        "server": SystemSetting.get("ldap_server", ""),
        "port": int(SystemSetting.get("ldap_port", "389")),
        "use_tls": SystemSetting.get("ldap_use_tls", "0") == "1",
        "base_dn": SystemSetting.get("ldap_base_dn", ""),
        "bind_dn": SystemSetting.get("ldap_bind_dn", ""),
        "bind_password": SystemSetting.get("ldap_bind_password", ""),
        "user_filter": SystemSetting.get("ldap_user_filter", "(sAMAccountName={username})"),
        "attribute_map": SystemSetting.get("ldap_attribute_map",
                                           '{"email":"mail","first_name":"givenName","last_name":"sn"}'),
    }


def authenticate(username, password):
    """Authenticate user against LDAP/AD.
    Returns a dict with user info on success, or None on failure.
    Auto-creates local user account if successful and user doesn't exist.
    """
    from app.extensions import db
    from app.models.user import User, Role

    settings = _get_settings()
    if not settings["enabled"] or not settings["server"] or not settings["base_dn"]:
        return None

    server = Server(settings["server"], port=settings["port"], get_info=ALL, use_ssl=settings["use_tls"])
    attr_map = _parse_attribute_map(settings["attribute_map"])

    search_filter = settings["user_filter"].replace("{username}", _escape_filter(username))

    try:
        conn = Connection(server, user=settings["bind_dn"], password=settings["bind_password"], auto_bind=True)
        conn.search(
            search_base=settings["base_dn"],
            search_filter=search_filter,
            search_scope=SUBTREE,
            attributes=list(attr_map.values()) + ["dn"],
            size_limit=1,
        )

        if not conn.entries:
            conn.unbind()
            return None

        entry = conn.entries[0]
        user_dn = entry.entry_dn

        # Attempt bind as the found user to verify password
        user_conn = Connection(server, user=user_dn, password=password, auto_bind=True)
        user_conn.unbind()
        conn.unbind()

    except (LDAPBindError, LDAPSocketOpenError, LDAPException):
        return None

    # Extract user attributes from LDAP entry
    ldap_attrs = {}
    for local_field, ldap_attr in attr_map.items():
        val = getattr(entry, ldap_attr, None)
        if val is not None:
            ldap_attrs[local_field] = str(val) if hasattr(val, "value") else str(val[0]) if val else ""

    ldap_attrs["username"] = username
    ldap_attrs.setdefault("email", f"{username}@ldap")
    ldap_attrs.setdefault("first_name", username)
    ldap_attrs.setdefault("last_name", "")

    # Auto-create or update local user
    user = User.query.filter_by(username=username).first()
    if user:
        if user.auth_source != "ldap":
            return None  # local-only user, skip LDAP auth
        user.last_login = datetime.utcnow()
        db.session.commit()
        return {"id": user.id, "username": user.username, "is_new": False}

    # Create new user with role='user'
    user_role = Role.query.filter_by(name="user").first()
    user = User(
        username=ldap_attrs["username"],
        email=ldap_attrs["email"],
        first_name=ldap_attrs["first_name"],
        last_name=ldap_attrs["last_name"],
        auth_source="ldap",
        password_hash="__ldap__",  # cannot log in locally
        is_active=True,
        last_login=datetime.utcnow(),
    )
    if user_role:
        user.roles.append(user_role)
    db.session.add(user)
    db.session.commit()
    return {"id": user.id, "username": user.username, "is_new": True}


def _parse_attribute_map(json_str):
    """Parse the attribute map JSON. Returns dict with defaults on error."""
    import json

    try:
        return json.loads(json_str) if json_str else {}
    except (json.JSONDecodeError, TypeError):
        return {"email": "mail", "first_name": "givenName", "last_name": "sn"}


def _escape_filter(value):
    """Escape special characters for LDAP filter."""
    return re.sub(r"([*()\\\0])", r"\\\1", value)
