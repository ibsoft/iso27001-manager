"""LDAP / Active Directory authentication service.

On successful authentication, auto-creates a local user account
with role='user' if one doesn't exist yet.
"""

import re
import logging
from datetime import datetime
from flask import current_app
from ldap3 import Server, Connection, ALL, SUBTREE
from ldap3.core.exceptions import LDAPException, LDAPBindError, LDAPSocketOpenError, LDAPStartTLSError

_logger = logging.getLogger("app.ldap")


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


def test_connection(settings=None):
    """Test LDAP connection with current or provided settings.
    Returns a dict with success, message, and optional details.
    """
    if settings is None:
        settings = _get_settings()

    log = []

    if not settings["server"]:
        return {"success": False, "message": "LDAP server address is empty", "log": log}
    if not settings["base_dn"]:
        return {"success": False, "message": "Base DN is empty", "log": log}

    log.append(f"Connecting to {settings['server']}:{settings['port']} (TLS: {settings['use_tls']})...")

    try:
        server = Server(
            settings["server"],
            port=settings["port"],
            get_info=ALL,
            use_ssl=settings["use_tls"],
            connect_timeout=10,
        )
        log.append(f"Server object created: {server}")

        bind_kwargs = {}
        if settings["bind_dn"]:
            bind_kwargs["user"] = settings["bind_dn"]
            bind_kwargs["password"] = settings["bind_password"]
            log.append(f"Bind DN: {settings['bind_dn']}")
        else:
            log.append("Bind DN: (anonymous)")

        conn = Connection(server, auto_bind=True, **bind_kwargs)
        log.append(f"Bound successfully: {conn}")
        log.append(f"Server info: {server.info}")

        # Test search with wildcard
        _test_filter = settings["user_filter"].replace("{username}", "*")
        log.append(f"Search 1: base={settings['base_dn']} filter={_test_filter}")
        _count1 = 0
        conn.search(
            search_base=settings["base_dn"],
            search_filter=_test_filter,
            search_scope=SUBTREE,
            attributes=['1.1'],
            size_limit=5,
            time_limit=10,
        )
        _count1 = len(conn.entries)
        log.append(f"Search 1 returned {_count1} entries")

        # If 0, try broader search to diagnose
        if not conn.entries:
            log.append("Search 2: trying (objectClass=*) to check base DN...")
            conn.search(
                search_base=settings["base_dn"],
                search_filter="(objectClass=*)",
                search_scope=SUBTREE,
                attributes=['1.1'],
                size_limit=5,
                time_limit=10,
            )
            log.append(f"Search 2 returned {len(conn.entries)} entries")

        conn.unbind()
        log.append("Connection closed.")
        _ok = _count1 > 0
        return {"success": _ok, "message": f"Connected (search 1 returned {_count1} entries)" if _ok else "Connected but search returned 0 entries — check Base DN and filter", "log": log}

    except LDAPStartTLSError as e:
        log.append(f"TLS error: {e}")
        return {"success": False, "message": f"TLS error: {e}", "log": log}
    except LDAPSocketOpenError as e:
        log.append(f"Socket error: {e}")
        return {"success": False, "message": f"Cannot reach server {settings['server']}:{settings['port']}", "log": log}
    except LDAPBindError as e:
        log.append(f"Bind error: {e}")
        return {"success": False, "message": f"Bind failed — check credentials", "log": log}
    except LDAPException as e:
        log.append(f"LDAP error: {e}")
        return {"success": False, "message": f"LDAP error: {e}", "log": log}
    except Exception as e:
        log.append(f"Unexpected error: {e}")
        return {"success": False, "message": f"Unexpected error: {e}", "log": log}


def authenticate(username, password):
    """Authenticate user against LDAP/AD.
    Returns a dict with user info on success, or None on failure.
    Auto-creates local user account if successful and user doesn't exist.
    """
    from app.extensions import db
    from app.models.user import User, Role

    settings = _get_settings()
    if not settings["enabled"] or not settings["server"] or not settings["base_dn"]:
        _logger.warning("LDAP auth skipped — not enabled or incomplete config")
        return None

    server = Server(settings["server"], port=settings["port"], get_info=ALL, use_ssl=settings["use_tls"])
    attr_map = _parse_attribute_map(settings["attribute_map"])

    search_filter = settings["user_filter"].replace("{username}", _escape_filter(username))
    _logger.info("LDAP auth for %s on %s:%s", username, settings["server"], settings["port"])

    try:
        conn = Connection(server, user=settings["bind_dn"], password=settings["bind_password"], auto_bind=True)
        attrs = list(attr_map.values())
        if not attrs:
            attrs = ['1.1']
        conn.search(
            search_base=settings["base_dn"],
            search_filter=search_filter,
            search_scope=SUBTREE,
            attributes=attrs,
            size_limit=1,
        )

        if not conn.entries:
            _logger.warning("LDAP user not found: %s", username)
            conn.unbind()
            return None

        entry = conn.entries[0]
        user_dn = entry.entry_dn
        _logger.info("LDAP found DN: %s", user_dn)

        # Attempt bind as the found user to verify password
        user_conn = Connection(server, user=user_dn, password=password, auto_bind=True)
        user_conn.unbind()
        conn.unbind()
        _logger.info("LDAP password verified for %s", username)

    except LDAPBindError:
        _logger.warning("LDAP bind failed for %s — bad password or locked account", username)
        return None
    except LDAPSocketOpenError as e:
        _logger.error("LDAP connection failed to %s:%s — %s", settings["server"], settings["port"], e)
        return None
    except LDAPException as e:
        _logger.error("LDAP error during auth for %s: %s", username, e)
        return None

    # Extract user attributes from LDAP entry
    ldap_attrs = _extract_attrs(entry, attr_map, username)

    # Auto-create or update local user
    user = User.query.filter_by(username=username).first()
    if user:
        if user.auth_source != "ldap":
            _logger.warning("LDAP: user %s exists but auth_source=%s, skipping", username, user.auth_source)
            return None  # local-only user, skip LDAP auth
        user.last_login = datetime.utcnow()
        user.first_name = ldap_attrs["first_name"]
        user.last_name = ldap_attrs["last_name"]
        user.email = ldap_attrs["email"]
        db.session.commit()
        _logger.info("LDAP: existing user %s authenticated", username)
        return {"id": user.id, "username": user.username, "is_new": False}

    # Create new user with role='user'
    return _create_ldap_user(ldap_attrs)


def list_users(settings=None, search=None, page=1, per_page=20):
    """List users from LDAP matching the configured filter.
    Supports optional search string and pagination.
    Returns a dict with success, message, users list, pagination info, and log.
    """
    from app.extensions import db as _db
    from app.models.user import User as _User

    if settings is None:
        settings = _get_settings()

    log = []
    if not settings["server"] or not settings["base_dn"]:
        return {"success": False, "message": "LDAP server or Base DN not configured", "users": [], "log": log}

    attr_map = _parse_attribute_map(settings["attribute_map"])

    # Build search filter: if search term given, wildcard-match; otherwise list all
    search_term = (search or "").strip()
    _wildcard = f"*{_escape_filter(search_term)}*" if search_term else "*"
    search_filter = settings["user_filter"].replace("{username}", _wildcard)

    # Extract username attribute from filter (e.g. "(sAMAccountName={username})" -> "sAMAccountName")
    _user_attr = "sAMAccountName"
    _m = re.search(r'\((\w+)=\{username\}', settings["user_filter"])
    if _m:
        _user_attr = _m.group(1)

    all_attrs = list(attr_map.values())
    if _user_attr not in all_attrs:
        all_attrs.append(_user_attr)
    if not all_attrs:
        all_attrs = ['1.1']

    log.append(f"Searching {settings['server']}:{settings['port']} base={settings['base_dn']}")
    log.append(f"Filter: {search_filter}")
    log.append(f"Attributes: {all_attrs}")

    try:
        server = Server(settings["server"], port=settings["port"], get_info=ALL, use_ssl=settings["use_tls"], connect_timeout=10)
        bind_kwargs = {}
        if settings["bind_dn"]:
            bind_kwargs["user"] = settings["bind_dn"]
            bind_kwargs["password"] = settings["bind_password"]

        conn = Connection(server, auto_bind=True, **bind_kwargs)
        log.append("Bound successfully")

        conn.search(
            search_base=settings["base_dn"],
            search_filter=search_filter,
            search_scope=SUBTREE,
            attributes=all_attrs,
            size_limit=1000,
            time_limit=30,
        )
        log.append(f"Found {len(conn.entries)} total users")

        users = []
        for entry in conn.entries:
            raw = getattr(entry, _user_attr, None)
            _username = str(raw) if raw is not None else entry.entry_dn
            attrs = _extract_attrs(entry, attr_map, _username)
            existing = _User.query.filter_by(username=attrs["username"]).first()
            users.append({
                "dn": entry.entry_dn,
                "username": attrs["username"],
                "email": attrs["email"],
                "first_name": attrs["first_name"],
                "last_name": attrs["last_name"],
                "exists": existing is not None,
                "auth_source": existing.auth_source if existing else None,
            })

        conn.unbind()
        log.append("Connection closed")

        total = len(users)
        total_pages = max(1, (total + per_page - 1) // per_page)
        page = max(1, min(page, total_pages))
        start = (page - 1) * per_page
        end = start + per_page

        return {
            "success": True,
            "message": f"Found {total} user(s)",
            "users": users[start:end],
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "search": search_term,
            "log": log,
        }

    except LDAPStartTLSError as e:
        log.append(f"TLS error: {e}")
        return {"success": False, "message": f"TLS error: {e}", "users": [], "log": log}
    except LDAPSocketOpenError as e:
        log.append(f"Socket error: {e}")
        return {"success": False, "message": "Cannot reach server", "users": [], "log": log}
    except LDAPBindError as e:
        log.append(f"Bind error: {e}")
        return {"success": False, "message": "Bind failed", "users": [], "log": log}
    except LDAPException as e:
        log.append(f"LDAP error: {e}")
        return {"success": False, "message": f"LDAP error: {e}", "users": [], "log": log}
    except Exception as e:
        log.append(f"Unexpected error: {e}")
        return {"success": False, "message": f"Error: {e}", "users": [], "log": log}


def import_users(usernames, settings=None):
    """Import selected LDAP users into local database."""
    from app.extensions import db
    from app.models.user import User, Role

    if settings is None:
        settings = _get_settings()

    imported = 0
    skipped = 0
    errors = []

    attr_map = _parse_attribute_map(settings["attribute_map"])

    try:
        server = Server(settings["server"], port=settings["port"], get_info=ALL, use_ssl=settings["use_tls"], connect_timeout=10)
        bind_kwargs = {}
        if settings["bind_dn"]:
            bind_kwargs["user"] = settings["bind_dn"]
            bind_kwargs["password"] = settings["bind_password"]

        conn = Connection(server, auto_bind=True, **bind_kwargs)

        for username in usernames:
            try:
                existing = User.query.filter_by(username=username).first()
                if existing:
                    if existing.auth_source == "ldap":
                        skipped += 1
                        continue
                    errors.append(f"{username}: already exists with auth_source={existing.auth_source}")
                    continue

                search_filter = settings["user_filter"].replace("{username}", _escape_filter(username))
                _attrs = list(attr_map.values())
                if not _attrs:
                    _attrs = ['1.1']
                conn.search(
                    search_base=settings["base_dn"],
                    search_filter=search_filter,
                    search_scope=SUBTREE,
                    attributes=_attrs,
                    size_limit=1,
                    time_limit=10,
                )

                if not conn.entries:
                    errors.append(f"{username}: not found in LDAP")
                    continue

                entry = conn.entries[0]
                attrs = _extract_attrs(entry, attr_map, username)
                _create_ldap_user(attrs)
                imported += 1

            except Exception as e:
                errors.append(f"{username}: {e}")

        conn.unbind()
    except Exception as e:
        errors.append(f"LDAP connection failed: {e}")

    return {"imported": imported, "skipped": skipped, "errors": errors}


def _extract_attrs(entry, attr_map, username):
    """Extract user attributes from an LDAP entry."""
    ldap_attrs = {"username": username}
    for local_field, ldap_attr in attr_map.items():
        val = getattr(entry, ldap_attr, None)
        if val is not None:
            ldap_attrs[local_field] = str(val) if hasattr(val, "value") else str(val[0]) if val else ""
    ldap_attrs.setdefault("email", f"{username}@ldap")
    ldap_attrs.setdefault("first_name", username)
    ldap_attrs.setdefault("last_name", "")
    return ldap_attrs


def _create_ldap_user(attrs):
    """Create a local user record for an LDAP user."""
    from app.extensions import db
    from app.models.user import User, Role

    user_role = Role.query.filter_by(name="user").first()
    user = User(
        username=attrs["username"],
        email=attrs["email"],
        first_name=attrs["first_name"],
        last_name=attrs["last_name"],
        auth_source="ldap",
        password_hash="__ldap__",
        is_active=True,
        last_login=datetime.utcnow(),
    )
    if user_role:
        user.roles.append(user_role)
    db.session.add(user)
    db.session.commit()
    _logger.info("LDAP: created local user %s", attrs["username"])
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
