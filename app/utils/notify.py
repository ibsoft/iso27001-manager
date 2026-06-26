from app.extensions import db
from app.models.notification import Notification
from app.utils.email import send_email


def _get_alert_recipients(event_type):
    from app.models.email_alert import EmailAlert
    from app.models.user import User, Role

    alerts = EmailAlert.query.filter_by(event_type=event_type, is_active=True).all()
    recipients = set()
    for alert in alerts:
        if alert.recipient_type == "user":
            user = User.query.get(alert.recipient_id)
            if user and user.email:
                recipients.add(user.email)
        elif alert.recipient_type == "role":
            role = Role.query.get(alert.recipient_id)
            if role:
                for user in role.users:
                    if user.email:
                        recipients.add(user.email)
    return list(recipients)


def notify(user, ntype, title, message=None, link=None, send_email_too=True, reference_type=None, reference_id=None):
    notif = Notification(
        user_id=user.id,
        type=ntype,
        title=title,
        message=message,
        link=link,
        reference_type=reference_type,
        reference_id=reference_id,
    )
    db.session.add(notif)
    db.session.commit()

    if send_email_too and user.email:
        from flask import render_template
        subject = title
        html = f"<h2>{title}</h2><p>{message or ''}</p>"
        try:
            html = render_template(f"email/{ntype}.html", title=title, message=message, link=link)
        except Exception:
            pass
        send_email(user.email, subject, html)

    return notif


def dispatch_alert(event_type, subject, html_body, context_user=None):
    recipients = _get_alert_recipients(event_type)
    if not recipients:
        return 0
    sent = 0
    for email in recipients:
        if send_email(email, subject, html_body):
            sent += 1
            from app.models.audit_log import AuditLog
            log = AuditLog(
                user_id=context_user.id if context_user else None,
                action="ALERT_SENT",
                resource_type="EmailAlert",
                resource_id=None,
                details=f"Alert '{event_type}' sent to {email}",
                ip_address=None,
            )
            db.session.add(log)
    db.session.commit()
    return sent
