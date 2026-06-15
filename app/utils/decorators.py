from functools import wraps
from flask import abort, flash, redirect, url_for
from flask_login import current_user
from app.extensions import db
from app.models.audit_log import AuditLog


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.has_role("admin"):
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


def permission_required(permission_codename):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash("Please log in to access this page.", "warning")
                return redirect(url_for("auth.login"))
            if not current_user.has_permission(permission_codename):
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def audit_logged(action, resource_type, get_resource_id=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            result = f(*args, **kwargs)
            try:
                from flask import request
                resource_id = None
                if get_resource_id:
                    resource_id = get_resource_id(*args, **kwargs)
                log = AuditLog(
                    user_id=current_user.id if current_user.is_authenticated else None,
                    action=action,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    ip_address=request.remote_addr,
                    user_agent=request.headers.get("User-Agent", "")[:256],
                )
                db.session.add(log)
                db.session.commit()
            except Exception:
                pass
            return result
        return decorated_function
    return decorator


def role_required(*role_names):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash("Please log in to access this page.", "warning")
                return redirect(url_for("auth.login"))
            if not any(current_user.has_role(r) for r in role_names):
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator
