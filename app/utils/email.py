from flask_mail import Message, Mail
from flask import render_template, current_app
from app.extensions import mail


def _apply_mail_settings():
    from app.models.user import SystemSetting
    app = current_app._get_current_object()
    server = SystemSetting.get("mail_server") or app.config.get("MAIL_SERVER", "")
    port = SystemSetting.get("mail_port") or app.config.get("MAIL_PORT", 587)
    use_tls = SystemSetting.get("mail_use_tls")
    username = SystemSetting.get("mail_username") or app.config.get("MAIL_USERNAME", "")
    password = SystemSetting.get("mail_password") or app.config.get("MAIL_PASSWORD", "")
    sender = SystemSetting.get("mail_default_sender") or app.config.get("MAIL_DEFAULT_SENDER", "")

    app.config["MAIL_SERVER"] = server
    try:
        app.config["MAIL_PORT"] = int(port)
    except (ValueError, TypeError):
        app.config["MAIL_PORT"] = 587
    app.config["MAIL_USE_TLS"] = str(use_tls).lower() == "true" if use_tls else app.config.get("MAIL_USE_TLS", True)
    app.config["MAIL_USE_SSL"] = str(use_tls).lower() == "ssl" if use_tls else False
    app.config["MAIL_USERNAME"] = username
    app.config["MAIL_PASSWORD"] = password
    app.config["MAIL_DEFAULT_SENDER"] = sender

    mail.init_app(app)


def send_email(to, subject, html_body):
    try:
        _apply_mail_settings()
        msg = Message(subject, recipients=[to], html=html_body)
        mail.send(msg)
        return True
    except Exception as e:
        current_app.logger.error("Failed to send email to %s: %s", to, e)
        return False


def send_test_email(to):
    subject = "Test Email from ISO27001-Manager"
    html_body = "<h2>Test Email</h2><p>If you receive this, your SMTP settings are working correctly.</p>"
    success = send_email(to, subject, html_body)
    return success
