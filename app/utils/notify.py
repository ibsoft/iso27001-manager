from app.extensions import db
from app.models.notification import Notification
from app.utils.email import send_email


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
