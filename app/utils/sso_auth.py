import os
import logging
from flask import url_for, current_app
from authlib.integrations.flask_client import OAuth
from app.models.user import SystemSetting

logger = logging.getLogger(__name__)
oauth = OAuth()

saml_settings_cache = {}


def _get_sso_settings():
    return {
        "sso_enabled": SystemSetting.get("sso_enabled", "0") == "1",
        "sso_provider": SystemSetting.get("sso_provider", ""),
        "sso_client_id": SystemSetting.get("sso_client_id", ""),
        "sso_client_secret": SystemSetting.get("sso_client_secret", ""),
        "sso_issuer_url": SystemSetting.get("sso_issuer_url", ""),
        "sso_metadata_url": SystemSetting.get("sso_metadata_url", ""),
    }


def _get_oidc_config(provider):
    settings = _get_sso_settings()
    issuer = settings["sso_issuer_url"].rstrip("/")
    if provider == "azure":
        return {
            "client_id": settings["sso_client_id"],
            "client_secret": settings["sso_client_secret"],
            "server_metadata_url": f"{issuer}/.well-known/openid-configuration",
            "client_kwargs": {"scope": "openid email profile"},
        }
    elif provider == "google":
        return {
            "client_id": settings["sso_client_id"],
            "client_secret": settings["sso_client_secret"],
            "server_metadata_url": "https://accounts.google.com/.well-known/openid-configuration",
            "client_kwargs": {"scope": "openid email profile"},
        }
    elif provider == "okta":
        return {
            "client_id": settings["sso_client_id"],
            "client_secret": settings["sso_client_secret"],
            "server_metadata_url": f"{issuer}/.well-known/openid-configuration",
            "client_kwargs": {"scope": "openid email profile"},
        }
    return None


def register_oidc_clients(app):
    for provider in ("azure", "google", "okta"):
        oauth.register(
            name=f"sso_{provider}",
            overwrite=True,
            server_metadata_url=None,
            client_id=None,
            client_secret=None,
            client_kwargs={"scope": "openid email profile"},
        )
    _lazy_configure_clients(app)


def _lazy_configure_clients(app):
    with app.app_context():
        settings = _get_sso_settings()
        if not settings["sso_enabled"]:
            return
        provider = settings["sso_provider"]
        if provider in ("azure", "google", "okta"):
            cfg = _get_oidc_config(provider)
            if cfg:
                callback_url = url_for("auth.sso_callback", provider=provider, _external=True)
                oauth.register(
                    name=f"sso_{provider}",
                    overwrite=True,
                    client_id=cfg["client_id"],
                    client_secret=cfg["client_secret"],
                    server_metadata_url=cfg["server_metadata_url"],
                    client_kwargs=cfg["client_kwargs"],
                    authorize_params=None,
                    authorize_url=None,
                    access_token_url=None,
                    api_base_url=None,
                )


def init_sso(app):
    register_oidc_clients(app)


def get_saml_settings():
    settings = _get_sso_settings()
    base_url = None
    try:
        from flask import request as _req
        base_url = _req.host_url.rstrip("/")
    except Exception:
        base_url = "http://localhost:5000"

    acs_url = f"{base_url}/auth/sso/acs"
    entity_id = f"{base_url}/auth/sso/metadata"
    issuer_url = settings["sso_issuer_url"].rstrip("/") if settings["sso_issuer_url"] else ""

    return {
        "strict": True,
        "debug": True,
        "sp": {
            "entityId": entity_id,
            "assertionConsumerService": {
                "url": acs_url,
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST",
            },
            "singleLogoutService": {
                "url": f"{base_url}/auth/sso/slo",
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
            },
            "NameIDFormat": "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress",
        },
        "idp": {
            "entityId": issuer_url,
            "singleSignOnService": {
                "url": f"{issuer_url}/sso" if issuer_url else "",
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
            },
            "singleLogoutService": {
                "url": f"{issuer_url}/slo" if issuer_url else "",
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
            },
            "x509cert": SystemSetting.get("saml_x509_cert", ""),
        },
    }


def find_or_create_sso_user(user_info, provider):
    from app.extensions import db
    from app.models.user import User, Role

    email = user_info.get("email", "").lower().strip()
    if not email:
        return None, "Email not provided by SSO provider"

    user = User.query.filter_by(email=email).first()
    if user:
        if user.auth_source not in ("saml", "sso"):
            return None, f"Email {email} already registered with {user.auth_source} authentication"
        user.auth_source = "saml"
        if user_info.get("first_name"):
            user.first_name = user_info["first_name"]
        if user_info.get("last_name"):
            user.last_name = user_info["last_name"]
        db.session.commit()
        return user, None

    username = email.split("@")[0]
    base_username = username
    counter = 1
    while User.query.filter_by(username=username).first():
        username = f"{base_username}{counter}"
        counter += 1

    user_role = Role.query.filter_by(name="user").first()
    user = User(
        username=username,
        email=email,
        first_name=user_info.get("first_name", username),
        last_name=user_info.get("last_name", "User"),
        auth_source="saml",
        password_hash=os.urandom(32).hex(),
        is_active=True,
    )
    if user_role:
        user.roles.append(user_role)
    db.session.add(user)
    db.session.commit()
    return user, None
